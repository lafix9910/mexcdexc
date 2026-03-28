import logging
from dataclasses import dataclass
from datetime import datetime

from mexc_client import MexcFuturesTicker
from gmgn_client import DexToken
from config import SPREAD_THRESHOLD_PCT, MIN_LIQUIDITY_USD, MAX_SPREAD_PCT

logger = logging.getLogger(__name__)

# Минимальный объём торгов на DEX (24h)
MIN_DEX_VOLUME_USD = 1000.0
# Максимальное отношение цен DEX/MEXC (фильтр "wrong token")
MAX_PRICE_RATIO = 10.0


@dataclass
class SpreadAlert:
    symbol: str
    chain: str
    dex_price: float
    futures_price: float
    spread_pct: float
    direction: str
    liquidity_usd: float
    volume_usd: float
    funding_rate: float
    timestamp: datetime

    @property
    def key(self) -> str:
        return f"{self.symbol}_{self.chain}"


def calculate_spreads(
    mexc_tickers: list[MexcFuturesTicker],
    dex_index: dict[str, DexToken],
) -> list[SpreadAlert]:
    alerts: list[SpreadAlert] = []

    for ticker in mexc_tickers:
        symbol = ticker.base_coin.upper()
        dex_token = dex_index.get(symbol)
        if not dex_token:
            continue

        if dex_token.liquidity_usd < MIN_LIQUIDITY_USD:
            continue
        if dex_token.price_usd <= 0 or ticker.fair_price <= 0:
            continue
        if dex_token.volume_usd < MIN_DEX_VOLUME_USD:
            continue

        price_ratio = dex_token.price_usd / ticker.fair_price
        if price_ratio > MAX_PRICE_RATIO or price_ratio < 1 / MAX_PRICE_RATIO:
            continue

        spread_pct = abs(dex_token.price_usd - ticker.fair_price) / ticker.fair_price * 100

        if spread_pct < SPREAD_THRESHOLD_PCT:
            continue
        if spread_pct > MAX_SPREAD_PCT:
            continue

        if dex_token.price_usd > ticker.fair_price:
            direction = "DEX higher -> short MEXC / long DEX"
        else:
            direction = "MEXC higher -> long MEXC / short DEX"

        alerts.append(SpreadAlert(
            symbol=symbol,
            chain=dex_token.chain,
            dex_price=dex_token.price_usd,
            futures_price=ticker.fair_price,
            spread_pct=round(spread_pct, 2),
            direction=direction,
            liquidity_usd=dex_token.liquidity_usd,
            volume_usd=dex_token.volume_usd,
            funding_rate=ticker.funding_rate,
            timestamp=datetime.utcnow(),
        ))

    alerts.sort(key=lambda a: a.spread_pct, reverse=True)
    return alerts
