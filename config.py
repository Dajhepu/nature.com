import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")

# Monitoring Settings
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 30))
MIN_USD_THRESHOLD = float(os.getenv("MIN_USD_THRESHOLD", 5000))

# Chains
SCAN_APIS = {
    "eth": {"url": "https://api.etherscan.io/api", "key_param": "apikey", "label": "Etherscan"},
    "bsc": {"url": "https://api.bscscan.com/api", "key_param": "apikey", "label": "BSCScan"},
    "base": {"url": "https://api.basescan.org/api", "key_param": "apikey", "label": "Basescan"},
    "arbitrum": {"url": "https://api.arbiscan.io/api", "key_param": "apikey", "label": "Arbiscan"},
    "polygon": {"url": "https://api.polygonscan.com/api", "key_param": "apikey", "label": "Polygonscan"},
    "avalanche": {"url": "https://api.snowtrace.io/api", "key_param": "apikey", "label": "Snowtrace"},
}

# Tokens for filtering
STABLES = {"usdt", "usdc", "dai", "busd", "tusd", "usdp", "frax", "lusd", "gusd", "susd", "cusd", "usd+"}
WRAPPERS = {"weth", "wbnb", "wmatic", "wavax", "wftm"}

# Wallets to monitor (examples from loadDemoTrades)
WALLETS = [
    {
        "addr": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "label": "vitalik.eth",
        "chain": "eth",
        "winRate": "91%",
        "pnl": "+$4.2M",
        "trades30d": 23,
        "notes": "Ethereum co-founder",
    },
    {
        "addr": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
        "label": "Alpha Whale #1",
        "chain": "bsc",
        "winRate": "78%",
        "pnl": "+$890K",
        "trades30d": 41,
        "notes": "BSC meme caller",
    },
]
