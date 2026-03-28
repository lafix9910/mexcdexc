import os

# Telegram
TELEGRAM_BOT_TOKEN = "8615830576:AAFi9jpOj76E46i2mCl-5gbgLBuTlBnWUQw"
CHAT_ID = os.getenv("CHAT_ID", None)

# Спред
SPREAD_THRESHOLD_PCT = float(os.getenv("SPREAD_THRESHOLD_PCT", "5.0"))
MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", "50000"))

# Интервалы
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "5"))
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", "300"))
CONTRACT_REFRESH_SEC = int(os.getenv("CONTRACT_REFRESH_SEC", "300"))

# Сколько топ токенов MEXC проверять на DEX (по объёму)
TOP_TOKENS_LIMIT = int(os.getenv("TOP_TOKENS_LIMIT", "100"))

# Максимальный спред % — если больше, это скорее всего другой токен
MAX_SPREAD_PCT = float(os.getenv("MAX_SPREAD_PCT", "100.0"))

# Stablecoins — игнорируем
STABLECOINS = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FRAX", "USDE", "MX", "WLFI"}

# MEXC
MEXC_BASE_URL = "https://api.mexc.com"
MEXC_CONTRACT_TICKER = "/api/v1/contract/ticker"
MEXC_CONTRACT_DETAIL = "/api/v1/contract/detail"
