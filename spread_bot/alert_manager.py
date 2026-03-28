import logging
from datetime import datetime, timedelta

from spread_calculator import SpreadAlert
from config import ALERT_COOLDOWN_SEC

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self):
        self._last_alert: dict[str, datetime] = {}

    def should_alert(self, alert: SpreadAlert) -> bool:
        now = datetime.utcnow()
        last = self._last_alert.get(alert.key)
        if last and (now - last) < timedelta(seconds=ALERT_COOLDOWN_SEC):
            return False
        return True

    def mark_sent(self, alert: SpreadAlert):
        self._last_alert[alert.key] = datetime.utcnow()

    def get_alerts_to_send(self, alerts: list[SpreadAlert]) -> list[SpreadAlert]:
        to_send = [a for a in alerts if self.should_alert(a)]
        for a in to_send:
            self.mark_sent(a)
        return to_send

    def format_alert(self, alert: SpreadAlert) -> str:
        dex_price_str = self._format_price(alert.dex_price)
        futures_price_str = self._format_price(alert.futures_price)
        liquidity_str = self._format_usd(alert.liquidity_usd)

        return (
            f"[!] SPRED ALERT\n"
            f"-----------------\n"
            f"Token: {alert.symbol}\n"
            f"Chain: {alert.chain.upper()}\n"
            f"DEX price: ${dex_price_str}\n"
            f"MEXC futures: ${futures_price_str}\n"
            f"Spread: {alert.spread_pct}%\n"
            f"Direction: {alert.direction}\n"
            f"DEX liquidity: {liquidity_str}\n"
            f"Funding rate: {alert.funding_rate:.4%}\n"
            f"Time (UTC): {alert.timestamp.strftime('%H:%M:%S')}\n"
            f"-----------------"
        )

    @staticmethod
    def _format_price(price: float) -> str:
        if price >= 1:
            return f"{price:,.4f}"
        elif price >= 0.0001:
            return f"{price:.6f}"
        else:
            return f"{price:.10f}"

    @staticmethod
    def _format_usd(amount: float) -> str:
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:,.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:,.1f}K"
        else:
            return f"${amount:,.0f}"
