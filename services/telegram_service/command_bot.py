# services/telegram_service/command_bot.py
import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger("command_bot")


class CommandBot:
    """
    Bot de comandos (PTB). SOLO registra handlers y delega a ApplicationLayer.
    """

    def __init__(self, application, app_layer):
        self.application = application
        self.app_layer = app_layer

    def register_handlers(self) -> None:
        """API pública (main.py la llama)."""
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("analizar", self.cmd_analizar))
        self.application.add_handler(CommandHandler("estado", self.cmd_estado))

        logger.info("✅ Handlers registrados: /start /help /analizar /estado")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "✅ Trading AI Monitor activo.\n"
            "Comandos:\n"
            "• /analizar <SYMBOL> <long|short>\n"
            "• /estado\n"
            "• /help"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🧭 Ayuda\n" "• /analizar YALAUSDT short\n" "• /estado"
        )

    async def cmd_estado(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Si luego quieres reportar tasks activas, DB counts, etc, lo hacemos aquí.
        await update.message.reply_text("📡 Estado: OK")

    async def cmd_analizar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args or len(context.args) < 2:
                await update.message.reply_text("Uso: /analizar <SYMBOL> <long|short>")
                return

            symbol = context.args[0].upper().strip()
            direction = context.args[1].lower().strip()

            result = await self.app_layer.analyze_symbol(
                symbol, direction, context="entry"
            )

            # Mensaje simple (tu notifier ya formatea “bonito” en otros flujos;
            # aquí respondemos directo al chat del comando)
            decision = result.get("decision", {})
            snap = result.get("snapshot", {})
            grade = decision.get("grade", snap.get("grade", "D"))
            score = decision.get("technical_score", 0)
            match = decision.get("match_ratio", 0)
            conf = int((decision.get("confidence", 0) or 0) * 100)
            dec = decision.get("decision", "wait")

            text = (
                f"📊 *Análisis de {symbol}*\n"
                f"🧭 Contexto: *Entrada*\n\n"
                f"🔴 *Decisión:* `{dec}`\n"
                f"📈 *Score técnico:* {score} / 100\n"
                f"🎯 *Match técnico:* {match} %\n"
                f"🔎 *Confianza:* {conf} %\n"
                f"🏅 *Grade:* {grade}\n"
            )

            reasons = decision.get("decision_reasons") or []
            if reasons:
                text += "\n📌 *Motivos:*\n" + "\n".join([f"• {r}" for r in reasons])

            await update.message.reply_markdown(text)

        except Exception as e:
            logger.exception(f"❌ Error en /analizar: {e}")
            await update.message.reply_text(f"❌ Error en análisis: {e}")
