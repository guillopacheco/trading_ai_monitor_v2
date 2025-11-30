# =====================================================================
# formatters.py
# ---------------------------------------------------------------
# Generadores de texto profesional para Telegram.
# Formatos: header, resumen técnico, temporalidades, puntajes.
# =====================================================================

def format_signal_intro(symbol: str, direction: str) -> str:
    d = direction.upper()
    emoji = "📈 LONG" if d.startswith("L") or d == "BUY" else "📉 SHORT"
    return f"🔥 **{symbol}** — {emoji}"


def format_tf_summary(blocks: dict) -> str:
    """
    Muestra los TF 1H/4H/1D con tendencia y score.
    """
    if not blocks:
        return "⚠️ No hay datos técnicos disponibles.\n"

    lines = ["📊 **Temporalidades**"]

    for tf, data in blocks.items():
        trend = data.get("trend_label", "neutral")
        score = data.get("score", 0.5)
        lines.append(f"• **{tf}** → `{trend}` — Score: {score:.2f}")

    return "\n".join(lines) + "\n"


def format_entry_grade(grade: str) -> str:
    color = {
        "A": "🟢",
        "B": "🟡",
        "C": "🟠",
        "D": "🔴",
    }.get(grade, "⚪")

    return f"🎯 **Entrada sugerida:** {color} *Nivel {grade}*\n"


def format_analysis_summary(result: dict) -> str:
    """
    Resumen final del Motor Técnico A+
    """
    score = result.get("global_score", 0.5)
    grade = result.get("entry_grade", "C")
    bias = result.get("bias", "neutral")

    txt = (
        "🧠 **Resumen Técnico A+**\n"
        f"• Score Global: **{score:.2f}**\n"
        f"• Nivel: **{grade}**\n"
        f"• Tendencia predominante: `{bias}`\n"
    )

    return txt
