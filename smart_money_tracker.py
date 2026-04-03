"""
╔══════════════════════════════════════════════════════════════╗
║         💎 Smart Money Finder & Tracker  v1.0              ║
║   Blockchain smart wallet discovery & real-time alerts      ║
╚══════════════════════════════════════════════════════════════╝

O'rnatish:
    pip install python-telegram-bot aiohttp aiosqlite python-dotenv colorlog

Ishga tushirish:
    python smart_money_tracker.py
"""

# ═══════════════════════════════════════════════════════════════
#  IMPORTS
# ═══════════════════════════════════════════════════════════════

import asyncio
import logging
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import aiosqlite
import colorlog
from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()


# ═══════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════

def _setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_red",
        },
    ))
    file_handler = logging.FileHandler("smart_money.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(file_handler)
    for lib in ("httpx", "httpcore", "telegram", "aiohttp"):
        logging.getLogger(lib).setLevel(logging.WARNING)

log = logging.getLogger("SmartMoney")


# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════

@dataclass
class ChainConfig:
    name: str
    chain_id: int
    native_symbol: str
    dexscreener_id: str
    gecko_id: str
    explorer_url: str
    explorer_api: str
    api_key_env: str
    llama_slug: str


CHAINS: Dict[str, ChainConfig] = {
    "ethereum": ChainConfig(
        name="Ethereum", chain_id=1, native_symbol="ETH",
        dexscreener_id="ethereum", gecko_id="eth",
        explorer_url="https://etherscan.io",
        explorer_api="https://api.etherscan.io/api",
        api_key_env="ETHERSCAN_API_KEY", llama_slug="ethereum",
    ),
    "bsc": ChainConfig(
        name="BSC", chain_id=56, native_symbol="BNB",
        dexscreener_id="bsc", gecko_id="bsc",
        explorer_url="https://bscscan.com",
        explorer_api="https://api.bscscan.com/api",
        api_key_env="BSCSCAN_API_KEY", llama_slug="bsc",
    ),
    "base": ChainConfig(
        name="Base", chain_id=8453, native_symbol="ETH",
        dexscreener_id="base", gecko_id="base",
        explorer_url="https://basescan.org",
        explorer_api="https://api.basescan.org/api",
        api_key_env="BASESCAN_API_KEY", llama_slug="base",
    ),
    "arbitrum": ChainConfig(
        name="Arbitrum", chain_id=42161, native_symbol="ETH",
        dexscreener_id="arbitrum", gecko_id="arbitrum",
        explorer_url="https://arbiscan.io",
        explorer_api="https://api.arbiscan.io/api",
        api_key_env="ARBISCAN_API_KEY", llama_slug="arbitrum",
    ),
    "polygon": ChainConfig(
        name="Polygon", chain_id=137, native_symbol="MATIC",
        dexscreener_id="polygon", gecko_id="polygon_pos",
        explorer_url="https://polygonscan.com",
        explorer_api="https://api.polygonscan.com/api",
        api_key_env="POLYGONSCAN_API_KEY", llama_slug="polygon",
    ),
    "avalanche": ChainConfig(
        name="Avalanche", chain_id=43114, native_symbol="AVAX",
        dexscreener_id="avalanche", gecko_id="avalanche",
        explorer_url="https://snowtrace.io",
        explorer_api="https://api.snowtrace.io/api",
        api_key_env="SNOWTRACE_API_KEY", llama_slug="avalanche",
    ),
    "solana": ChainConfig(
        name="Solana", chain_id=0, native_symbol="SOL",
        dexscreener_id="solana", gecko_id="solana",
        explorer_url="https://solscan.io",
        explorer_api="https://public-api.solscan.io",
        api_key_env="", llama_slug="solana",
    ),
}

CHAIN_EMOJI: Dict[str, str] = {
    "ethereum":  "⟠",
    "bsc":       "🟡",
    "base":      "🔵",
    "arbitrum":  "🔷",
    "polygon":   "🟣",
    "avalanche": "🔺",
    "solana":    "◎",
}

EMOJI = {
    "wallet":  "👛", "profit":  "💰", "loss":    "📉",
    "fire":    "🔥", "search":  "🔍", "check":   "✅",
    "cross":   "❌", "warning": "⚠️", "rocket":  "🚀",
    "chart":   "📊", "clock":   "⏰", "bell":    "🔔",
    "star":    "⭐", "diamond": "💎", "add":     "➕",
    "remove":  "➖", "list":    "📋", "link":    "🔗",
    "buy":     "🟢", "sell":    "🔴",
}

# ── API URLs ──────────────────────────────────────────────────
DEXSCREENER_TRENDING = "https://api.dexscreener.com/token-boosts/top/v1"
DEXSCREENER_LATEST   = "https://api.dexscreener.com/token-boosts/latest/v1"
DEXSCREENER_TOKENS   = "https://api.dexscreener.com/latest/dex/tokens"
GECKO_TRENDING       = "https://api.geckoterminal.com/api/v2/networks/{}/trending_pools"
GECKO_TRADES         = "https://api.geckoterminal.com/api/v2/networks/{}/pools/{}/trades"
SOLSCAN_BASE         = "https://public-api.solscan.io"
LLAMA_BASE           = "https://coins.llama.fi"


@dataclass
class AppConfig:
    bot_token:       str   = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "8489499074:AAEbc1ZNVEBprLhPhnoiY0orE4oRmno9UYM"))
    allowed_users:   List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ALLOWED_USER_IDS", "798283148").split(",") if x.strip()
    ])
    min_win_rate:    float = field(default_factory=lambda: float(os.getenv("MIN_WIN_RATE", "50")))
    min_pnl_usd:     float = field(default_factory=lambda: float(os.getenv("MIN_PNL_USD", "1000")))
    min_trade_count: int   = field(default_factory=lambda: int(os.getenv("MIN_TRADE_COUNT", "5")))
    min_tx_history:  int   = field(default_factory=lambda: int(os.getenv("MIN_TX_HISTORY", "100")))
    monitor_interval:    int = field(default_factory=lambda: int(os.getenv("MONITOR_INTERVAL", "30")))
    discovery_interval:  int = field(default_factory=lambda: int(os.getenv("DISCOVERY_INTERVAL", "3600")))
    db_path:         str   = field(default_factory=lambda: os.getenv("DATABASE_PATH", "smart_money.db"))
    active_chains:   List[str] = field(default_factory=lambda: list(CHAINS.keys()))

    async def reload(self, db):
        self.min_win_rate = float(await db.get_setting("min_win_rate", self.min_win_rate))
        self.min_pnl_usd  = float(await db.get_setting("min_pnl_usd", self.min_pnl_usd))


CFG = AppConfig()


# ═══════════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════════

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS wallets (
    address     TEXT NOT NULL,
    chain       TEXT NOT NULL,
    label       TEXT DEFAULT '',
    win_rate    REAL DEFAULT 0,
    total_pnl   REAL DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    added_at    TEXT NOT NULL,
    last_seen   TEXT,
    is_active   INTEGER DEFAULT 1,
    PRIMARY KEY (address, chain)
);
CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet       TEXT NOT NULL,
    chain        TEXT NOT NULL,
    tx_hash      TEXT NOT NULL UNIQUE,
    action       TEXT NOT NULL,
    token_addr   TEXT NOT NULL,
    token_name   TEXT DEFAULT '',
    token_symbol TEXT DEFAULT '',
    amount_usd   REAL DEFAULT 0,
    price_usd    REAL DEFAULT 0,
    timestamp    TEXT NOT NULL,
    notified     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS discovery_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at              TEXT NOT NULL,
    chain               TEXT NOT NULL,
    token_addr          TEXT NOT NULL,
    wallets_found       INTEGER DEFAULT 0,
    wallets_qualified   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_tx_wallet   ON transactions (wallet, chain);
CREATE INDEX IF NOT EXISTS idx_tx_notified ON transactions (notified);
CREATE INDEX IF NOT EXISTS idx_w_active    ON wallets (is_active);
"""


class Database:
    def __init__(self, path: str = CFG.db_path):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_CREATE_TABLES)
        await self._conn.commit()
        log.info(f"Database: {self.path}")

    async def close(self):
        if self._conn:
            await self._conn.close()

    # ── Wallets ───────────────────────────────────────────────

    async def upsert_wallet(self, address: str, chain: str,
                             stats: Dict, label: str = "") -> bool:
        now = datetime.utcnow().isoformat()
        async with self._conn.execute(
            "SELECT address FROM wallets WHERE address=? AND chain=?",
            (address, chain)
        ) as cur:
            exists = await cur.fetchone()

        if exists:
            await self._conn.execute(
                """UPDATE wallets SET win_rate=?, total_pnl=?, trade_count=?,
                   last_seen=?, is_active=1 WHERE address=? AND chain=?""",
                (stats["win_rate"], stats["total_pnl"],
                 stats["trade_count"], now, address, chain),
            )
        else:
            await self._conn.execute(
                """INSERT INTO wallets (address, chain, label, win_rate, total_pnl,
                   trade_count, added_at, last_seen, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (address, chain, label, stats["win_rate"],
                 stats["total_pnl"], stats["trade_count"], now, now),
            )
        await self._conn.commit()
        return not bool(exists)

    async def add_wallet(self, address: str, chain: str, label: str = "") -> bool:
        return await self.upsert_wallet(
            address, chain,
            {"win_rate": 0, "total_pnl": 0, "trade_count": 0},
            label=label,
        )

    async def remove_wallet(self, address: str, chain: str) -> bool:
        async with self._conn.execute(
            "UPDATE wallets SET is_active=0 WHERE address=? AND chain=?",
            (address, chain)
        ) as cur:
            await self._conn.commit()
            return cur.rowcount > 0

    async def get_wallet(self, address: str, chain: str) -> Optional[Dict]:
        async with self._conn.execute(
            "SELECT * FROM wallets WHERE address=? AND chain=?",
            (address, chain)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_wallets(self, active_only: bool = True) -> List[Dict]:
        q = "SELECT * FROM wallets" + (" WHERE is_active=1" if active_only else "")
        q += " ORDER BY total_pnl DESC"
        async with self._conn.execute(q) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ── Transactions ──────────────────────────────────────────

    async def save_tx(self, wallet: str, chain: str, tx: Dict) -> bool:
        try:
            await self._conn.execute(
                """INSERT OR IGNORE INTO transactions
                   (wallet, chain, tx_hash, action, token_addr, token_name,
                    token_symbol, amount_usd, price_usd, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (wallet, chain, tx["hash"], tx["action"], tx["token_addr"],
                 tx.get("token_name", ""), tx.get("token_symbol", ""),
                 tx.get("amount_usd", 0), tx.get("price_usd", 0),
                 tx["timestamp"]),
            )
            await self._conn.commit()
            async with self._conn.execute("SELECT changes()") as cur:
                return (await cur.fetchone())[0] > 0
        except Exception as e:
            log.error(f"save_tx: {e}")
            return False

    async def get_wallet_txs(self, wallet: str, chain: str,
                              limit: int = 5) -> List[Dict]:
        async with self._conn.execute(
            """SELECT * FROM transactions WHERE wallet=? AND chain=?
               ORDER BY timestamp DESC LIMIT ?""",
            (wallet, chain, limit)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ── Stats ─────────────────────────────────────────────────

    async def global_summary(self) -> Dict:
        async with self._conn.execute(
            "SELECT COUNT(*) t, SUM(is_active) a FROM wallets"
        ) as cur:
            w = await cur.fetchone()
        async with self._conn.execute(
            "SELECT COUNT(*) t FROM transactions"
        ) as cur:
            t = await cur.fetchone()
        async with self._conn.execute(
            "SELECT COUNT(*) t FROM discovery_log"
        ) as cur:
            d = await cur.fetchone()
        return {"total": w[0], "active": w[1] or 0,
                "transactions": t[0], "discoveries": d[0]}

    async def log_discovery(self, chain: str, token_addr: str,
                             found: int, qualified: int):
        await self._conn.execute(
            """INSERT INTO discovery_log
               (run_at, chain, token_addr, wallets_found, wallets_qualified)
               VALUES (?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), chain, token_addr, found, qualified),
        )
        await self._conn.commit()

    # ── Settings ──────────────────────────────────────────────

    async def get_setting(self, key: str, default: Any = None) -> Any:
        async with self._conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

    async def set_setting(self, key: str, value: Any):
        await self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        await self._conn.commit()


DB = Database()


# ═══════════════════════════════════════════════════════════════
#  HTTP HELPER
# ═══════════════════════════════════════════════════════════════

_HTTP_SESSION: Optional[aiohttp.ClientSession] = None

async def _get_session() -> aiohttp.ClientSession:
    global _HTTP_SESSION
    if _HTTP_SESSION is None or _HTTP_SESSION.closed:
        import socket

        # Try to use aiodns resolver for faster/more reliable resolution
        resolver = None
        try:
            from aiohttp.resolver import AsyncResolver
            resolver = AsyncResolver(nameservers=["1.1.1.1", "8.8.8.8"])
        except Exception:
            pass

        # Use a connector to force IPv4 and enable DNS caching to combat flaky mobile DNS
        connector = aiohttp.TCPConnector(
            family=socket.AF_INET,
            resolver=resolver,
            use_dns_cache=True,
            ttl_dns_cache=300,
            limit=50
        )
        _HTTP_SESSION = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=45, connect=15),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            trust_env=True
        )
    return _HTTP_SESSION

async def _http_get(url: str, headers: Optional[Dict] = None,
                    params: Optional[Dict] = None, retries: int = 3) -> Optional[Any]:
    for attempt in range(retries):
        try:
            sess = await _get_session()
            async with sess.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()

                if resp.status == 429 and attempt < retries - 1:
                    # Specific wait for rate limits
                    wait = 5 + (2 ** attempt)
                    log.warning(f"🛑 Rate Limit (429): {url}. {wait}s kutilmoqda…")
                    await asyncio.sleep(wait)
                    continue

                if resp.status in (500, 502, 503, 504) and attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

                log.warning(f"HTTP {resp.status}: {url}")
                return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            ename = type(e).__name__
            if "DNSError" in ename or "DNS" in str(e):
                log.warning(f"🌐 DNS Xatoligi ({attempt+1}/{retries}): {url}. "
                            "Yechim: Telefoningizda Private DNS -> 1.1.1.1 yoki VPN yoqing.")

            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            log.error(f"HTTP error ({ename}): {url} -> {e}")
            return None
    return None


# ═══════════════════════════════════════════════════════════════
#  TRENDING DISCOVERY (DexScreener & GeckoTerminal)
# ═══════════════════════════════════════════════════════════════

async def discovery_trending(chain: str) -> List[Dict]:
    """Unified trending discovery with GeckoTerminal fallback."""
    # 1. Try DexScreener
    dex_tokens = await dex_trending(chain)
    if dex_tokens:
        return [_parse_dex_pair(t) for t in dex_tokens]

    # 2. Fallback to GeckoTerminal
    log.info(f"[{chain}] Falling back to GeckoTerminal for discovery")
    gecko_data = await gecko_trending(chain)
    if gecko_data:
        return [_parse_gecko_pool(p, chain) for p in gecko_data]

    return []


async def dex_trending(chain: Optional[str] = None) -> List[Dict]:
    data = await _http_get(DEXSCREENER_TRENDING)
    if not data:
        data = await _http_get(DEXSCREENER_LATEST)
    if not data:
        return []
    tokens = data if isinstance(data, list) else data.get("pairs", [])
    if chain:
        did = CHAINS[chain].dexscreener_id if chain in CHAINS else chain
        tokens = [t for t in tokens
                  if t.get("chainId", "").lower() == did.lower()]
    return tokens[:50]


async def gecko_trending(chain: str) -> List[Dict]:
    cfg = CHAINS.get(chain)
    if not cfg: return []
    url = GECKO_TRENDING.format(cfg.gecko_id)
    data = await _http_get(url)
    if data and "data" in data:
        return data["data"][:30]
    return []


def _parse_dex_pair(pair: Dict) -> Dict:
    base  = pair.get("baseToken", {})
    vol   = pair.get("volume", {})
    liq   = pair.get("liquidity", {})
    pchg  = pair.get("priceChange", {})
    return {
        "pair_address":   pair.get("pairAddress", ""),
        "chain":          pair.get("chainId", ""),
        "token_address":  base.get("address", ""),
        "token_name":     base.get("name", "Unknown"),
        "token_symbol":   base.get("symbol", "???"),
        "price_usd":      float(pair.get("priceUsd", 0) or 0),
        "volume_24h":     float(vol.get("h24", 0) or 0),
        "liquidity_usd":  float(liq.get("usd", 0) or 0),
        "price_change_24h": float(pchg.get("h24", 0) or 0),
        "pair_created_at": pair.get("pairCreatedAt", 0),
        "url":            pair.get("url", ""),
    }


def _parse_gecko_pool(pool: Dict, chain: str) -> Dict:
    attr  = pool.get("attributes", {})
    rel   = pool.get("relationships", {})
    # GeckoTerminal pools have base and quote.
    # Usually the first base_token is what we want.
    base_toks = rel.get("base_token", {}).get("data", [])
    token_addr = ""
    if base_toks:
        # data is usually a single object or list with 'id' like "network_addr"
        tid = base_toks[0].get("id", "") if isinstance(base_toks, list) else base_toks.get("id", "")
        token_addr = tid.split("_")[-1] if "_" in tid else tid

    return {
        "pair_address":   attr.get("address", ""),
        "chain":          chain,
        "token_address":  token_addr,
        "token_name":     attr.get("name", "Unknown"),
        "token_symbol":   attr.get("symbol", "???"),
        "price_usd":      float(attr.get("price_usd", 0) or 0),
        "volume_24h":     float(attr.get("volume_usd", {}).get("h24", 0) or 0),
        "liquidity_usd":  float(attr.get("reserve_in_usd", 0) or 0),
        "price_change_24h": float(attr.get("price_change_percentage", {}).get("h24", 0) or 0),
        "pair_created_at": 0,
        "url":            f"https://www.geckoterminal.com/{CHAINS[chain].gecko_id}/pools/{attr.get('address')}",
    }


# ═══════════════════════════════════════════════════════════════
#  BLOCKCHAIN  —  transaction fetchers
# ═══════════════════════════════════════════════════════════════

# ── Explorer (Etherscan-compatible) ───────────────────────────

async def explorer_tokentx(address: str, chain: str,
                             limit: int = 200) -> List[Dict]:
    if chain not in CHAINS or chain == "solana":
        return []
    cfg     = CHAINS[chain]
    api_key = os.getenv(cfg.api_key_env, "")
    params  = {"module": "account", "action": "tokentx",
               "address": address, "sort": "desc",
               "offset": limit, "page": 1}
    if api_key:
        params["apikey"] = api_key
    data = await _http_get(cfg.explorer_api, params=params)
    if not data or data.get("status") != "1":
        return []
    return data.get("result", [])


def _normalize_explorer(address: str, raw: List[Dict]) -> List[Dict]:
    out     = []
    wal_low = address.lower()
    for tx in raw:
        try:
            is_buy = tx.get("to", "").lower() == wal_low
            ts_int = int(tx.get("timeStamp", "0"))
            ts = datetime.fromtimestamp(
                ts_int, tz=timezone.utc
            ).isoformat()
            out.append({
                "hash":         tx.get("hash", ""),
                "action":       "buy" if is_buy else "sell",
                "token_addr":   tx.get("contractAddress", ""),
                "token_name":   tx.get("tokenName", ""),
                "token_symbol": tx.get("tokenSymbol", ""),
                "amount_usd":   0.0,
                "price_usd":    0.0,
                "timestamp":    ts,
                # Store raw values for enrichment
                "_ts_int":      ts_int,
                "_raw_value":   tx.get("value", "0"),
                "_raw_decimal": tx.get("tokenDecimal", "18"),
            })
        except Exception:
            pass
    return out


async def explorer_early_buyers(token_address: str, chain: str,
                                  top_n: int = 50) -> List[str]:
    if chain not in CHAINS or chain == "solana":
        return []
    cfg     = CHAINS[chain]
    api_key = os.getenv(cfg.api_key_env, "")

    # We use both v1 and try to be compatible with newer explorer APIs
    # tokentx with sort=asc gives us the very first transfers of this token
    params  = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": token_address,
        "sort": "asc",
        "offset": 100,
        "page": 1
    }
    if api_key:
        params["apikey"] = api_key

    data = await _http_get(cfg.explorer_api, params=params)

    # Some explorers return "0" status but still have data in result for some reason,
    # or the result is a list directly.
    result = []
    if isinstance(data, dict):
        result = data.get("result", [])
    elif isinstance(data, list):
        result = data

    if not isinstance(result, list):
        return []

    seen: set  = set()
    buyers: List[str] = []

    # Filter out common non-wallet addresses (null address, the token itself)
    ignored = {"0x0000000000000000000000000000000000000000", token_address.lower()}

    for tx in result:
        addr = tx.get("to", "").lower()
        if addr and addr not in seen and addr not in ignored:
            # Simple heuristic: if it's a contract, skip it?
            # Hard to know without another API call.
            # For now, just collect.
            seen.add(addr)
            buyers.append(addr)
            if len(buyers) >= top_n:
                break
    return buyers


# ── Solana (Solscan) ──────────────────────────────────────────

async def solana_defi(address: str, limit: int = 100) -> List[Dict]:
    url  = f"{SOLSCAN_BASE}/account/defiActivities"
    data = await _http_get(url, params={"account": address,
                                         "limit": limit, "offset": 0})
    return data.get("data", []) if data else []


async def solana_early_buyers(token_mint: str, top_n: int = 50) -> List[str]:
    url  = f"{SOLSCAN_BASE}/token/holders"
    data = await _http_get(url, params={"tokenAddress": token_mint,
                                         "limit": top_n, "offset": 0})
    if not data:
        return []
    holders = data.get("data", [])
    return [h.get("owner", h.get("address", "")) for h in holders
            if h.get("owner") or h.get("address")]


def _normalize_solana(raw: List[Dict]) -> List[Dict]:
    out = []
    for tx in raw:
        try:
            act = tx.get("type", "").lower()
            if act not in ("buy", "sell"):
                act = "buy"
            out.append({
                "hash":         tx.get("txHash", ""),
                "action":       act,
                "token_addr":   tx.get("tokenAddress", ""),
                "token_name":   tx.get("tokenName", ""),
                "token_symbol": tx.get("tokenSymbol", ""),
                "amount_usd":   float(tx.get("usdValue", 0) or 0),
                "price_usd":    float(tx.get("price", 0) or 0),
                "timestamp":    str(tx.get("blockTime",
                                            datetime.now(timezone.utc).isoformat())),
            })
        except Exception:
            pass
    return out


# ── Price Enrichment (DeFiLlama & DexScreener) ────────────────

async def get_historical_price_llama(chain: str, token_addr: str,
                                     timestamp: int) -> float:
    """Fetch historical USD price from DeFiLlama."""
    cfg = CHAINS.get(chain)
    if not cfg or not cfg.llama_slug:
        return 0.0

    coin_id = f"{cfg.llama_slug}:{token_addr}"
    url = f"{LLAMA_BASE}/prices/historical/{timestamp}/{coin_id}"
    data = await _http_get(url)
    if data and "coins" in data and coin_id in data["coins"]:
        return float(data["coins"][coin_id].get("price", 0))
    return 0.0


async def get_token_prices_dex(token_addresses: List[str]) -> Dict[str, float]:
    """Fetch current USD prices for a list of tokens from DexScreener."""
    if not token_addresses:
        return {}
    # DexScreener API handles up to 30 tokens at once
    out = {}
    for i in range(0, len(token_addresses), 30):
        batch = token_addresses[i:i+30]
        url = f"{DEXSCREENER_TOKENS}/{','.join(batch)}"
        data = await _http_get(url)
        if data and "pairs" in data:
            for pair in data["pairs"]:
                addr = pair.get("baseToken", {}).get("address", "").lower()
                price = float(pair.get("priceUsd", 0) or 0)
                if addr and price > 0:
                    out[addr] = price
    return out


# ── Unified Fetcher ───────────────────────────────────────────

_PRICE_CACHE: Dict[str, float] = {}

async def get_swap_history(address: str, chain: str,
                            limit: int = 100) -> List[Dict]:
    if chain == "solana":
        return _normalize_solana(await solana_defi(address, limit))

    raw_txs = await explorer_tokentx(address, chain, limit)
    normalized = _normalize_explorer(address, raw_txs)
    if not normalized:
        return []

    # Enrich with historical prices for PnL calculation
    semaphore = asyncio.Semaphore(5) # Reduced concurrency for free APIs

    async def enrich_tx(tx):
        cache_key = f"{chain}:{tx['token_addr']}:{tx['_ts_int'] // 3600}" # Hourly cache
        if cache_key in _PRICE_CACHE:
            tx["price_usd"] = _PRICE_CACHE[cache_key]
            try:
                val = int(tx.get("_raw_value", 0))
                dec = int(tx.get("_raw_decimal", 18))
                tx["amount_usd"] = (val / (10**dec)) * tx["price_usd"]
            except Exception: pass
            return tx

        async with semaphore:
            # Add a small stagger to avoid bursts
            await asyncio.sleep(0.1)
            price = await get_historical_price_llama(chain, tx["token_addr"], tx["_ts_int"])
            if price > 0:
                _PRICE_CACHE[cache_key] = price
                tx["price_usd"] = price
                try:
                    val = int(tx.get("_raw_value", 0))
                    dec = int(tx.get("_raw_decimal", 18))
                    tx["amount_usd"] = (val / (10**dec)) * price
                except Exception:
                    pass
            return tx

    # Enrich in parallel
    tasks = [enrich_tx(tx) for tx in normalized]
    await asyncio.gather(*tasks)

    # Fallback to current DexScreener prices for any missing prices
    missing_addrs = list(set(tx["token_addr"] for tx in normalized if tx["price_usd"] == 0))
    if missing_addrs:
        current_prices = await get_token_prices_dex(missing_addrs)
        for tx in normalized:
            if tx["price_usd"] == 0:
                addr = tx["token_addr"].lower()
                if addr in current_prices:
                    tx["price_usd"] = current_prices[addr]
                    try:
                        val = int(tx.get("_raw_value", 0))
                        dec = int(tx.get("_raw_decimal", 18))
                        tx["amount_usd"] = (val / (10**dec)) * current_prices[addr]
                    except Exception:
                        pass

    return normalized


async def get_gecko_pool_trades(chain: str, pool_address: str) -> List[str]:
    """Fetch recent trade makers from a GeckoTerminal pool."""
    cfg = CHAINS.get(chain)
    if not cfg: return []
    url = GECKO_TRADES.format(cfg.gecko_id, pool_address)
    data = await _http_get(url)
    if not data or "data" not in data:
        return []

    makers = set()
    for t in data["data"]:
        attr = t.get("attributes", {})
        maker = attr.get("tx_from_address")
        if maker:
            makers.add(maker.lower())
    return list(makers)


async def get_early_buyers(token_address: str, chain: str,
                            top_n: int = 50, pool_address: str = "") -> List[str]:
    """Combine explorers and GeckoTerminal for discovery."""
    buyers = []

    # 1. Explorer (True early buyers)
    if chain != "solana":
        early = await explorer_early_buyers(token_address, chain, top_n=top_n)
        buyers.extend(early)
    else:
        early = await solana_early_buyers(token_address, top_n=top_n)
        buyers.extend(early)

    # 2. Gecko (Currently active buyers/makers)
    if pool_address:
        active = await get_gecko_pool_trades(chain, pool_address)
        buyers.extend(active)

    return list(set(buyers))


# ═══════════════════════════════════════════════════════════════
#  WALLET ANALYZER
# ═══════════════════════════════════════════════════════════════

@dataclass
class TradeRecord:
    token_addr: str
    buys:  List[float] = field(default_factory=list)
    sells: List[float] = field(default_factory=list)

    @property
    def is_closed(self) -> bool:
        return bool(self.sells)

    @property
    def pnl(self) -> float:
        return sum(self.sells) - sum(self.buys)

    @property
    def is_profitable(self) -> bool:
        return self.pnl > 0


@dataclass
class WalletStats:
    address:          str
    chain:            str
    win_rate:         float = 0.0
    total_pnl:        float = 0.0
    trade_count:      int   = 0
    profitable_trades: int  = 0
    total_trades:     int   = 0
    avg_trade_size:   float = 0.0
    best_trade:       float = 0.0
    worst_trade:      float = 0.0
    qualifies:        bool  = False
    score:            float = 0.0

    def compute_score(self) -> float:
        self.score = (
            min(self.win_rate, 100) * 0.40 +
            min(self.total_pnl / 10_000, 100) * 0.40 +
            min(self.trade_count / 100, 1) * 20
        )
        return self.score


async def analyze_wallet(address: str, chain: str,
                          min_tx: int = CFG.min_tx_history) -> WalletStats:
    stats = WalletStats(address=address, chain=chain)
    swaps = await get_swap_history(address, chain, limit=min_tx)
    if not swaps:
        return stats

    trades: Dict[str, TradeRecord] = {}
    for s in swaps:
        addr = s.get("token_addr", "").lower()
        if not addr:
            continue
        if addr not in trades:
            trades[addr] = TradeRecord(token_addr=addr)
        amt = float(s.get("amount_usd", 0) or 0)
        if s.get("action") == "buy":
            trades[addr].buys.append(amt)
        else:
            trades[addr].sells.append(amt)

    closed      = [t for t in trades.values() if t.is_closed]
    profitable  = [t for t in closed if t.is_profitable]

    stats.total_trades      = len(closed)
    stats.profitable_trades = len(profitable)
    stats.trade_count       = len(closed)

    if not closed:
        return stats

    stats.win_rate  = (len(profitable) / len(closed)) * 100
    stats.total_pnl = sum(t.pnl for t in closed)

    pnls = [t.pnl for t in closed]
    stats.best_trade  = max(pnls)
    stats.worst_trade = min(pnls)

    all_buys = [v for t in trades.values() for v in t.buys]
    stats.avg_trade_size = sum(all_buys) / len(all_buys) if all_buys else 0

    stats.qualifies = (
        stats.win_rate   >= CFG.min_win_rate   and
        stats.total_pnl  >= CFG.min_pnl_usd    and
        stats.trade_count >= CFG.min_trade_count
    )
    stats.compute_score()
    return stats


# ═══════════════════════════════════════════════════════════════
#  DISCOVERY ENGINE
# ═══════════════════════════════════════════════════════════════

async def run_discovery(chains: Optional[List[str]] = None,
                         progress_cb: Optional[Callable] = None,
                         ) -> List[WalletStats]:
    if chains is None:
        chains = CFG.active_chains

    all_qualified: List[WalletStats] = []
    seen: set = set()

    for chain in chains:
        log.info(f"[{chain}] Discovery started")
        # Stagger chain discovery
        if chains.index(chain) > 0:
            await asyncio.sleep(5)

        trending = await discovery_trending(chain)
        if not trending:
            log.warning(f"[{chain}] No trending tokens")
            continue
        log.info(f"[{chain}] {len(trending)} trending tokens")

        for i, pair in enumerate(trending[:15]):
            token_addr = pair["token_address"]
            if not token_addr:
                continue

            if progress_cb:
                await _safe_cb(progress_cb,
                    f"🔍 [{chain.upper()}] Token {i+1}/15: "
                    f"{pair['token_symbol']} ({pair['token_name']})"
                )

            # Analyze more buyers per token to find better wallets
            buyers = await get_early_buyers(
                token_addr, chain, top_n=50,
                pool_address=pair.get("pair_address")
            )
            log.info(f"[{chain}] {pair['token_symbol']}: {len(buyers)} potential smart wallets found")

            for batch_start in range(0, len(buyers), 5):
                batch   = buyers[batch_start:batch_start + 5]
                results = await asyncio.gather(
                    *[analyze_wallet(addr, chain) for addr in batch],
                    return_exceptions=True,
                )
                for stats in results:
                    if isinstance(stats, Exception):
                        log.error(f"Analysis error: {stats}")
                        continue

                    if not stats or not stats.address:
                        continue

                    key = (stats.address.lower(), stats.chain)
                    if key in seen:
                        continue
                    seen.add(key)

                    # No strict 'qualifies' filter for discovery - we take the best ones by score
                    # but ensure at least some activity or profit to avoid junk
                    if stats.score > 0 or stats.total_pnl > 0 or stats.trade_count > 2:
                        all_qualified.append(stats)
                        log.info(
                            f"✅ [{chain}] {stats.address[:10]}… "
                            f"WR={stats.win_rate:.1f}% PnL=${stats.total_pnl:,.0f} Score={stats.score:.1f}"
                        )
                        # Only auto-save to DB if it's actually good (meets the settings)
                        if stats.qualifies:
                             await DB.upsert_wallet(
                                stats.address, chain,
                                {"win_rate": stats.win_rate,
                                 "total_pnl": stats.total_pnl,
                                 "trade_count": stats.trade_count},
                            )

                        await DB.log_discovery(
                            chain, token_addr, len(buyers), len(all_qualified)
                        )
                await asyncio.sleep(2.0) # Increased delay to avoid rate limits

    all_qualified.sort(key=lambda w: w.score, reverse=True)
    return all_qualified


async def _safe_cb(cb, msg):
    try:
        if asyncio.iscoroutinefunction(cb):
            await cb(msg)
        else:
            cb(msg)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  MONITOR  —  real-time polling
# ═══════════════════════════════════════════════════════════════

_last_tx_cache: Dict[str, str] = {}


class WalletMonitor:
    def __init__(self):
        self._running   = False
        self._tx_cbs:   List[Callable] = []
        self._disc_cbs: List[Callable] = []

    def on_tx(self, cb: Callable):
        self._tx_cbs.append(cb)

    async def start(self):
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._monitor_loop())
        asyncio.create_task(self._discovery_loop())
        log.info("Monitor started.")

    async def stop(self):
        self._running = False
        log.info("Monitor stopped.")

    async def trigger_discovery(self, chains=None,
                                 progress_cb=None) -> List[WalletStats]:
        return await run_discovery(chains=chains, progress_cb=progress_cb)

    # ── Loops ──────────────────────────────────────────────────

    async def _monitor_loop(self):
        while self._running:
            try:
                wallets = await DB.list_wallets(active_only=True)
                for w in wallets:
                    await self._check_wallet(w["address"], w["chain"])
                    await asyncio.sleep(0.3)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Monitor loop: {e}")
            await asyncio.sleep(CFG.monitor_interval)

    async def _check_wallet(self, address: str, chain: str):
        key   = f"{chain}:{address}"
        swaps = await get_swap_history(address, chain, limit=5)
        if not swaps:
            return
        latest_hash = swaps[0].get("hash", "")
        old_hash    = _last_tx_cache.get(key)
        _last_tx_cache[key] = latest_hash

        if old_hash is None or old_hash == latest_hash:
            return  # First run or no change

        new_txs = []
        for s in swaps:
            if s.get("hash") == old_hash:
                break
            new_txs.append(s)

        for tx in reversed(new_txs):
            is_new = await DB.save_tx(address, chain, tx)
            if is_new:
                for cb in self._tx_cbs:
                    await _safe_cb(cb, (address, chain, tx))

    async def _discovery_loop(self):
        await asyncio.sleep(60)  # Wait before first auto-run
        while self._running:
            try:
                log.info("Auto-discovery started…")
                await run_discovery()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Discovery loop: {e}")
            await asyncio.sleep(CFG.discovery_interval)


MONITOR = WalletMonitor()


# ═══════════════════════════════════════════════════════════════
#  FORMATTERS
# ═══════════════════════════════════════════════════════════════

def fmt_tx_alert(address: str, chain: str, tx: Dict,
                  label: str = "") -> str:
    chain_em  = CHAIN_EMOJI.get(chain, "🌐")
    action    = tx.get("action", "buy")
    action_em = EMOJI["buy"] if action == "buy" else EMOJI["sell"]
    action_uz = "SOTIB OLDI" if action == "buy" else "SOTDI"
    symbol    = tx.get("token_symbol", "???") or "???"
    name      = tx.get("token_name", "") or symbol
    amount    = tx.get("amount_usd", 0) or 0
    price     = tx.get("price_usd", 0) or 0
    ts        = (tx.get("timestamp", "") or "")[:19].replace("T", " ")
    short     = f"{address[:6]}…{address[-4:]}"
    cfg       = CHAINS.get(chain)

    txt  = f"{action_em} <b>{action_uz}</b>  {chain_em} {chain.upper()}\n"
    txt += f"{'─' * 28}\n"
    if label:
        txt += f"📌 <b>{label}</b>\n"
    txt += f"{EMOJI['wallet']} <code>{short}</code>\n"
    txt += f"🪙 <b>{symbol}</b>"
    if name != symbol:
        txt += f" ({name})"
    txt += "\n"
    if amount:
        txt += f"💵 <b>${amount:,.2f}</b>\n"
    if price:
        txt += f"📈 Narx: <b>${price:.8f}</b>\n"
    txt += f"🕐 {ts} UTC"
    if cfg and tx.get("hash"):
        txt += (f'\n{EMOJI["link"]} <a href="{cfg.explorer_url}'
                f'/tx/{tx["hash"]}">Explorer</a>')
    return txt


def fmt_wallet_row(w: Dict, idx: int = 0) -> str:
    chain   = w.get("chain", "")
    em      = CHAIN_EMOJI.get(chain, "🌐")
    short   = f"{w['address'][:6]}…{w['address'][-4:]}"
    label   = w.get("label", "")
    wr      = w.get("win_rate", 0)
    pnl     = w.get("total_pnl", 0)
    cnt     = w.get("trade_count", 0)
    pnl_em  = EMOJI["profit"] if pnl >= 0 else EMOJI["loss"]
    prefix  = f"<b>{idx}.</b> " if idx else ""
    lbl_ln  = f"   📌 {label}\n" if label else ""
    return (
        f"{prefix}{em} <code>{short}</code>\n"
        f"{lbl_ln}"
        f"   ✅ Win Rate: <b>{wr:.1f}%</b>  "
        f"{pnl_em} PnL: <b>${pnl:,.0f}</b>  "
        f"📊 <b>{cnt}</b> savdo\n"
    )


# ═══════════════════════════════════════════════════════════════
#  TELEGRAM BOT
# ═══════════════════════════════════════════════════════════════

def _auth(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if CFG.allowed_users and uid not in CFG.allowed_users:
            target = update.message or (update.callback_query.message if update.callback_query else None)
            if target:
                await target.reply_text(
                    f"{EMOJI['cross']} Ruxsat yo'q. Sizning ID: <code>{uid}</code>",
                    parse_mode=ParseMode.HTML,
                )
            return
        return await func(update, ctx)
    wrapper.__name__ = func.__name__
    return wrapper


async def _reply(update: Update, text: str, **kw):
    target = update.message
    if not target and update.callback_query:
        target = update.callback_query.message

    if not target:
        return

    for chunk in [text[i:i+4096] for i in range(0, len(text), 4096)]:
        if update.callback_query and not kw.get("reply_markup"):
             # If it's a callback and no new markup, maybe we want to edit?
             # But _reply is usually for new messages.
             # Let's keep it simple: always send new message for now,
             # or edit if it's the first chunk of a callback.
             pass

        await target.reply_text(
            chunk, parse_mode=ParseMode.HTML,
            disable_web_page_preview=True, **kw
        )


# ── /start ────────────────────────────────────────────────────

@_auth
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chains_txt = "".join(
        f"  {CHAIN_EMOJI[k]} {cfg.name}\n" for k, cfg in CHAINS.items()
    )
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJI['search']} Qidirish", callback_data="cmd_find"),
            InlineKeyboardButton(f"{EMOJI['list']} Ro'yxat", callback_data="cmd_list"),
        ],
        [
            InlineKeyboardButton(f"{EMOJI['chart']} Statistika", callback_data="cmd_stats_main"),
            InlineKeyboardButton(f"⚙️ Sozlamalar", callback_data="cmd_settings"),
        ],
        [
            InlineKeyboardButton(f"🌐 DNS Muammo", callback_data="cmd_dns_fix"),
            InlineKeyboardButton(f"{EMOJI['warning']} Yordam", callback_data="cmd_help")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await _reply(update,
        f"{EMOJI['diamond']} <b>Smart Money Finder & Tracker</b> (Free v1.3)\n"
        f"{'═' * 32}\n\n"
        f"Blockchain tarmog'idagi aqlli treyderlarni\n"
        f"avtomatik topish va real vaqtda kuzatish.\n"
        f"<i>Barcha API'lar abadiy tekin va ochiq.</i>\n\n"
        f"<b>Tarmoqlar:</b>\n{chains_txt}\n"
        f"<b>Filtr:</b>  WinRate ≥ {CFG.min_win_rate}%  |  "
        f"PnL ≥ ${CFG.min_pnl_usd:,.0f}  |  Savdolar ≥ {CFG.min_trade_count}\n\n"
        f"Quyidagi tugmalardan foydalaning:",
        reply_markup=reply_markup
    )


# ── /help ─────────────────────────────────────────────────────

@_auth
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await _reply(update,
        f"{EMOJI['search']} <b>Buyruqlar</b>\n{'─' * 30}\n\n"
        f"<b>/find</b> [chain]\n"
        f"  Trending tokenlar orqali smart wallet topish.\n"
        f"  Misol: <code>/find ethereum</code>\n\n"
        f"<b>/list</b>\n"
        f"  Barcha kuzatuvdagi hamyonlar.\n\n"
        f"<b>/add</b> &lt;address&gt; &lt;chain&gt; [label]\n"
        f"  Misol: <code>/add 0xabc...def ethereum Pro Trader</code>\n\n"
        f"<b>/remove</b> &lt;address&gt; &lt;chain&gt;\n"
        f"  Hamyonni kuzatuvdan o'chirish.\n\n"
        f"<b>/stats</b> [address chain]\n"
        f"  Tizim yoki hamyon statistikasi.\n\n"
        f"<b>Qo'llab-quvvatlanadigan tarmoqlar:</b>\n"
        f"  {', '.join(CHAINS.keys())}\n",
        reply_markup=reply_markup
    )


# ── /list ─────────────────────────────────────────────────────

@_auth
async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    wallets = await DB.list_wallets(active_only=True)
    if not wallets:
        keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_start")]]
        await _reply(update,
            f"{EMOJI['warning']} Kuzatuvda hech qanday hamyon yo'q.\n"
            f"/add yoki /find buyrug'ini ishlating.",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    lines = [f"{EMOJI['list']} <b>Kuzatuvdagi hamyonlar</b> ({len(wallets)} ta)\n"
             f"{'═' * 30}\n\n"]

    # We'll use a simplified list if there are many, or just provide buttons for the top ones
    for i, w in enumerate(wallets[:20], 1):
        lines.append(fmt_wallet_row(w, i) + "\n")

    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['remove']} Hamyonni o'chirish", callback_data="list_remove_select")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_start")]
    ]

    await _reply(update, "".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


# ── /add ──────────────────────────────────────────────────────

@_auth
async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args or []
    if len(args) < 2:
        await _reply(update,
            f"{EMOJI['warning']} Foydalanish:\n"
            f"<code>/add &lt;address&gt; &lt;chain&gt; [label]</code>\n\n"
            f"Misol:\n<code>/add 0xabc123 ethereum Pro Trader</code>")
        return

    address = args[0].strip()
    chain   = args[1].lower().strip()
    label   = " ".join(args[2:]) if len(args) > 2 else ""

    if chain not in CHAINS:
        await _reply(update,
            f"{EMOJI['cross']} Noto'g'ri tarmoq: <b>{chain}</b>\n"
            f"Mavjud: {', '.join(CHAINS.keys())}")
        return
    if chain != "solana" and not address.startswith("0x"):
        await _reply(update,
            f"{EMOJI['cross']} EVM manzil <code>0x</code> bilan boshlanishi kerak.")
        return

    target = update.message or update.callback_query.message
    msg = await target.reply_text(
        f"{EMOJI['clock']} Hamyon qo'shilmoqda va tahlil qilinmoqda…")

    is_new = await DB.add_wallet(address, chain, label=label)
    if not is_new:
        await msg.edit_text(
            f"{EMOJI['warning']} Bu hamyon allaqachon kuzatuvda:\n"
            f"<code>{address[:10]}…</code>",
            parse_mode=ParseMode.HTML)
        return

    await msg.edit_text(
        f"{EMOJI['search']} Statistika hisoblanmoqda…",
        parse_mode=ParseMode.HTML)

    stats = await analyze_wallet(address, chain)
    await DB.upsert_wallet(address, chain, {
        "win_rate":    stats.win_rate,
        "total_pnl":  stats.total_pnl,
        "trade_count": stats.trade_count,
    }, label=label)

    chain_em = CHAIN_EMOJI.get(chain, "🌐")
    short    = f"{address[:8]}…{address[-4:]}"
    qual_em  = EMOJI["check"] if stats.qualifies else EMOJI["warning"]
    qual_txt = "Professional savdochi ✅" if stats.qualifies else "Minimal talablar bajarilmagan"
    pnl_em   = EMOJI["profit"] if stats.total_pnl >= 0 else EMOJI["loss"]

    await msg.edit_text(
        f"{EMOJI['add']} <b>Hamyon qo'shildi!</b>\n"
        f"{'─' * 28}\n"
        f"{chain_em} <code>{short}</code>\n"
        f"{'📌 ' + label + chr(10) if label else ''}\n"
        f"<b>📊 Tahlil natijasi:</b>\n"
        f"  ✅ Win Rate:   <b>{stats.win_rate:.1f}%</b>\n"
        f"  {pnl_em} PnL:       <b>${stats.total_pnl:,.0f}</b>\n"
        f"  🔢 Savdolar:  <b>{stats.trade_count}</b>\n"
        f"  ⭐ Bali:      <b>{stats.score:.0f}/100</b>\n\n"
        f"{qual_em} {qual_txt}",
        parse_mode=ParseMode.HTML,
    )


# ── /remove ───────────────────────────────────────────────────

@_auth
async def cmd_remove(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args or []
    if len(args) < 2:
        await _reply(update,
            f"{EMOJI['warning']} Foydalanish:\n"
            f"<code>/remove &lt;address&gt; &lt;chain&gt;</code>")
        return
    address, chain = args[0].strip(), args[1].lower().strip()
    ok = await DB.remove_wallet(address, chain)

    target = update.message or update.callback_query.message
    if ok:
        await target.reply_text(
            f"{EMOJI['remove']} Hamyon olib tashlandi:\n"
            f"<code>{address[:10]}…</code>  [{chain}]",
            parse_mode=ParseMode.HTML)
    else:
        await target.reply_text(
            f"{EMOJI['cross']} Hamyon topilmadi:\n"
            f"<code>{address[:10]}…</code>  [{chain}]",
            parse_mode=ParseMode.HTML)


# ── /stats ────────────────────────────────────────────────────

@_auth
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args or []

    if not args:
        summary = await DB.global_summary()
        await _reply(update,
            f"{EMOJI['chart']} <b>Tizim statistikasi</b>\n"
            f"{'─' * 28}\n"
            f"  👛 Jami hamyonlar:  <b>{summary['total']}</b>\n"
            f"  ✅ Aktiv:           <b>{summary['active']}</b>\n"
            f"  📝 Tranzaksiyalar:  <b>{summary['transactions']}</b>\n"
            f"  🔍 Qidiruvlar:     <b>{summary['discoveries']}</b>\n\n"
            f"Hamyon statistikasi:\n"
            f"<code>/stats &lt;address&gt; &lt;chain&gt;</code>")
        return

    if len(args) < 2:
        await _reply(update,
            f"{EMOJI['warning']} Foydalanish:\n"
            f"<code>/stats &lt;address&gt; &lt;chain&gt;</code>")
        return

    address, chain = args[0].strip(), args[1].lower().strip()
    if chain not in CHAINS:
        await _reply(update, f"{EMOJI['cross']} Noma'lum tarmoq: {chain}")
        return

    target = update.message or update.callback_query.message
    msg   = await target.reply_text(f"{EMOJI['clock']} Tahlil qilinmoqda…")
    stats = await analyze_wallet(address, chain)

    chain_em = CHAIN_EMOJI.get(chain, "🌐")
    short    = f"{address[:8]}…{address[-4:]}"
    pnl_em   = EMOJI["profit"] if stats.total_pnl >= 0 else EMOJI["loss"]
    qual     = "✅ Professional savdochi" if stats.qualifies else "❌ Minimal talablar bajarilmagan"

    recent_txs = await DB.get_wallet_txs(address, chain, limit=5)
    recent_txt = ""
    if recent_txs:
        recent_txt = "\n\n📝 <b>Oxirgi tranzaksiyalar:</b>\n"
        for tx in recent_txs:
            em  = EMOJI["buy"] if tx["action"] == "buy" else EMOJI["sell"]
            sym = tx.get("token_symbol") or "???"
            amt = f"${tx.get('amount_usd', 0):,.0f}"
            ts  = (tx.get("timestamp") or "")[:10]
            recent_txt += f"  {em} {sym}  {amt}  {ts}\n"

    await msg.edit_text(
        f"{EMOJI['chart']} <b>Hamyon statistikasi</b>\n"
        f"{'═' * 30}\n\n"
        f"{chain_em} <code>{short}</code>\n\n"
        f"<b>📊 Ko'rsatkichlar:</b>\n"
        f"  ✅ Win Rate:       <b>{stats.win_rate:.2f}%</b>\n"
        f"  {pnl_em} Umumiy PnL:  <b>${stats.total_pnl:,.0f}</b>\n"
        f"  📈 Eng yaxshi:    <b>${stats.best_trade:,.0f}</b>\n"
        f"  📉 Eng yomon:     <b>${stats.worst_trade:,.0f}</b>\n"
        f"  🔢 Jami savdolar: <b>{stats.total_trades}</b>\n"
        f"  ✔️  Foydali:       <b>{stats.profitable_trades}</b>\n"
        f"  💵 O'rtacha:      <b>${stats.avg_trade_size:,.0f}</b>\n"
        f"  ⭐ Sifat bali:    <b>{stats.score:.1f}/100</b>\n\n"
        f"{qual}"
        f"{recent_txt}",
        parse_mode=ParseMode.HTML,
    )


# ── /settings ─────────────────────────────────────────────────

@_auth
async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(f"Win Rate ({CFG.min_win_rate}%)", callback_data="set_wr_menu"),
            InlineKeyboardButton(f"PnL (${CFG.min_pnl_usd:,.0f})", callback_data="set_pnl_menu"),
        ],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await _reply(update,
        f"⚙️ <b>Sozlamalar</b>\n"
        f"{'─' * 28}\n\n"
        f"Bu yerda hamyonlarni saralash filtrlarini o'zgartirishingiz mumkin.\n\n"
        f"✅ <b>Win Rate:</b> {CFG.min_win_rate}%\n"
        f"💰 <b>Minimal PnL:</b> ${CFG.min_pnl_usd:,.0f}",
        reply_markup=reply_markup
    )


# ── CALLBACK HANDLER ──────────────────────────────────────────

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid   = query.from_user.id
    if CFG.allowed_users and uid not in CFG.allowed_users:
        await query.answer("Ruxsat yo'q!", show_alert=True)
        return

    data = query.data
    await query.answer()

    # Simple routing
    if data == "cmd_start":
        await cmd_start(update, ctx)
        try: await query.message.delete()
        except: pass
    elif data == "cmd_help":
        await cmd_help(update, ctx)
        try: await query.message.delete()
        except: pass
    elif data == "cmd_list":
        await cmd_list(update, ctx)
        try: await query.message.delete()
        except: pass
    elif data == "cmd_find":
        await cmd_find_select_chain(update, ctx)
        try: await query.message.delete()
        except: pass
    elif data.startswith("find_run_"):
        chain = data.replace("find_run_", "")
        if chain == "all":
            ctx.args = []
        else:
            ctx.args = [chain]
        await cmd_find(update, ctx)
    elif data == "list_remove_select":
        wallets = await DB.list_wallets(active_only=True)
        if not wallets:
            await query.edit_message_text("Hamyonlar yo'q.")
            return
        keyboard = []
        for w in wallets[:15]: # Limit to avoid huge keyboard
            short = f"{w['address'][:6]}…{w['address'][-4:]}"
            keyboard.append([InlineKeyboardButton(
                f"{EMOJI['remove']} {short} [{w['chain']}]",
                callback_data=f"remove_confirm_{w['address']}_{w['chain']}"
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_list")])
        await query.edit_message_text(
            "<b>O'chirish uchun hamyonni tanlang:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data.startswith("remove_confirm_"):
        parts = data.replace("remove_confirm_", "").split("_")
        if len(parts) >= 2:
            address, chain = parts[0], parts[1]
            ctx.args = [address, chain]
            await cmd_remove(update, ctx)
    elif data == "cmd_stats_main":
        await cmd_stats(update, ctx)
    elif data == "cmd_settings":
        await cmd_settings(update, ctx)
    elif data == "cmd_dns_fix":
        # Check connection status
        results = []
        for host in ["google.com", "api.dexscreener.com", "api.geckoterminal.com"]:
            try:
                import socket
                socket.gethostbyname(host)
                results.append(f"✅ {host}")
            except:
                results.append(f"❌ {host}")

        status_txt = "\n".join(results)

        await _reply(update,
            f"🌐 <b>DNS va Ulanish holati:</b>\n{status_txt}\n\n"
            f"{'─' * 30}\n\n"
            f"Agar botda 'DNS Xatoligi' ko'rinsa, quyidagi amallarni bajaring:\n\n"
            f"1️⃣ <b>Private DNS o'rnatish (Tavsiya):</b>\n"
            f"   - Android Sozlamalari -> Tarmoq (Network) -> Private DNS\n"
            f"   - <code>1.1.1.1</code> yoki <code>dns.google</code> deb yozing.\n\n"
            f"2️⃣ <b>VPN ishlatish:</b>\n"
            f"   - 1.1.1.1, Cloudflare yoki biror VPN ilovasini yoqing.\n\n"
            f"3️⃣ <b>Internetni yangilash:</b>\n"
            f"   - Airplane mode yoqib-o'chiring.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_start")]])
        )
    elif data == "set_wr_menu" or data.startswith("set_wr_"):
        if data.startswith("set_wr_"):
            change = 0
            if "up_1" in data: change = 1
            elif "up_5" in data: change = 5
            elif "down_1" in data: change = -1
            elif "down_5" in data: change = -5
            CFG.min_win_rate = max(0, min(100, CFG.min_win_rate + change))
            await DB.set_setting("min_win_rate", CFG.min_win_rate)

        keyboard = [
            [
                InlineKeyboardButton("-5%", callback_data="set_wr_down_5"),
                InlineKeyboardButton("-1%", callback_data="set_wr_down_1"),
                InlineKeyboardButton("+1%", callback_data="set_wr_up_1"),
                InlineKeyboardButton("+5%", callback_data="set_wr_up_5"),
            ],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_settings")]
        ]
        await query.edit_message_text(
            f"<b>Win Rate sozlamalari</b>\n\nJoriy: {CFG.min_win_rate}%\n\nO'zgartirish:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "set_pnl_menu" or data.startswith("set_pnl_"):
        if data.startswith("set_pnl_"):
            change = 0
            if "up_1000" in data: change = 1000
            if "up_10000" in data: change = 10000
            if "down_1000" in data: change = -1000
            if "down_10000" in data: change = -10000
            CFG.min_pnl_usd = max(0, CFG.min_pnl_usd + change)
            await DB.set_setting("min_pnl_usd", CFG.min_pnl_usd)

        keyboard = [
            [
                InlineKeyboardButton("-10k", callback_data="set_pnl_down_10000"),
                InlineKeyboardButton("-1k", callback_data="set_pnl_down_1000"),
                InlineKeyboardButton("+1k", callback_data="set_pnl_up_1000"),
                InlineKeyboardButton("+10k", callback_data="set_pnl_up_10000"),
            ],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_settings")]
        ]
        await query.edit_message_text(
            f"<b>Minimal PnL sozlamalari</b>\n\nJoriy: ${CFG.min_pnl_usd:,.0f}\n\nO'zgartirish:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ── /find ─────────────────────────────────────────────────────

@_auth
async def cmd_find_select_chain(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    # 2 chains per row
    chain_list = list(CHAINS.keys())
    for i in range(0, len(chain_list), 2):
        row = []
        for c in chain_list[i:i+2]:
            row.append(InlineKeyboardButton(f"{CHAIN_EMOJI[c]} {c.upper()}", callback_data=f"find_run_{c}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🌐 BARCHA TARMOQLAR", callback_data="find_run_all")])
    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="cmd_start")])

    await _reply(update,
        f"{EMOJI['search']} <b>Qaysi tarmoqdan qidiramiz?</b>\n"
        f"Trending tokenlar orqali smart walletlar qidiriladi.",
        reply_markup=InlineKeyboardMarkup(keyboard))


@_auth
async def cmd_find(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args         = ctx.args or []
    chain_filter = args[0].lower() if args else None

    if chain_filter and chain_filter not in CHAINS:
        await _reply(update,
            f"{EMOJI['cross']} Noma'lum tarmoq: <b>{chain_filter}</b>\n"
            f"Mavjud: {', '.join(CHAINS.keys())}")
        return

    chains_label = chain_filter.upper() if chain_filter else "Barcha tarmoqlar"
    target = update.message or update.callback_query.message
    msg = await target.reply_text(
        f"{EMOJI['search']} <b>Qidiruv boshlandi…</b>\n"
        f"{'─' * 28}\n"
        f"🌐 {chains_label}\n\n"
        f"⏳ Bu bir necha daqiqa olishi mumkin…",
        parse_mode=ParseMode.HTML,
    )

    progress_lines: List[str] = []

    async def progress_cb(text: str):
        progress_lines.append(text)
        last = "\n".join(progress_lines[-6:])
        try:
            await msg.edit_text(
                f"{EMOJI['search']} <b>Qidiruv davom etmoqda…</b>\n"
                f"{'─' * 28}\n\n{last}\n\n⏳ Kuting…",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    try:
        results = await MONITOR.trigger_discovery(
            chains=[chain_filter] if chain_filter else None,
            progress_cb=progress_cb,
        )
    except Exception as e:
        log.error(f"Discovery: {e}")
        await msg.edit_text(
            f"{EMOJI['cross']} Xatolik: {e}", parse_mode=ParseMode.HTML)
        return

    if not results:
        await msg.edit_text(
            f"{EMOJI['warning']} Tahlil qilingan hamyonlar ichidan mos keladigani topilmadi.",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = [
        f"{EMOJI['fire']} <b>Eng yaxshi topilgan hamyonlar:</b>\n"
        f"{'═' * 30}\n\n"
    ]
    for i, s in enumerate(results[:15], 1):
        chain_em = CHAIN_EMOJI.get(s.chain, "🌐")
        short    = f"{s.address[:8]}…{s.address[-4:]}"
        pnl_em   = EMOJI["profit"] if s.total_pnl >= 0 else EMOJI["loss"]
        lines.append(
            f"<b>{i}.</b> {chain_em} <code>{short}</code>  [{s.chain}]\n"
            f"   ✅ WR: <b>{s.win_rate:.1f}%</b>  "
            f"{pnl_em} PnL: <b>${s.total_pnl:,.0f}</b>  "
            f"📊 <b>{s.trade_count}</b>  "
            f"⭐ <b>{s.score:.0f}</b>\n\n"
        )
    await msg.edit_text("".join(lines), parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATION BROADCASTER
# ═══════════════════════════════════════════════════════════════

class Broadcaster:
    def __init__(self, app: Application):
        self.app = app

    async def __call__(self, payload):
        """Called by MONITOR with (address, chain, tx) tuple."""
        address, chain, tx = payload
        w     = await DB.get_wallet(address, chain)
        label = (w or {}).get("label", "")
        text  = fmt_tx_alert(address, chain, tx, label=label)
        for uid in CFG.allowed_users:
            try:
                await self.app.bot.send_message(
                    chat_id=uid, text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                log.warning(f"Notify {uid}: {e}")


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def _banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║     💎  Smart Money Finder & Tracker (FREE) v1.3        ║
╠══════════════════════════════════════════════════════════╣""")
    for k, cfg in CHAINS.items():
        em = CHAIN_EMOJI.get(k, "🌐")
        print(f"║  {em} {cfg.name:<20} chain_id={cfg.chain_id:<8}  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\n  Filter: WinRate≥{CFG.min_win_rate}% | "
          f"PnL≥${CFG.min_pnl_usd:,.0f} | "
          f"Trades≥{CFG.min_trade_count}\n")


def _validate():
    errors = []
    if not CFG.bot_token:
        errors.append("❌  TELEGRAM_BOT_TOKEN .env faylida belgilanmagan.")
    if not CFG.allowed_users:
        print("⚠️   ALLOWED_USER_IDS belgilanmagan — barcha foydalanuvchilar kirishi mumkin!")
    for e in errors:
        print(e)
    if errors:
        sys.exit(1)


async def main():
    _setup_logging()
    _validate()
    _banner()

    log.info("Ma'lumotlar bazasi ulanmoqda…")
    await DB.connect()
    await CFG.reload(DB)

    log.info("Telegram bot yaratilmoqda…")
    app = Application.builder().token(CFG.bot_token).build()

    # Register all commands
    for cmd, handler in [
        ("start",  cmd_start),
        ("help",   cmd_help),
        ("list",   cmd_list),
        ("add",    cmd_add),
        ("remove", cmd_remove),
        ("stats",  cmd_stats),
        ("find",   cmd_find),
    ]:
        app.add_handler(CommandHandler(cmd, handler))

    app.add_handler(CallbackQueryHandler(on_callback))

    # Set bot command menu
    await app.initialize()
    await app.bot.set_my_commands([
        BotCommand("start",  "Botni ishga tushirish"),
        BotCommand("find",   "Yangi aqlli hamyonlarni qidirish"),
        BotCommand("list",   "Kuzatuvdagi hamyonlar"),
        BotCommand("add",    "Hamyon qo'shish"),
        BotCommand("remove", "Hamyonni o'chirish"),
        BotCommand("stats",  "Statistika"),
        BotCommand("help",   "Yordam"),
    ])

    # Wire monitor → broadcaster
    broadcaster = Broadcaster(app)
    MONITOR.on_tx(broadcaster)

    log.info("Monitor ishga tushmoqda…")
    await MONITOR.start()

    log.info("Bot polling boshlandi ✅  |  To'xtatish: Ctrl+C")
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("To'xtatilmoqda…")
    finally:
        await MONITOR.stop()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await DB.close()

        global _HTTP_SESSION
        if _HTTP_SESSION and not _HTTP_SESSION.closed:
            await _HTTP_SESSION.close()

        log.info("Xayr! 👋")


if __name__ == "__main__":
    asyncio.run(main())
