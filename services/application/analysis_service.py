import logging

logger = logging.getLogger("analysis_service")

# Motor técnico (DeepSeek o GPT)
# El wrapper puede ser async o sync dependiendo de la versión
try:
    from services.technical_engine.motor_wrapper import analyze as engine_analyze
except:
    from services.technical_engine.technical_engine import analyze as engine_analyze


# ============================================================
#  FUNCIÓN DE NORMALIZACIÓN
# ============================================================
def _normalize_analysis(symbol: str, direction: str, raw: dict) -> dict:
    """
    Garantiza que el análisis SIEMPRE regrese una estructura estándar,
    sin importar si viene del motor GPT, DeepSeek o un wrapper.
    """

    if not isinstance(raw, dict):
        return {
            "symbol": symbol,
            "direction": direction,
            "error": True,
            "msg": "Motor devolvió estructura inválida"
        }

    # --- BASE ---
    result = {
        "symbol": raw.get("symbol", symbol),
        "direction": direction,
        "error": False,

        # DECISIÓN
        "decision": {
            "decision": "unknown",
            "allowed": False,
            "decision_reasons": []
        },

        # ENTRADA
        "entry": {
            "allowed": False,
            "entry_mode": "N/A",
            "entry_score": 0
        }
    }

    # --- CASO 1: DeepSeek-style (decision y smart_entry anidados) ---
    if "decision" in raw and isinstance(raw["decision"], dict):
        decision = raw["decision"]
        result["decision"]["decision"] = decision.get("decision", "unknown")
        result["decision"]["allowed"] = decision.get("allowed", False)
        result["decision"]["decision_reasons"] = decision.get("decision_reasons", [])

    # --- CASO 2: GPT-style (entry separado) ---
    if "entry" in raw and isinstance(raw["entry"], dict):
        entry = raw["entry"]
        result["entry"]["allowed"] = entry.get("allowed", False)
        result["entry"]["entry_mode"] = entry.get("entry_mode", "N/A")
        result["entry"]["entry_score"] = entry.get("entry_score", 0)

    # Si la decisión no tiene allowed, pero entry sí → fallback
    if not result["decision"]["allowed"] and result["entry"]["allowed"]:
        result["decision"]["allowed"] = True
        result["decision"]["decision"] = "entry_allowed"

    return result


# ============================================================
#  ANÁLISIS PRINCIPAL
# ============================================================
async def analyze_symbol(symbol: str, direction: str) -> dict:
    """
    Ejecuta el motor técnico (sin saber si es async o sync)
    y normaliza el resultado.
    """
    try:
        # DeepSeek: función normal
        # GPT: async
        try:
            raw = engine_analyze(symbol, direction)
        except TypeError:
            raw = await engine_analyze(symbol, direction)

        normalized = _normalize_analysis(symbol, direction, raw)
        return normalized

    except Exception as e:
        logger.exception(f"❌ Error analizando {symbol}: {e}")
        return {
            "symbol": symbol,
            "direction": direction,
            "error": True,
            "msg": str(e)
        }


# ============================================================
# FORMATEO TELEGRAM (opcional, no crítico para reactivación)
# ============================================================
def format_analysis_for_telegram(result: dict) -> str:
    if not result or result.get("error"):
        return "⚠️ Error en análisis técnico."

    dec = result.get("decision", {})
    entry = result.get("entry", {})

    return (
        f"📊 *Análisis de {result.get('symbol')} ({result.get('direction')})*\n"
        f"• Decisión: *{dec.get('decision', 'N/A')}*\n"
        f"• Permitido: *{'Sí' if dec.get('allowed') else 'No'}*\n"
        f"• Entrada permitida: *{'Sí' if entry.get('allowed') else 'No'}*\n"
        f"• Score: {entry.get('entry_score', 0)}\n"
    )
