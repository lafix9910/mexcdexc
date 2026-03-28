import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, CHAT_ID, SPREAD_THRESHOLD_PCT, MIN_LIQUIDITY_USD, POLL_INTERVAL_SEC

logger = logging.getLogger(__name__)


class SpreadBot:
    def __init__(self, app: Application, chat_id: int | None):
        self.app = app
        self.chat_id = chat_id
        self._running = False
        self._stats = {
            "cycles": 0,
            "alerts_sent": 0,
            "last_cycle_time": None,
            "tokens_mexc": 0,
            "tokens_dex": 0,
        }

    async def send_alert(self, text: str):
        if not self.chat_id:
            logger.warning("No chat_id configured, skipping alert")
            return
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
            )
            self._stats["alerts_sent"] += 1
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def update_stats(self, **kwargs):
        self._stats.update(kwargs)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.chat_id is None:
            self.chat_id = user_id
            logger.info(f"Chat ID set to: {user_id}")

        await update.message.reply_text(
            f"Spread Alert Bot - DEX vs MEXC Futures\n\n"
            f"Spread threshold: {SPREAD_THRESHOLD_PCT}%\n"
            f"Min liquidity: ${MIN_LIQUIDITY_USD:,.0f}\n"
            f"Poll interval: {POLL_INTERVAL_SEC} sec\n"
            f"Chat ID: {user_id}\n\n"
            f"Commands:\n"
            f"/status - bot status\n"
            f"/stop - stop monitoring"
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self._stats
        await update.message.reply_text(
            f"Bot Status\n\n"
            f"Cycles: {stats['cycles']}\n"
            f"Alerts sent: {stats['alerts_sent']}\n"
            f"MEXC tokens: {stats['tokens_mexc']}\n"
            f"DEX tokens: {stats['tokens_dex']}\n"
            f"Last cycle: {stats['last_cycle_time'] or 'N/A'}\n"
            f"Running: {'Yes' if self._running else 'No'}"
        )

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._running = False
        await update.message.reply_text("Monitoring stopped.")

    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop))
