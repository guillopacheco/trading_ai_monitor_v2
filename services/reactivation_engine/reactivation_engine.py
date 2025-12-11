import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger("reactivation_engine")


# ============================================================
# Estados y modos de reactivación
# ============================================================


class ReactivationState(str, Enum):
    IGNORED = "ignored"  # Señal descartada inicialmente (skip)
    WATCHING = "watching"  # En observación
    CANDIDATE = "candidate"  # Cumple parte de las condiciones
    REACTIVATED = "reactivated"  # Reactivada oficialmente
    EXPIRED = "expired"  # Ya no tiene sentido reactivarla


class ReactivationMode(str, Enum):
    WITH_TREND = "with_trend"  # A favor de la tendencia mayor
    COUNTER_TREND = "counter_trend"  # Contra la tendencia mayor
    NEUTRAL = "neutral"  # Sin ventaja clara


# ============================================================
# Resultado estructurado
# ============================================================


@dataclass
class ReactivationResult:
    should_reactivate: bool
    state: ReactivationState
    score: float  # 0–100
    mode: ReactivationMode
    dominant_tf: Optional[str]
    risk_level: str  # "low" / "medium" / "high"
    reasons: List[str]
    context: str  # siempre "reactivation"
    meta: Dict[str, Any]


# ============================================================
# Reactivation Engine (capa táctica)
# ============================================================


class ReactivationEngine:
    """
    Capa táctica de reactivación.

    Usa el motor técnico base como sensor estructural y decide si una señal
    inicialmente ignorada ("skip") merece una reactivación tardía en
    temporalidades menores (15m / 30m), con control de riesgo.
    """

    def __init__(self, technical_engine):
        self.technical_engine = technical_engine

        # 🔧 Umbrales ajustables
        self.REACTIVATE_SCORE = 60.0  # mínimo para reactivar
        self.CANDIDATE_SCORE = 30.0  # por debajo de esto, solo watching

    # --------------------------------------------------------
    # Punto de entrada principal
    # --------------------------------------------------------
    async def evaluate_signal(
        self,
        signal: Dict[str, Any],
        base_result: Dict[str, Any],
    ) -> ReactivationResult:
        """
        Evalúa si una señal (ya analizada y saltada) merece reactivación.

        - `signal`: fila de la DB de señales (id, symbol, direction, chat_id, etc.)
        - `base_result`: resultado original del motor técnico (decision=skip, grade, score...)

        Devuelve un ReactivationResult con:
        - should_reactivate=True/False
        - score de reactivación (0–100)
        - modo (with_trend / counter_trend / neutral)
        - tf dominante que dispara la reactivación
        - nivel de riesgo y razones explicables
        """

        symbol = signal["symbol"]
        direction = signal["direction"].lower()

        logger.info(
            f"♻️ Evaluando reactivación | ID={signal.get('id')} | "
            f"{symbol} {direction}"
        )

        # 1️⃣ Filtro duro: señales que jamás se reactivan
        grade = base_result.get("grade")
        technical_score = base_result.get("technical_score", 0)

        if grade == "D" or (
            isinstance(technical_score, (int, float)) and technical_score < 30
        ):
            logger.info(
                f"♻️ Señal ID={signal.get('id')} marcada como EXPIRED "
                f"(grade={grade}, score={technical_score})"
            )
            return self._expired(
                "Grade D o score técnico insuficiente para reactivación."
            )

        # 2️⃣ Snapshot fresco del motor técnico (contexto = reactivation)
        try:
            fresh_result = await self.technical_engine.analyze(
                symbol=symbol,
                direction=direction,
                context="reactivation",
            )
        except Exception as e:
            logger.exception(
                f"❌ Error en technical_engine.analyze() para reactivación {symbol}: {e}"
            )
            return self._expired("Error al obtener snapshot técnico para reactivación.")

        # 3️⃣ Calcular score táctico de reactivación
        score, mode, dominant_tf, risk_level, reasons = (
            self._compute_reactivation_score(
                direction=direction, fresh_result=fresh_result
            )
        )

        # 4️⃣ Decisión final según score
        if score >= self.REACTIVATE_SCORE:
            state = ReactivationState.REACTIVATED
            should_reactivate = True
        elif score >= self.CANDIDATE_SCORE:
            state = ReactivationState.CANDIDATE
            should_reactivate = False
        else:
            state = ReactivationState.WATCHING
            should_reactivate = False

        logger.info(
            f"♻️ Resultado reactivación | {symbol} {direction} | "
            f"score={score:.1f} | state={state.value} | mode={mode.value} | "
            f"tf_dominante={dominant_tf} | riesgo={risk_level}"
        )

        return ReactivationResult(
            should_reactivate=should_reactivate,
            state=state,
            score=score,
            mode=mode,
            dominant_tf=dominant_tf,
            risk_level=risk_level,
            reasons=reasons,
            context="reactivation",
            meta={"fresh_result": fresh_result},
        )

    # --------------------------------------------------------
    # Núcleo de scoring táctico (B2–B4)
    # --------------------------------------------------------
    def _compute_reactivation_score(
        self,
        direction: str,
        fresh_result: Dict[str, Any],
    ):
        """
        Calcula el score de reactivación en función de:

        - Relación con la tendencia mayor (with / counter-trend)
        - Cruce de EMAs (obligatorio en la práctica)
        - (Opcional) cruce de banda media de Bollinger si existe en el snapshot
        - Señales de confirmación: MACD, RSI, divergencias RSI/CCI
        """

        timeframes = fresh_result.get("timeframes") or []
        major_trend = fresh_result.get("major_trend_code")  # bull / bear / flat / None

        score = 0.0
        reasons: List[str] = []
        dominant_tf: Optional[str] = None
        risk_level = "medium"
        mode = ReactivationMode.NEUTRAL

        direction = direction.lower()

        # ----------------------------------------------------
        # B3 — Relación con la tendencia mayor
        # ----------------------------------------------------
        if (direction == "long" and major_trend == "bull") or (
            direction == "short" and major_trend == "bear"
        ):
            mode = ReactivationMode.WITH_TREND
            score += 10.0
            reasons.append("Reactivación a favor de la tendencia mayor.")
        elif major_trend in ("bull", "bear"):
            mode = ReactivationMode.COUNTER_TREND
            score -= 10.0
            risk_level = "high"
            reasons.append("Reactivación contra la tendencia mayor.")
        else:
            mode = ReactivationMode.NEUTRAL
            reasons.append("Tendencia mayor neutra o indefinida.")

        # ----------------------------------------------------
        # B2 — Señales en TF bajos (estructura + momentum)
        # Se evalúan de menor a mayor TF (15m, 30m, 1h...)
        # ----------------------------------------------------
        for tf in reversed(timeframes):
            tf_label = tf.get("tf_label") or tf.get("tf")
            if not tf_label:
                continue

            ema_short = tf.get("ema_short")
            ema_long = tf.get("ema_long")
            macd_hist = tf.get("macd_hist")
            rsi = tf.get("rsi")
            div_rsi = tf.get("div_rsi")
            div_cci = tf.get("div_cci")  # opcional, si el motor lo calcula
            close_price = tf.get("close")

            # Posible banda media de BB (si algún día la añades al motor)
            bb_mid = tf.get("bb_mid") or tf.get("bb_middle")

            # 1) Cruce EMAs 10/30 a favor del trade (peso fuerte)
            ema_cross = False
            if ema_short is not None and ema_long is not None:
                if direction == "long" and ema_short > ema_long:
                    ema_cross = True
                    score += 40.0
                    reasons.append(f"Cruce EMA alcista a favor en {tf_label}.")
                elif direction == "short" and ema_short < ema_long:
                    ema_cross = True
                    score += 40.0
                    reasons.append(f"Cruce EMA bajista a favor en {tf_label}.")

            if ema_cross and dominant_tf is None:
                dominant_tf = tf_label

            # 2) Banda media BB20 (si existe en el snapshot)
            if bb_mid is not None and close_price is not None:
                if direction == "long" and close_price > bb_mid:
                    score += 30.0
                    reasons.append(
                        f"Precio por encima de la banda media BB en {tf_label}."
                    )
                    if dominant_tf is None:
                        dominant_tf = tf_label
                elif direction == "short" and close_price < bb_mid:
                    score += 30.0
                    reasons.append(
                        f"Precio por debajo de la banda media BB en {tf_label}."
                    )
                    if dominant_tf is None:
                        dominant_tf = tf_label

            # 3) Confirmación MACD (cambio de momentum)
            if macd_hist is not None:
                if direction == "long" and macd_hist > 0:
                    score += 15.0
                    reasons.append(f"MACD respalda movimiento alcista en {tf_label}.")
                    if dominant_tf is None:
                        dominant_tf = tf_label
                elif direction == "short" and macd_hist < 0:
                    score += 15.0
                    reasons.append(f"MACD respalda movimiento bajista en {tf_label}.")
                    if dominant_tf is None:
                        dominant_tf = tf_label

            # 4) Divergencias RSI / CCI (opcionales pero potentes)
            if div_rsi and div_rsi != "ninguna":
                score += 20.0
                reasons.append(f"Divergencia RSI a favor en {tf_label}.")
                if dominant_tf is None:
                    dominant_tf = tf_label

            if div_cci and div_cci != "ninguna":
                score += 20.0
                reasons.append(f"Divergencia CCI a favor en {tf_label}.")
                if dominant_tf is None:
                    dominant_tf = tf_label

            # 5) RSI saliendo de zona extrema
            if rsi is not None:
                if direction == "long" and rsi > 40:
                    score += 10.0
                    reasons.append(f"RSI se recupera por encima de 40 en {tf_label}.")
                elif direction == "short" and rsi < 60:
                    score += 10.0
                    reasons.append(f"RSI pierde fuerza por debajo de 60 en {tf_label}.")

        # ----------------------------------------------------
        # Normalización y ajustes finales
        # ----------------------------------------------------
        score = max(0.0, min(100.0, score))

        if dominant_tf is None and timeframes:
            # Si nada dominó explícitamente, usamos el TF menor (más táctico)
            dominant_tf = timeframes[-1].get("tf_label") or timeframes[-1].get("tf")

        # Riesgo según modo y score
        if mode == ReactivationMode.COUNTER_TREND:
            risk_level = "high"
        elif score >= 80:
            risk_level = "low"
        else:
            risk_level = max(risk_level, "medium")

        return score, mode, dominant_tf, risk_level, reasons

    # --------------------------------------------------------
    # Helper para marcar señal expirada
    # --------------------------------------------------------
    def _expired(self, reason: str) -> ReactivationResult:
        return ReactivationResult(
            should_reactivate=False,
            state=ReactivationState.EXPIRED,
            score=0.0,
            mode=ReactivationMode.NEUTRAL,
            dominant_tf=None,
            risk_level="high",
            reasons=[reason],
            context="reactivation",
            meta={},
        )
