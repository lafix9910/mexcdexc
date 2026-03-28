import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

from config import MEXC_BASE_URL, MEXC_CONTRACT_TICKER, STABLECOINS

logger = logging.getLogger(__name__)


@dataclass
class MexcFuturesTicker:
    symbol: str
    base_coin: str
    last_price: float
    fair_price: float
    funding_rate: float
    volume_24h: float
    timestamp: int


class MexcClient:
    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._own_session = session is None
        self._session = session

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def get_all_futures_tickers(self) -> list[MexcFuturesTicker]:
        session = await self._ensure_session()
        url = f"{MEXC_BASE_URL}{MEXC_CONTRACT_TICKER}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.error(f"MEXC ticker request failed: {resp.status}")
                    return []
                json_data = await resp.json()
                if not json_data.get("success"):
                    logger.error(f"MEXC API error: {json_data}")
                    return []

                tickers = []
                for item in json_data["data"]:
                    symbol = item.get("symbol", "")
                    if not symbol:
                        continue
                    base_coin = symbol.split("_")[0] if "_" in symbol else symbol
                    if base_coin in STABLECOINS:
                        continue

                    last_price = item.get("lastPrice") or item.get("fairPrice")
                    if not last_price or last_price == 0:
                        continue

                    tickers.append(MexcFuturesTicker(
                        symbol=symbol,
                        base_coin=base_coin,
                        last_price=float(last_price),
                        fair_price=float(item.get("fairPrice", last_price)),
                        funding_rate=float(item.get("fundingRate", 0)),
                        volume_24h=float(item.get("amount24", 0)),
                        timestamp=int(item.get("timestamp", 0)),
                    ))
                return tickers
        except Exception as e:
            logger.error(f"MEXC fetch error: {e}")
            return []

    async def get_fair_price(self, symbol: str) -> Optional[float]:
        session = await self._ensure_session()
        url = f"{MEXC_BASE_URL}/api/v1/contract/fair_price/{symbol}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                json_data = await resp.json()
                if json_data.get("success") and json_data.get("data"):
                    return float(json_data["data"]["fairPrice"])
        except Exception as e:
            logger.error(f"MEXC fair_price error for {symbol}: {e}")
        return None
