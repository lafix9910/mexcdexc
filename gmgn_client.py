import asyncio
import logging
from dataclasses import dataclass, field

import aiohttp

logger = logging.getLogger(__name__)

# DexScreener rate limit: 60 req/min → 1 req/sec safe
DEX_SEARCH_DELAY = 1.1


@dataclass
class DexToken:
    symbol: str
    price_usd: float
    liquidity_usd: float
    volume_usd: float
    chain: str
    address: str
    market_cap: float = 0.0
    pair_name: str = ""


class DexScreenerClient:
    BASE_URL = "https://api.dexscreener.com"

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

    async def search_token(self, symbol: str) -> DexToken | None:
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/latest/dex/search"
        params = {"q": symbol}
        try:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"DexScreener {symbol}: HTTP {resp.status}")
                    return None
                data = await resp.json()
                pairs = data.get("pairs")
                if not pairs:
                    return None

                best = None
                best_liq = 0.0
                for pair in pairs:
                    base = pair.get("baseToken", {})
                    if base.get("symbol", "").upper() != symbol.upper():
                        continue
                    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                    price = pair.get("priceUsd")
                    if not price or liq <= 0:
                        continue
                    if liq > best_liq:
                        best_liq = liq
                        best = pair

                if not best:
                    return None

                base = best.get("baseToken", {})
                volume = best.get("volume", {}).get("h24", 0)
                mcap = best.get("marketCap", 0)

                return DexToken(
                    symbol=base.get("symbol", symbol).upper(),
                    price_usd=float(best.get("priceUsd", 0)),
                    liquidity_usd=best_liq,
                    volume_usd=float(volume or 0),
                    chain=best.get("chainId", "unknown"),
                    address=base.get("address", ""),
                    market_cap=float(mcap or 0),
                    pair_name=best.get("pairAddress", ""),
                )
        except Exception as e:
            logger.debug(f"DexScreener search error for {symbol}: {e}")
            return None

    async def search_tokens_batch(
        self,
        symbols: list[str],
        batch_size: int = 20,
        delay: float = DEX_SEARCH_DELAY,
    ) -> dict[str, DexToken]:
        result: dict[str, DexToken] = {}
        unique = list(set(s.upper() for s in symbols))

        for i in range(0, len(unique), batch_size):
            batch = unique[i : i + batch_size]
            tasks = [self.search_token(sym) for sym in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for sym, res in zip(batch, results):
                if isinstance(res, DexToken):
                    result[sym] = res
                elif isinstance(res, BaseException):
                    logger.debug(f"DexScreener {sym} exception: {res}")

            if i + batch_size < len(unique):
                await asyncio.sleep(delay)

        return result
