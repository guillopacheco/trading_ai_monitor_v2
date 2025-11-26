import logging
from indicators import (
    get_multi_tf_trend,
    detect_divergences,
    get_atr_series,
    get_latest_candles,
    get_volume_series,
)
from helpers import normalize_tf_list

logger = logging.getLogger("entry_validator")

# ============================================================
#  ENTRY VALIDATOR v1.1 — Bloquea entrada peligrosa,
#  pero conserva reactivación futura (modo profesional)
# ============================================================

def validate_entry(symbol: str, direction: str) -> dict:
    """
    Evaluación profesional de entrada al recibir una señal.
    
    Retorna:
        {
            "allowed": bool,
            "severity": "ok" | "warning" | "blocked",
            "reasons": [...],
            "score": float (0–100),
            "trend_alignment": float,
            "risk_conditions": dict,
            "momentum_conditions": dict
        }
    """

    results = {
        "allowed": True,
        "severity": "ok",
        "score": 0,
        "trend_alignment": 0,
        "reasons": [],
        "risk_conditions": {},
        "momentum_conditions": {},
    }

    # ============================================
    # 0️⃣ Configuración de temporalidades estables
    # ============================================
    tfs = ["15m", "30m", "1h", "4h"]
    tfs = normalize_tf_list(tfs)

    # ============================================
    # 1️⃣ Tendencia multi-TF
    # ============================================
    try:
        trend_data = get_multi_tf_trend(symbol, tfs)
    except Exception as e:
        logger.error(f"❌ Error en get_multi_tf_trend({symbol}): {e}")
        results["allowed"] = False
        results["severity"] = "blocked"
        results["reasons"].append("Error al obtener tendencias multi-TF.")
        return results

    # Conteo de tendencias alineadas
    same_direction = 0
    total_valid = 0

    for tf, info in trend_data.items():
        if not info:
            continue

        total_valid += 1
        if info["trend"].lower() == direction.lower():
            same_direction += 1

    trend_alignment = (same_direction / max(1, total_valid)) * 100
    results["trend_alignment"] = round(trend_alignment, 2)

    # Regla principal:
    # → En scalping (<30m), se requiere >= 40%
    # → En swing (≥30m), se requiere >= 60%
    if trend_alignment < 40:
        results["allowed"] = False
        results["severity"] = "blocked"
        results["reasons"].append("Tendencia global desalineada (<40%).")
    elif trend_alignment < 60:
        results["severity"] = "warning"
        results["reasons"].append("Tendencia mayor parcialmente desalineada.")

    # ============================================
    # 2️⃣ Divergencias
    # ============================================
    try:
        divs = detect_divergences(symbol, tfs)
    except:
        divs = {}

    bullish_div = any(d.get("type") == "bullish" for d in divs.values())
    bearish_div = any(d.get("type") == "bearish" for d in divs.values())

    # Señal LONG bloqueada por divergencia bajista fuerte
    if direction == "long" and bearish_div:
        results["allowed"] = False
        results["severity"] = "blocked"
        results["reasons"].append("Divergencia bajista fuerte detectada.")

    # Señal SHORT bloqueada por divergencia alcista fuerte
    if direction == "short" and bullish_div:
        results["allowed"] = False
        results["severity"] = "blocked"
        results["reasons"].append("Divergencia alcista fuerte detectada.")

    # ============================================
    # 3️⃣ Momentum inmediato (velas recientes)
    # ============================================
    candles = get_latest_candles(symbol, "15m", 5)
    if candles is not None and len(candles) >= 3:
        last = candles.iloc[-1]
        prev = candles.iloc[-2]

        # Cuerpo relativo
        body = abs(last["close"] - last["open"])
        range_total = last["high"] - last["low"]

        if range_total > 0:
            body_ratio = body / range_total
        else:
            body_ratio = 0

        # Regla:
        # Si la última vela es FUERTE CONTRARIA → bloquear
        if direction == "short" and last["close"] > last["open"] and body_ratio > 0.60:
            results["allowed"] = False
            results["severity"] = "blocked"
            results["reasons"].append("Momentum contrario fuerte detectado en 15m.")

        if direction == "long" and last["close"] < last["open"] and body_ratio > 0.60:
            results["allowed"] = False
            results["severity"] = "blocked"
            results["reasons"].append("Momentum contrario fuerte detectado en 15m.")

        results["momentum_conditions"] = {
            "last_body_ratio": round(body_ratio, 3),
            "last_close": float(last["close"]),
            "last_open": float(last["open"]),
        }

    # ============================================
    # 4️⃣ Volumen relativo
    # ============================================
    vol = get_volume_series(symbol, "1h")
    if vol is not None and len(vol) > 5:
        recent_vol = vol.iloc[-1]
        avg_vol = vol.iloc[-5:].mean()

        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 0
        results["risk_conditions"]["volume_ratio"] = round(vol_ratio, 2)

        if vol_ratio < 0.45:
            results["severity"] = "warning"
            results["reasons"].append("Volumen débil (<45%). Entrada poco fiable.")

    # ============================================
    # 5️⃣ ATR — volatilidad / riesgo SL
    # ============================================
    atr = get_atr_series(symbol, "1h")
    if atr is not None:
        atr_val = atr.iloc[-1]
        results["risk_conditions"]["atr"] = float(atr_val)

        if atr_val > 0:
            # Una volatilidad demasiado baja o demasiado alta penaliza
            if atr_val < 0.004:
                results["severity"] = "warning"
                results["reasons"].append("ATR extremadamente bajo (posible rango estrecho).")

            if atr_val > 0.06:
                results["severity"] = "warning"
                results["reasons"].append("ATR muy alto (riesgo de barridas).")

    # ============================================
    # 6️⃣ Score final
    # ============================================
    score = trend_alignment

    if bullish_div or bearish_div:
        score -= 20

    if results["severity"] == "warning":
        score -= 10

    if not results["allowed"]:
        score -= 40

    results["score"] = max(0, min(100, score))

    return results
