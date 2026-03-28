import asyncio
import logging
import signal
import sys
from datetime import datetime

from telegram.ext import Application

from config import (
    TELEGRAM_BOT_TOKEN,
    POLL_INTERVAL_SEC,
    CONTRACT_REFRESH_SEC,
    TOP_TOKENS_LIMIT,
    STABLECOINS,
)
from mexc_client import MexcClient
from gmgn_client import DexScreenerClient
from spread_calculator import calculate_spreads
from alert_manager import AlertManager
from bot import SpreadBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("spread_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main_loop(
    bot: SpreadBot,
    mexc: MexcClient,
    dex: DexScreenerClient,
    alerts: AlertManager,
):
    dex_cache: dict = {}
    dex_cache_time: float = 0
    loop = asyncio.get_event_loop()

    bot._running = True
    logger.info("Starting main loop...")

    while bot._running:
        cycle_start = datetime.utcnow()

        try:
            # 1. Получаем все фьючерсы с MEXC
            mexc_tickers = await mexc.get_all_futures_tickers()
            if not mexc_tickers:
                logger.warning("No MEXC tickers received")
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            # 2. Обновляем кэш DEX цен если пора
            now_ts = loop.time()
            if not dex_cache or (now_ts - dex_cache_time) > CONTRACT_REFRESH_SEC:
                logger.info("Refreshing DEX price cache via DexScreener...")

                # Берём топ токенов по объёму
                sorted_tickers = sorted(
                    mexc_tickers,
                    key=lambda t: t.volume_24h,
                    reverse=True,
                )[:TOP_TOKENS_LIMIT]

                symbols = [
                    t.base_coin.upper()
                    for t in sorted_tickers
                    if t.base_coin.upper() not in STABLECOINS
                ]

                dex_cache = await dex.search_tokens_batch(symbols)
                dex_cache_time = now_ts
                logger.info(
                    f"DEX cache refreshed: {len(dex_cache)} tokens "
                    f"out of {len(symbols)} searched"
                )

            # 3. Считаем спреды
            spread_alerts = calculate_spreads(mexc_tickers, dex_cache)

            # 4. Отправляем алерты
            to_send = alerts.get_alerts_to_send(spread_alerts)
            for alert in to_send:
                text = alerts.format_alert(alert)
                await bot.send_alert(text)
                logger.info(
                    f"Alert: {alert.symbol} ({alert.chain}) "
                    f"spread={alert.spread_pct}%"
                )

            # 5. Обновляем статистику
            bot.update_stats(
                cycles=bot._stats["cycles"] + 1,
                tokens_mexc=len(mexc_tickers),
                tokens_dex=len(dex_cache),
                last_cycle_time=cycle_start.strftime("%H:%M:%S"),
            )

            if spread_alerts:
                logger.info(
                    f"Cycle: {len(spread_alerts)} spreads found, "
                    f"{len(to_send)} alerts sent"
                )

        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)

        elapsed = (datetime.utcnow() - cycle_start).total_seconds()
        sleep_time = max(0, POLL_INTERVAL_SEC - elapsed)
        await asyncio.sleep(sleep_time)

    logger.info("Main loop stopped.")


async def run():
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "Set TELEGRAM_BOT_TOKEN environment variable or edit config.py"
        )
        sys.exit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot = SpreadBot(app, chat_id=None)
    bot.setup_handlers()

    mexc = MexcClient()
    dex = DexScreenerClient()
    alert_mgr = AlertManager()

    logger.info("Starting Telegram bot...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot started. Send /start to register your chat.")

    loop_task = asyncio.create_task(main_loop(bot, mexc, dex, alert_mgr))

    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received")
        bot._running = False
        stop_event.set()

    if sys.platform != "win32":
        ev_loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            ev_loop.add_signal_handler(sig, handle_signal)

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
        bot._running = False

    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass

    await mexc.close()
    await dex.close()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Bot stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(run())
