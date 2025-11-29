"""
core/signal_engine.py
---------------------
Capa intermedia entre Telegram/DB ↔ Motor Técnico A+.

Responsabilidades:
- Parsear señales crudas
- Convertirlas en objetos Signal
- Llamar al Motor Técnico Unificado A+
- Devolver dicts estandarizados a controladores
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from models.signal import Signal
from core.technical_brain_unified import run_unified_analysis
from utils.helpers import normalize_direction
from utils.formatters import (
    format_signal_intro,
    format_analysis_summary,
)

logger = logging.getLogger("signal_engine")


# ============================================================
# 🔍 PARSEAR Y NORMALIZAR SEÑALES DEL CANAL VIP
# ============================================================

def parse_raw_signal(raw_text: str) -> Optional[Signal]:
    """Convierte texto crudo en objeto Signal limpio."""
    try:
        text = raw_text.replace("\n", " ").strip()

        if "#" not in text:
            return None

        # Par
        start = text.index("#") + 1
        end = text.index(" ", start)
        raw_pair = text[start:end].upper().replace("/", "").strip()

        # Dirección
        direction = "long" if "LONG" in text.upper() else "short"

        # Entry
        entry = None
        if "ENTRY" in text.upper():
            try:
                part = text.upper().split("ENTRY")[1]
                entry = float(part.replace("-", "").strip().split(" ")[0])
            except Exception:
                entry = None

        return Signal(
            symbol=raw_pair,
            direction=direction,
            raw_text=raw_text,
            entry_price=entry,
        )

    except Exception as e:
        logger.error(f"❌ Error parseando señal: {e}")
        return None


# ============================================================
# 🧠 ANÁLISIS PARA SEÑALES NUEVAS
# ============================================================

def analyze_signal(signal: Signal) -> Dict:
    """Ejecuta análisis técnico completo (Motor A+) para señales nuevas."""
    try:
        logger.info(f"🧠 Analizando señal: {signal.symbol} ({signal.direction})")

        analysis = run_unified_analysis(
            symbol=signal.symbol,
            direction_hint=normalize_direction(signal.direction),
            request_context="signal_entry",     # ✔ Etiqueta A+
        )

        summary = format_analysis_summary(
            symbol=signal.symbol,
            direction=signal.direction,
            match_ratio=analysis["match_ratio"],
            technical_score=analysis["technical_score"],
            grade=analysis["grade"],
            decision=analysis["decision"],
            emoji=analysis["global_confidence"],
        )

        return {
            "signal": signal,
            "analysis": analysis,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_signal(): {e}")
        return {
            "signal": signal,
            "analysis": {"allowed": False, "decision": "error", "error": str(e)},
            "summary": "Error interno ejecutando análisis técnico.",
        }


# ============================================================
# ♻️ ANÁLISIS DE REACTIVACIÓN
# ============================================================

def analyze_reactivation(signal: Signal) -> Dict:
    """Evalúa si una señal pendiente debe reactivarse (Motor A+)."""
    try:
        logger.info(f"♻️ Reactivación: {signal.symbol} ({signal.direction})")

        analysis = run_unified_analysis(
            symbol=signal.symbol,
            direction_hint=normalize_direction(signal.direction),
            request_context="signal_reactivation",     # ✔ Etiqueta A+
        )

        return {
            "signal": signal,
            "analysis": analysis,
            "summary": f"Reactivación → {analysis['decision']} ({analysis['global_confidence']})",
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_reactivation(): {e}")
        return {
            "signal": signal,
            "analysis": {"allowed": False, "decision": "error", "error": str(e)},
            "summary": "Error técnico evaluando reactivación.",
        }


# ============================================================
# 🔄 ANÁLISIS DE POSICIONES ABIERTAS
# ============================================================

def analyze_open_position(symbol: str, direction: str) -> Dict:
    """Evalúa reversiones y continuaciones sobre posiciones abiertas."""
    try:
        logger.info(f"🔍 Analizando posición abierta: {symbol} ({direction})")

        analysis = run_unified_analysis(
            symbol=symbol,
            direction_hint=normalize_direction(direction),
            request_context="open_position",       # ✔ Etiqueta A+
        )

        return {
            "symbol": symbol,
            "direction": direction,
            "analysis": analysis,
            "summary": f"Posición → {analysis['decision']} ({analysis['global_confidence']})",
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_open_position(): {e}")
        return {
            "symbol": symbol,
            "direction": direction,
            "analysis": {"allowed": False, "decision": "error", "error": str(e)},
            "summary": "Error técnico evaluando la posición.",
        }
