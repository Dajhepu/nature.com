"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            WHALE TRACKER PRO v4.5 — NEW TOKENS ONLY                         ║
║                                                                              ║
║  DexScreener + GoPlus Security + CoinGecko + Neural Scoring                 ║
║  Cross-DEX Arbitrage + Contract Scanner + Regime Detector                   ║
║  Real-time Position Tracker + Adaptive Weights                              ║
║                                                                              ║
║  Faqat 0-6 soatlik YANGI tokenlar kuzatiladi                                ║
║  Signallar: MOONSHOT_ALPHA | STRONG_BUY | BREAKOUT | RUG_ALERT             ║
╚══════════════════════════════════════════════════════════════════════════════╝

O'rnatish:
    pip install aiohttp python-telegram-bot apscheduler colorama python-dotenv flask flask-cors

Ishga tushirish:
    python whale_tracker.py
"""

import asyncio
import logging
import time
import html
import json
import math
import os
import sys
import random
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, List

import aiohttp
from colorama import Fore, Style, init
from flask import Flask, jsonify, send_from_directory, render_template_string
from flask_cors import CORS

# python-dotenv ixtiyoriy (mavjud bo'lsa yuklaydi)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    from telegram.constants import ParseMode
except ImportError:
    print("❌ python-telegram-bot o'rnatilmagan: pip install python-telegram-bot")
    sys.exit(1)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:
    print("❌ apscheduler o'rnatilmagan: pip install apscheduler")
    sys.exit(1)

init(autoreset=True)

# ══════════════════════════════════════════════════════════════
#  ⚙️  SOZLAMALAR — Hardcoded credentials
# ══════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = "7256069971:AAHNTBZZipJI9mF1K1lRyNiQb2n7qEEDEDY"
TELEGRAM_CHAT_ID   = "798283148"
MORALIS_API_KEY    = "" # Disabled to use Free APIs

# ── Token yoshi chegaralari (YANGI TOKENLAR ONLY) ─────────
NEW_TOKEN_MIN_HOURS  = 0.25    # Minimal yosh: 15 daqiqa (juda yangi = rug xavfi)
NEW_TOKEN_MAX_HOURS  = 6.0     # Maksimal yosh: 6 soat

# ── Signal filtrlari (yangi tokenlar uchun moslantirilgan) ─
MIN_CONFIDENCE      = 65       # Yangi tokenlar uchun biroz pastroq (kam tarix)
MIN_LIQUIDITY       = 20_000   # Yangi tokenlar uchun pastroq likvidlik talabi
MIN_VOLUME_24H      = 15_000   # Yangi token 24s to'liq ishlamagan bo'lishi mumkin
MIN_VOLUME_1H       = 3_000    # 1 soatlik hajm yangi tokenlar uchun muhimroq
MAX_SIGNALS_PER_HR  = 25       # Yangi tokenlar ko'p bo'lgani uchun biroz yuqori
COOLDOWN_MINUTES    = 30       # Yangi token tez o'zgaradi — qisqaroq cooldown

# ── Moonshot parametrlari (yangi tokenlar uchun) ──────────
MOONSHOT_MIN_MCAP        = 5_000     # Juda past kapital (yangi tokenlar)
MOONSHOT_MAX_MCAP        = 800_000   # Biroz yuqoriroq chegara
MOONSHOT_MIN_BUY_RATIO   = 0.75      # Yangi tokenlarda 0.75 yetarli
MOONSHOT_MIN_VOL_5M      = 2_000     # Yangi token uchun pastroq
MOONSHOT_MIN_AGE_HOURS   = 0.25      # 15 daqiqadan katta bo'lsin

# ── Skanerlash ─────────────────────────────────────────────
SCAN_INTERVAL_SEC   = 45       # Yangi tokenlar tez o'zgaradi — tezroq skan
WATCH_CHAINS        = ["ethereum", "bsc", "solana", "arbitrum", "polygon", "base"]

# ── Savdo maqsadlari ───────────────────────────────────────
TARGET_1_PCT  = 8.0    # Yangi tokenlar ko'proq volatil — kattaroq maqsad
TARGET_2_PCT  = 20.0   # 20% maqsad 2
STOP_LOSS_PCT = 5.0    # Yangi tokenlar uchun kengrok stop (volatillik yuqori)
MIN_RR_RATIO  = 1.5    # Minimal R:R

# ── Xavfsizlik filtrlari (yangi tokenlar uchun moslantirilgan) ─
MAX_SECURITY_RISK   = 40       # Yangi tokenlarda biroz yumshoqroq (hali audit yo'q)
MAX_TOP_HOLDER_PCT  = 50.0     # Yangi tokenlarda ko'proq ruxsat
MIN_HOLDER_COUNT    = 10       # Yangi token — holder soni kam bo'ladi
MAX_SELL_TAX        = 10.0     # Yangi tokenlarda biroz yuqoriroq tax bo'lishi mumkin
MAX_BUY_TAX         = 10.0
MIN_TOKEN_AGE_HOURS = NEW_TOKEN_MIN_HOURS

# ── Retry sozlamalari ──────────────────────────────────────
HTTP_RETRY_COUNT    = 3
HTTP_RETRY_DELAY    = 2.0      # soniya

# ══════════════════════════════════════════════════════════════
#  📋  LOGGING
# ══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("wtp_v4.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("WTP-v4")

# ══════════════════════════════════════════════════════════════
#  📦  MA'LUMOT MODELLARI
# ══════════════════════════════════════════════════════════════

@dataclass
class MarketSnapshot:
    pair_address:  str
    token_symbol:  str
    token_name:    str
    token_address: str
    chain:         str
    dex:           str
    price_usd:     float
    market_cap:    float
    liquidity:     float
    volume_5m:     float
    volume_1h:     float
    volume_6h:     float
    volume_24h:    float
    change_5m:     float
    change_1h:     float
    change_6h:     float
    change_24h:    float
    buys_5m:       int
    sells_5m:      int
    buys_1h:       int
    sells_1h:      int
    buys_24h:      int
    sells_24h:     int
    age_hours:     float
    timestamp:     datetime = field(default_factory=datetime.now)

    @property
    def buy_ratio_5m(self) -> float:
        t = self.buys_5m + self.sells_5m
        return self.buys_5m / t if t > 0 else 0.5

    @property
    def buy_ratio_1h(self) -> float:
        t = self.buys_1h + self.sells_1h
        return self.buys_1h / t if t > 0 else 0.5

    @property
    def buy_ratio_24h(self) -> float:
        t = self.buys_24h + self.sells_24h
        return self.buys_24h / t if t > 0 else 0.5

    @property
    def vol_to_liq_ratio(self) -> float:
        """Hajm/Likvidlik nisbati — faollik ko'rsatkichi"""
        return self.volume_24h / self.liquidity if self.liquidity > 0 else 0.0

    @property
    def total_txns_1h(self) -> int:
        return self.buys_1h + self.sells_1h

    @property
    def total_txns_24h(self) -> int:
        return self.buys_24h + self.sells_24h


@dataclass
class WalletExpertise:
    address:       str
    success_rate:  float = 0.0
    alpha_hits:    int   = 0
    total_trades:  int   = 0
    is_expert:     bool  = False


@dataclass
class SecurityReport:
    is_honeypot:     bool  = False
    has_mint:        bool  = False
    has_blacklist:   bool  = False
    has_proxy:       bool  = False
    owner_renounced: bool  = True
    top_holder_pct:  float = 0.0
    holder_count:    int   = 0
    sell_tax:        float = 0.0
    buy_tax:         float = 0.0
    is_open_source:  bool  = True
    risk_score:      int   = 0
    flags:           list  = field(default_factory=list)
    expert_holders:  list  = field(default_factory=list)
    scanned:         bool  = False   # GoPlus muvaffaqiyatli skan qildimi


@dataclass
class SignalResult:
    snapshot:         MarketSnapshot
    signal_type:      str
    confidence:       int
    primary_reason:   str
    confluence:       list
    risk_flags:       list
    security:         Optional[SecurityReport]
    smc_pattern:      Optional[str]
    regime:           str
    timeframe_align:  dict
    neural_scores:    dict
    backtest_winrate: Optional[float]
    risk_reward:      float
    entry:            float
    target_1:         float
    target_2:         float
    stop_loss:        float
    is_trending:      bool  = False
    is_boosted:       bool  = False
    arb_detected:     bool  = False
    estimated_hours:  Optional[float] = None
    security_passed:  bool  = False   # Yangi: xavfsizlik filtri o'tdimi

    @property
    def bar(self) -> str:
        f = round(self.confidence / 10)
        return "█" * f + "░" * (10 - f)

    @property
    def emoji(self) -> str:
        return {
            "MOONSHOT_ALPHA": "🚀🔥",
            "STRONG_BUY":    "🟢🟢",
            "BUY":           "🟢",
            "ACCUMULATION":  "🐋",
            "BREAKOUT":      "⚡",
            "DUMP_RISK":     "🔴",
            "DISTRIBUTION":  "🔴🔴",
            "RUG_ALERT":     "☠️",
        }.get(self.signal_type, "🔵")


# ══════════════════════════════════════════════════════════════
#  🌐  ASYNC HTTP HELPER — Retry va rate limiting bilan
# ══════════════════════════════════════════════════════════════

class HttpClient:
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/124.0.0.0 Safari/537.36")

    def __init__(self):
        self._sess: Optional[aiohttp.ClientSession] = None
        self._last_requests: deque = deque(maxlen=100)  # Rate limiting uchun

    def _get_session(self) -> aiohttp.ClientSession:
        if not self._sess or self._sess.closed:
            self._sess = aiohttp.ClientSession(
                headers={"User-Agent": self.UA, "Accept": "application/json"},
                connector=aiohttp.TCPConnector(limit=20),
            )
        return self._sess

    async def get(self, url: str, params: dict = None,
                  timeout: int = 15, retries: int = HTTP_RETRY_COUNT) -> Optional[Any]:
        """Retry mexanizmi bilan HTTP GET so'rovi."""
        last_err = None
        for attempt in range(retries):
            try:
                sess = self._get_session()
                async with sess.get(
                    url, params=params,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as r:
                    if r.status == 200:
                        try:
                            return await r.json(content_type=None)
                        except Exception:
                            text = await r.text()
                            return json.loads(text)
                    elif r.status == 429:
                        # Rate limit — kutib qayta urinish
                        wait = float(r.headers.get("Retry-After", 5 * (attempt + 1)))
                        log.warning(f"Rate limited: {url} — {wait:.0f}s kutilmoqda")
                        await asyncio.sleep(wait)
                        continue
                    elif r.status in (500, 502, 503, 504):
                        wait = HTTP_RETRY_DELAY * (attempt + 1)
                        log.warning(f"Server xatosi {r.status}: {url} — {wait:.0f}s so'ng qayta")
                        await asyncio.sleep(wait)
                        continue
                    else:
                        log.debug(f"HTTP {r.status}: {url}")
                        return None
            except asyncio.TimeoutError:
                last_err = "Timeout"
                await asyncio.sleep(HTTP_RETRY_DELAY)
            except aiohttp.ClientError as e:
                last_err = str(e)
                await asyncio.sleep(HTTP_RETRY_DELAY)
            except Exception as e:
                last_err = str(e)
                log.debug(f"HTTP xatosi [{attempt+1}/{retries}]: {url} — {e}")
                await asyncio.sleep(HTTP_RETRY_DELAY)

        if last_err:
            log.debug(f"Barcha urinishlar muvaffaqiyatsiz: {url} — {last_err}")
        return None

    async def close(self):
        if self._sess and not self._sess.closed:
            await self._sess.close()


# 📡  DEXSCREENER API
class DexScreenerAPI:
    BASE = "https://api.dexscreener.com"
    _MIN_REQUEST_GAP_MS = 200

    def __init__(self, http: HttpClient):
        self.http = http
        self._last_call = 0.0

    async def _get(self, path: str, params: dict = None) -> Optional[Any]:
        now = time.time()
        gap = now - self._last_call
        if gap < self._MIN_REQUEST_GAP_MS / 1000:
            await asyncio.sleep(self._MIN_REQUEST_GAP_MS / 1000 - gap)
        self._last_call = time.time()
        return await self.http.get(f"{self.BASE}{path}", params=params)

    async def get_latest_profiles(self) -> list:
        data = await self._get("/token-profiles/latest/v1")
        return data if isinstance(data, list) else []

    async def get_boosted_tokens(self) -> list:
        data = await self._get("/token-boosts/latest/v1")
        return data if isinstance(data, list) else []

    async def search(self, query: str) -> list:
        data = await self._get("/latest/dex/search", params={"q": query})
        return (data or {}).get("pairs", []) or []

    async def get_pair(self, chain: str, address: str) -> Optional[dict]:
        data = await self._get(f"/latest/dex/pairs/{chain}/{address}")
        pairs = (data or {}).get("pairs", [])
        return pairs[0] if pairs else None

    async def get_token_pairs(self, token_address: str) -> list:
        data = await self._get(f"/latest/dex/tokens/{token_address}")
        return (data or {}).get("pairs", []) or []


def parse_snap(pair: dict) -> Optional[MarketSnapshot]:
    try:
        base  = pair.get("baseToken", {})
        sym   = base.get("symbol", "?").strip()
        name  = base.get("name", "?").strip()
        taddr = base.get("address", "").strip()
        chain = pair.get("chainId", "").strip()
        dex   = pair.get("dexId", "").strip()
        addr  = pair.get("pairAddress", "").strip()

        if not addr or not chain or not sym or sym == "?":
            return None

        def fv(d, k):  return float(d.get(k) or 0)
        def iv(d, k, s): return int((d.get(k) or {}).get(s) or 0)

        vol  = pair.get("volume") or {}
        ch   = pair.get("priceChange") or {}
        txns = pair.get("txns") or {}
        liq  = float((pair.get("liquidity") or {}).get("usd") or 0)
        price = float(pair.get("priceUsd") or 0)

        if price <= 0 or liq <= 0:
            return None

        ca  = pair.get("pairCreatedAt")
        age = (time.time() - ca / 1000) / 3600 if ca else 9999

        return MarketSnapshot(
            pair_address=addr,   token_symbol=sym,    token_name=name,
            token_address=taddr, chain=chain,          dex=dex,
            price_usd=price,
            market_cap=float(pair.get("marketCap") or pair.get("fdv") or 0),
            liquidity=liq,
            volume_5m=fv(vol,"m5"),  volume_1h=fv(vol,"h1"),
            volume_6h=fv(vol,"h6"),  volume_24h=fv(vol,"h24"),
            change_5m=fv(ch,"m5"),   change_1h=fv(ch,"h1"),
            change_6h=fv(ch,"h6"),   change_24h=fv(ch,"h24"),
            buys_5m=iv(txns,"m5","buys"),    sells_5m=iv(txns,"m5","sells"),
            buys_1h=iv(txns,"h1","buys"),    sells_1h=iv(txns,"h1","sells"),
            buys_24h=iv(txns,"h24","buys"),  sells_24h=iv(txns,"h24","sells"),
            age_hours=age,
        )
    except Exception as e:
        log.debug(f"parse_snap xatosi: {e}")
        return None


# 🛡️  GOPLUS SECURITY SCANNER
CHAIN_TO_GOPLUS = {
    "ethereum": "1",   "bsc": "56",    "polygon": "137",
    "arbitrum": "42161", "base": "8453", "solana": "solana",
}

class GoPlusScanner:
    BASE = "https://api.gopluslabs.io/api/v1"

    def __init__(self, http: HttpClient):
        self.http  = http
        self._cache: dict = {}
        self.CACHE_TTL = 1800

    async def scan(self, chain: str, token_address: str) -> SecurityReport:
        if not token_address or len(token_address) < 10:
            return SecurityReport()

        key = f"{chain}:{token_address.lower()}"
        if key in self._cache:
            rep, ts = self._cache[key]
            if time.time() - ts < self.CACHE_TTL:
                return rep

        chain_id = CHAIN_TO_GOPLUS.get(chain)
        if not chain_id:
            return SecurityReport()

        url = (f"{self.BASE}/solana/token_security"
               if chain == "solana" else
               f"{self.BASE}/token_security/{chain_id}")

        data = await self.http.get(url, params={"contract_addresses": token_address})
        rep  = self._parse(data, token_address, chain)
        self._cache[key] = (rep, time.time())
        return rep

    def _parse(self, data: Optional[dict], token_addr: str, chain: str) -> SecurityReport:
        rep = SecurityReport()
        if not data:
            return rep

        result = data.get("result") or {}
        info   = (result.get(token_addr.lower()) or
                  result.get(token_addr) or
                  (list(result.values())[0] if result else {}))
        if not info:
            return rep

        rep.scanned = True

        def b(k): return str(info.get(k, "0")) == "1"
        def f(k): return float(info.get(k) or 0)
        def i(k): return int(info.get(k) or 0)

        rep.is_honeypot     = b("is_honeypot")
        rep.has_mint        = b("is_mintable")
        rep.has_blacklist   = b("is_blacklisted")
        rep.has_proxy       = b("is_proxy")
        rep.sell_tax        = f("sell_tax")
        rep.buy_tax         = f("buy_tax")
        rep.is_open_source  = b("is_open_source")
        rep.holder_count    = i("holder_count")

        owner_addr = info.get("owner_address", "")
        rep.owner_renounced = owner_addr in ("", "0x0000000000000000000000000000000000000000")

        holders = info.get("holders", [])
        if holders:
            rep.top_holder_pct = float(holders[0].get("percent", 0)) * 100

        score = 0
        if rep.is_honeypot:
            score += 60; rep.flags.append("☠️ HONEYPOT aniqlandi!")
        if rep.has_mint:
            score += 25; rep.flags.append("🖨️ Mintable")
        if rep.has_blacklist:
            score += 20; rep.flags.append("🚫 Blacklist")
        if rep.has_proxy:
            score += 15; rep.flags.append("🔄 Proxy")
        if not rep.owner_renounced:
            score += 10; rep.flags.append("👤 Owner not renounced")
        if rep.sell_tax > MAX_SELL_TAX:
            score += 20; rep.flags.append(f"💸 Sell tax {rep.sell_tax:.0f}%")
        if rep.buy_tax > MAX_BUY_TAX:
            score += 15; rep.flags.append(f"💸 Buy tax {rep.buy_tax:.0f}%")
        if rep.top_holder_pct > MAX_TOP_HOLDER_PCT:
            score += 20; rep.flags.append(f"🐳 Top holder {rep.top_holder_pct:.0f}%")

        rep.risk_score = min(100, score)
        return rep

    def passes_strict_filter(self, rep: SecurityReport, snap: "MarketSnapshot") -> tuple[bool, str]:
        if rep.is_honeypot: return False, "Honeypot"
        if rep.risk_score > MAX_SECURITY_RISK: return False, f"Risk score {rep.risk_score}"
        if rep.sell_tax > MAX_SELL_TAX: return False, f"Sell tax {rep.sell_tax}%"
        return True, "OK"


# 📈  COINGECKO TRENDING
class CoinGeckoTrending:
    BASE = "https://api.coingecko.com/api/v3"

    def __init__(self, http: HttpClient):
        self.http = http
        self._trending_symbols: set = set()
        self._last_update = 0
        self.TTL = 600

    async def refresh(self):
        if time.time() - self._last_update < self.TTL: return
        data = await self.http.get(f"{self.BASE}/search/trending")
        if not data: return
        coins = data.get("coins") or []
        self._trending_symbols = {c.get("item", {}).get("symbol", "").upper() for c in coins}
        self._last_update = time.time()

    def is_trending(self, symbol: str) -> bool:
        return symbol.upper() in self._trending_symbols


# 🧠  MORALIS WALLET INTELLIGENCE
class MoralisClient:
    BASE_EVM = "https://deep-index.moralis.io/api/v2.2"

    def __init__(self, http: HttpClient):
        self.http = http
        self.key  = MORALIS_API_KEY
        self._cache: dict = {}
        self.enabled = bool(self.key)

    async def _get(self, url: str, params: dict = None) -> Optional[Any]:
        if not self.enabled: return None
        headers = {"X-API-Key": self.key}
        sess = self.http._get_session()
        try:
            async with sess.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200: return await r.json()
                return None
        except Exception: return None

    async def get_token_owners(self, chain: str, token_address: str) -> list:
        chain_map = {"ethereum":"eth","bsc":"bsc","polygon":"polygon","arbitrum":"arbitrum","base":"base"}
        m_chain = chain_map.get(chain)
        if not m_chain: return []
        data = await self._get(f"{self.BASE_EVM}/erc20/{token_address}/owners", params={"chain": m_chain, "limit": 15})
        return (data or {}).get("result", [])

    async def analyze_wallet(self, chain: str, wallet: str) -> WalletExpertise:
        if wallet in self._cache: return self._cache[wallet]
        chain_map = {"ethereum":"eth","bsc":"bsc","polygon":"polygon","arbitrum":"arbitrum","base":"base"}
        m_chain = chain_map.get(chain)
        if not m_chain: return WalletExpertise(address=wallet)
        data = await self._get(f"{self.BASE_EVM}/wallets/{wallet}/history", params={"chain": m_chain, "limit": 50})
        hist = (data or {}).get("result", [])
        total = len({tx.get("address") for tx in hist if tx.get("address")})
        hits  = min(total // 4, 12)
        rate  = (hits / total * 100) if total >= 5 else (hits * 10)
        perf = WalletExpertise(address=wallet, success_rate=round(rate, 1), alpha_hits=hits, total_trades=total, is_expert=(hits >= 3 and rate > 25))
        self._cache[wallet] = perf
        return perf

    async def detect_smart_money(self, chain: str, token_address: str) -> list:
        if not self.enabled: return []
        owners  = await self.get_token_owners(chain, token_address)
        experts = []
        for owner in owners[:8]:
            addr = owner.get("owner_address")
            if addr:
                perf = await self.analyze_wallet(chain, addr)
                if perf.is_expert: experts.append(perf)
            await asyncio.sleep(0.1)
        return experts


# 🕸️  CROSS-DEX ARBITRAGE DETECTOR
class ArbitrageDetector:
    def __init__(self):
        self._prices: dict = defaultdict(dict)

    def update(self, snap: MarketSnapshot):
        if snap.price_usd > 0: self._prices[snap.token_address][snap.dex] = snap.price_usd

    def check(self, snap: MarketSnapshot) -> tuple:
        prices = self._prices.get(snap.token_address, {})
        if len(prices) < 2: return False, 0.0
        vals = list(prices.values())
        mn, mx = min(vals), max(vals)
        if mn <= 0: return False, 0.0
        spread = (mx - mn) / mn * 100
        return spread > 2.0, round(spread, 2)


# 💧  LIQUIDITY MONITOR
class LiquidityMonitor:
    def __init__(self):
        self._history: dict = defaultdict(lambda: deque(maxlen=20))

    def update(self, snap: MarketSnapshot):
        self._history[snap.pair_address].append(snap.liquidity)

    def analyze(self, snap: MarketSnapshot) -> tuple:
        hist = list(self._history[snap.pair_address])
        if len(hist) < 2: return 0.0, []
        prev, curr = hist[-2], hist[-1]
        change = (curr - prev) / prev * 100 if prev > 0 else 0
        flags  = []
        if change > 8:
            flags.append(f"🐋 LP {change:+.1f}% added")
            return 1.0, flags
        elif change < -8:
            flags.append(f"⚠️ LP {change:+.1f}% removed!")
            return -1.0, flags
        return change / 10, flags


@dataclass
class OpenPosition:
    snap:        MarketSnapshot
    signal_type: str
    entry_price: float
    target_1:    float
    target_2:    float
    stop_loss:   float
    opened_at:   datetime
    t1_hit:      bool = False
    t2_hit:      bool = False
    sl_hit:      bool = False
    peak_price:  float = 0.0   # Yangi: eng yuqori narx (trailing stop uchun)
    last_milestone: float = 0.0 # Oxirgi xabar yuborilgan o'sish foizi


# 🌊  REGIME DETECTOR
class RegimeDetector:
    def __init__(self):
        self._history: deque = deque(maxlen=200)
        self.current: str = "SIDEWAYS"

    def update(self, snaps: list):
        if not snaps: return
        sample = snaps[:80]
        avg1h  = sum(s.change_1h for s in sample) / len(sample)
        avg24h = sum(s.change_24h for s in sample) / len(sample)
        vol    = sum(abs(s.change_1h) for s in sample) / len(sample)
        self._history.append(avg1h)
        if vol > 8: self.current = "VOLATILE"
        elif avg1h > 2 and avg24h > 5: self.current = "BULL"
        elif avg1h < -2 and avg24h < -5: self.current = "BEAR"
        else: self.current = "SIDEWAYS"

    @property
    def emoji(self) -> str:
        return {"BULL":"🟢","BEAR":"🔴","SIDEWAYS":"⬜","VOLATILE":"🟡"}.get(self.current,"⬜")

    @property
    def confidence_delta(self) -> int:
        return {"BULL": -3, "BEAR": +8, "VOLATILE": +10, "SIDEWAYS": 0}.get(self.current, 0)


# 🧬  NEURAL SCORER
class NeuralScorer:
    DEFAULT_WEIGHTS = {
        "buy_ratio_5m": 12.0, "buy_ratio_1h": 15.0, "buy_ratio_24h": 10.0,
        "volume_accel": 8.0, "price_momentum_5m": 7.0, "price_momentum_1h": 9.0,
        "liquidity_depth": 6.0, "liq_to_mcap": 5.0, "vol_to_liq": 6.0,
        "age_score": 6.0, "tx_count_quality": 5.0, "spread_quality": 4.0,
        "security_score": 10.0, "trending_bonus": 5.0, "arb_bonus": 3.0,
        "regime_alignment": 6.0, "expert_wallet_bonus": 8.0, "lp_momentum_bonus": 8.0,
    }

    def __init__(self):
        self.weights = dict(self.DEFAULT_WEIGHTS)

    def _sigmoid(self, x, center=0, scale=1):
        try: return 1 / (1 + math.exp(-scale * (x - center)))
        except OverflowError: return 1.0 if x > center else 0.0

    def _compute(self, snap: MarketSnapshot, sec: SecurityReport, is_trending: bool, arb: bool, regime: str, lp_score: float) -> dict:
        f = {}
        s = self._sigmoid
        f["buy_ratio_5m"]  = s(snap.buy_ratio_5m, 0.55, 8)
        f["buy_ratio_1h"]  = s(snap.buy_ratio_1h, 0.55, 8)
        f["buy_ratio_24h"] = s(snap.buy_ratio_24h, 0.55, 6)
        accel = snap.volume_5m / (snap.volume_1h / 12 + 1) if snap.volume_1h > 0 else 0.5
        f["volume_accel"] = s(accel, 1.5, 2)
        f["price_momentum_5m"] = s(snap.change_5m, 2, 0.3)
        f["price_momentum_1h"] = s(snap.change_1h, 3, 0.2)
        f["liquidity_depth"] = s(math.log10(max(snap.liquidity, 1)), 5, 1.5)
        f["liq_to_mcap"] = s(snap.liquidity / snap.market_cap, 0.15, 10) if snap.market_cap > 0 else 0.4
        f["vol_to_liq"] = s(snap.vol_to_liq_ratio, 0.5, 2)
        f["age_score"] = s(math.log10(max(snap.age_hours, 0.1)), 1.5, 2)
        total_tx = snap.total_txns_24h
        f["tx_count_quality"] = s(total_tx, 300, 0.008)
        f["spread_quality"] = 1.0 - s(abs(snap.buy_ratio_24h - 0.5), 0.35, 10) if total_tx > 10 else 0.3
        f["security_score"] = 1.0 - sec.risk_score / 100 if sec.scanned else 0.5
        f["trending_bonus"] = 0.9 if is_trending else 0.3
        f["arb_bonus"]      = 0.8 if arb else 0.3
        f["expert_wallet_bonus"] = min(1.0, len(getattr(sec, "expert_holders", [])) * 0.2 + 0.3)
        f["lp_momentum_bonus"] = s(lp_score, 0.0, 4)
        bullish = snap.change_1h > 0 and snap.buy_ratio_1h > 0.5
        f["regime_alignment"] = {"BULL": 1.0 if bullish else 0.2, "BEAR": 0.7 if not bullish else 0.2, "SIDEWAYS": 0.5, "VOLATILE": 0.4}.get(regime, 0.5)
        return f

    def score(self, snap: MarketSnapshot, sec: SecurityReport, is_trending: bool, arb: bool, regime: str, lp_score: float) -> tuple:
        factors   = self._compute(snap, sec, is_trending, arb, regime, lp_score)
        total_w   = sum(self.weights.values())
        weighted  = sum(factors[k] * self.weights[k] for k in factors if k in self.weights)
        confidence = max(0, min(100, int(weighted / total_w * 100)))
        return confidence, factors

    def adapt(self, factors: dict, win: bool):
        lr = 0.04
        for k, v in factors.items():
            if k not in self.weights or v < 0.3: continue
            if win and v > 0.65: self.weights[k] = min(30.0, self.weights[k] * (1 + lr * v))
            elif not win and v > 0.65: self.weights[k] = max(1.0, self.weights[k] * (1 - lr * 0.5))


# 🧠  SMC ANALYZER
class SMCAnalyzer:
    def __init__(self):
        self._hist: dict = defaultdict(lambda: deque(maxlen=30))

    def analyze(self, snap: MarketSnapshot) -> tuple:
        h = self._hist[snap.pair_address]
        h.append(snap.price_usd)
        if len(h) < 4: return None, 0
        p = list(h)
        p1, p2, p3, p4 = p[-4], p[-3], p[-2], p[-1]
        if p2 < p1 and p3 < p2 and p4 > p1: return "Bullish BOS", 15
        if p4 > 0 and p1 > 0 and (p4-p1)/p1 > 0.08 and snap.change_1h > 5: return "Bullish FVG", 13
        if snap.change_5m < -4 and snap.change_1h > 3 and snap.buy_ratio_1h > 0.62: return "Liq Sweep + Recovery", 18
        if abs(snap.change_6h) < 2.5 and snap.volume_1h > snap.volume_6h / 3: return "Order Block", 10
        return None, 0


# 📊  MULTI-TIMEFRAME CONFLUENCE
class MTFConfluence:
    def analyze(self, snap: MarketSnapshot) -> tuple:
        tf = {}
        bonus = 0
        def add(name, bias, change, ratio=None):
            tf[name] = {"bias": bias, "change": change}
            if ratio is not None: tf[name]["buy_ratio"] = round(ratio * 100)
        r5 = snap.buy_ratio_5m
        add("5m", "bull" if r5>0.58 else "bear" if r5<0.42 else "neutral", snap.change_5m, r5)
        if r5 > 0.70: bonus += 10
        r1 = snap.buy_ratio_1h
        add("1h", "bull" if r1>0.58 else "bear" if r1<0.42 else "neutral", snap.change_1h, r1)
        if r1 > 0.67: bonus += 13
        add("6h", "bull" if snap.change_6h > 3 else "bear" if snap.change_6h < -3 else "neutral", snap.change_6h)
        add("24h", "bull" if snap.change_24h > 5 else "bear" if snap.change_24h < -5 else "neutral", snap.change_24h)
        biases = [v["bias"] for v in tf.values()]
        if biases.count("bull") == 4: bonus += 22
        elif biases.count("bull") == 3: bonus += 10
        return tf, bonus


# 📚  BACKTEST ENGINE
class BacktestEngine:
    def __init__(self, dex: DexScreenerAPI, neural: NeuralScorer):
        self.dex, self.neural = dex, neural
        self._pending, self._results, self._factors = {}, defaultdict(list), {}

    def record(self, sig: SignalResult, factors: dict):
        self._pending[sig.snapshot.pair_address] = {"chain": sig.snapshot.chain, "entry": sig.entry, "target": sig.target_1, "stop": sig.stop_loss, "signal": sig.signal_type, "time": datetime.now()}
        self._factors[sig.snapshot.pair_address] = factors

    async def check(self, snaps: list):
        snap_map, completed, now = {s.pair_address: s for s in snaps}, [], datetime.now()
        for addr, entry in list(self._pending.items()):
            if (now - entry["time"]).total_seconds() / 3600 < 2: continue
            cur = snap_map.get(addr)
            if not cur:
                p = await self.dex.get_pair(entry["chain"], addr)
                if p: cur = parse_snap(p)
            if cur:
                win, loss = cur.price_usd >= entry["target"], cur.price_usd <= entry["stop"]
                if win or loss or (now - entry["time"]).total_seconds() / 3600 >= 24:
                    res = win if (win or loss) else (cur.price_usd > entry["entry"])
                    self._results[entry["signal"]].append(res)
                    completed.append(addr)
                    if addr in self._factors: self.neural.adapt(self._factors[addr], res)
            elif (now - entry["time"]).total_seconds() / 3600 > 24:
                self._results[entry["signal"]].append(False)
                completed.append(addr)
        for a in completed: self._pending.pop(a, None); self._factors.pop(a, None)

    def winrate(self, stype: str) -> Optional[float]:
        r = self._results.get(stype, [])
        return round(sum(r) / len(r) * 100, 1) if len(r) >= 3 else None

    def overall(self) -> Optional[float]:
        all_r = [x for v in self._results.values() for x in v]
        return round(sum(all_r) / len(all_r) * 100, 1) if len(all_r) >= 5 else None

    def summary(self) -> str:
        lines = []
        for st, res in self._results.items():
            if res:
                wr = sum(res) / len(res) * 100
                lines.append(f"{'✅' if wr>=55 else '⚠️' if wr>=40 else '❌'} <code>{st}</code>: <code>{wr:.0f}%</code> ({len(res)})")
        return "\n".join(lines) if lines else "<i>No data</i>"


# 🚫  RUG DETECTOR
class RugDetector:
    STABLES = {"USDT","USDC","DAI","BUSD","TUSD","FRAX","LUSD","MIM","USDD","USDP","USDE","PYUSD","FDUSD","CRVUSD","GHO"}
    def __init__(self): self._liq_hist = defaultdict(lambda: deque(maxlen=8))
    def check(self, snap: MarketSnapshot, sec: SecurityReport) -> tuple:
        flags, is_rug, is_wash = list(sec.flags), sec.is_honeypot or sec.risk_score >= 55, False
        h = self._liq_hist[snap.pair_address]
        if h and h[-1] > 0 and (h[-1] - snap.liquidity) / h[-1] > 0.20: flags.append("💧 Liq drop!"); is_rug = True
        h.append(snap.liquidity)
        if snap.age_hours < NEW_TOKEN_MIN_HOURS: flags.append("🕐 Too young"); is_rug = True
        if snap.sells_24h == 0 and snap.buys_24h > 20: flags.append("🍯 Honeypot signs"); is_rug = True
        if snap.total_txns_24h > 0 and snap.volume_24h > 300_000 and (snap.volume_24h / snap.total_txns_24h) > 50_000: flags.append("🤖 Wash trading"); is_wash = True
        return is_rug, is_wash, flags


# ⚙️  SIGNAL ENGINE
class SignalEngine:
    def __init__(self, dex, goplus, moralis, trending, neural, backtest):
        self.dex, self.goplus, self.moralis, self.trending, self.neural, self.backtest = dex, goplus, moralis, trending, neural, backtest
        self.rug, self.smc, self.mtf, self.arb, self.lp, self.regime = RugDetector(), SMCAnalyzer(), MTFConfluence(), ArbitrageDetector(), LiquidityMonitor(), RegimeDetector()
        self._seen, self._hour_count, self._hour_reset = {}, 0, datetime.now()

    def _rate_ok(self, addr: str) -> bool:
        now = datetime.now()
        if (now - self._hour_reset).total_seconds() >= 3600: self._hour_count, self._hour_reset = 0, now
        if self._hour_count >= MAX_SIGNALS_PER_HR: return False
        return addr not in self._seen or (now - self._seen[addr]) > timedelta(minutes=COOLDOWN_MINUTES)

    async def analyze(self, snap: MarketSnapshot) -> Optional[SignalResult]:
        self.lp.update(snap)
        lp_score, lp_flags = self.lp.analyze(snap)
        if snap.token_symbol.upper() in RugDetector.STABLES or snap.age_hours <= 0 or snap.age_hours > NEW_TOKEN_MAX_HOURS or snap.age_hours < NEW_TOKEN_MIN_HOURS: return None
        is_moonshot = MOONSHOT_MIN_MCAP < snap.market_cap < MOONSHOT_MAX_MCAP and snap.buy_ratio_5m > MOONSHOT_MIN_BUY_RATIO and snap.volume_5m > MOONSHOT_MIN_VOL_5M
        if snap.liquidity < (MIN_LIQUIDITY*0.5 if is_moonshot else MIN_LIQUIDITY) or (snap.volume_1h < MIN_VOLUME_1H * min(1.0, max(0.2, snap.age_hours)) and snap.volume_24h < MIN_VOLUME_24H): return None
        if snap.price_usd <= 0 or not self._rate_ok(snap.pair_address): return None
        sec = await self.goplus.scan(snap.chain, snap.token_address)
        passed, _ = self.goplus.passes_strict_filter(sec, snap)
        if not passed: return None
        stype = "MOONSHOT_ALPHA" if is_moonshot else ("STRONG_BUY" if snap.buy_ratio_5m > 0.72 and snap.change_5m > 1.5 else ("BREAKOUT" if snap.change_1h > 10 else None))
        if not stype: return None
        is_rug, is_wash, rflags = self.rug.check(snap, sec)
        rflags.extend(lp_flags)
        self.arb.update(snap)
        arb_ok, spread = self.arb.check(snap)
        is_trending = self.trending.is_trending(snap.token_symbol)
        if is_rug:
            self._seen[snap.pair_address], self._hour_count = datetime.now(), self._hour_count + 1
            return SignalResult(snapshot=snap, signal_type="RUG_ALERT", confidence=90, primary_reason="Rug!", confluence=[], risk_flags=rflags, security=sec, smc_pattern=None, regime=self.regime.current, timeframe_align={}, neural_scores={}, backtest_winrate=None, risk_reward=0, entry=snap.price_usd, target_1=0, target_2=0, stop_loss=snap.price_usd*0.5, is_trending=is_trending, security_passed=False)
        conf, factors = self.neural.score(snap, sec, is_trending, arb_ok, self.regime.current, lp_score)
        smc_p, smc_b = self.smc.analyze(snap)
        conf += smc_b
        tf_d, mtf_b = self.mtf.analyze(snap)
        conf += mtf_b // 3 + self.regime.confidence_delta
        if is_wash: conf -= 22
        wr = self.backtest.winrate(stype)
        if wr: conf += 8 if wr>=70 else (4 if wr>=55 else -15)
        conf = max(0, min(100, conf))
        if conf < MIN_CONFIDENCE + self.regime.confidence_delta: return None
        p = snap.price_usd
        entry, t1, t2, sl = (p, p*1.8, p*4, p*0.85) if stype=="MOONSHOT_ALPHA" else (p, p*(1+TARGET_1_PCT/100), p*(1+TARGET_2_PCT/100), p*(1-STOP_LOSS_PCT/100))
        rr = abs(t1-entry)/max(abs(entry-sl), 1e-10)
        if rr < MIN_RR_RATIO and stype != "MOONSHOT_ALPHA": return None
        res = SignalResult(snapshot=snap, signal_type=stype, confidence=conf, primary_reason=stype, confluence=[], risk_flags=rflags, security=sec, smc_pattern=smc_p, regime=self.regime.current, timeframe_align=tf_d, neural_scores=factors, backtest_winrate=wr, risk_reward=round(rr, 2), entry=entry, target_1=t1, target_2=t2, stop_loss=sl, is_trending=is_trending, security_passed=True)
        self._seen[snap.pair_address], self._hour_count = datetime.now(), self._hour_count + 1
        self.backtest.record(res, factors)
        return res


# 🔗  POSITION TRACKER
class PositionTracker:
    def __init__(self, send_fn): self.send, self.positions, self.closed_pl = send_fn, {}, []
    def open(self, sig: SignalResult): self.positions[sig.snapshot.pair_address] = OpenPosition(snap=sig.snapshot, signal_type=sig.signal_type, entry_price=sig.entry, target_1=sig.target_1, target_2=sig.target_2, stop_loss=sig.stop_loss, opened_at=datetime.now(), peak_price=sig.entry)
    async def check_all(self, snaps: list, dex_api=None):
        snap_map, to_close = {s.pair_address: s for s in snaps}, []
        for addr, pos in self.positions.items():
            cur = snap_map.get(addr)
            if not cur and dex_api:
                try:
                    p = await dex_api.get_pair(pos.snap.chain, addr)
                    if p: cur = parse_snap(p)
                except Exception: pass
            if not cur: continue
            p, pnl = cur.price_usd, (cur.price_usd/pos.entry_price-1)*100
            if p > pos.peak_price: pos.peak_price = p
            milestone = math.floor(pnl/50)*50
            if milestone > pos.last_milestone and milestone >= 50:
                pos.last_milestone = milestone
                await self.send(f"📈 <b>{pos.snap.token_symbol} +{pnl:.1f}%</b>")
            if not pos.t1_hit and p >= pos.target_1: pos.t1_hit = True; await self.send(f"🎯 <b>{pos.snap.token_symbol} T1 HIT!</b>")
            elif pos.t1_hit and not pos.t2_hit and p >= pos.target_2: pos.t2_hit = True; self.closed_pl.append(pnl); await self.send(f"🚀 <b>{pos.snap.token_symbol} T2 HIT!</b>"); to_close.append(addr)
            elif not pos.sl_hit and p <= pos.stop_loss: pos.sl_hit = True; self.closed_pl.append(pnl); await self.send(f"🛑 <b>{pos.snap.token_symbol} SL!</b>"); to_close.append(addr)
            elif (datetime.now()-pos.opened_at).total_seconds() > 172800: self.closed_pl.append(pnl); to_close.append(addr)
        for a in to_close: self.positions.pop(a, None)
    def avg_pl(self): return round(sum(self.closed_pl)/len(self.closed_pl), 2) if self.closed_pl else None


# 💬  TELEGRAM XABAR FORMATI
def fmt(sig: SignalResult) -> str:
    s = sig.snapshot
    url = f"https://dexscreener.com/{s.chain}/{s.pair_address}"
    tf_str = "  ".join(f"{'🟢' if d['bias']=='bull' else '🔴' if d['bias']=='bear' else '⬜'}<code>{n}:{d['change']:+.1f}%</code>" for n, d in sig.timeframe_align.items())
    sec = sig.security
    sec_str = f"\n🛡️ <b>Security:</b> {'🟢' if sec.risk_score<20 else '🟡' if sec.risk_score<40 else '🔴'} ({sec.risk_score}/100)\n  Tax: <code>{sec.buy_tax:.0f}/{sec.sell_tax:.0f}%</code>" if sec and sec.scanned else ""
    if sig.signal_type == "RUG_ALERT": return f"☠️ <b>RUG XAVFI! {s.token_symbol}</b>\n{sec_str}\n🔗 <a href='{url}'>DexScreener</a>"
    return f"{sig.emoji} <b>{sig.signal_type} — {s.token_symbol}</b>\nMCap: <code>${s.market_cap:,.0f}</code> | Liq: <code>${s.liquidity:,.0f}</code>\n🎯 <b>Confidence:</b> <code>{sig.bar}</code> <b>{sig.confidence}/100</b>\n📐 <b>T1:</b> <code>+{TARGET_1_PCT:.0f}%</code> | <b>SL:</b> <code>-{STOP_LOSS_PCT:.0f}%</code>\n{sec_str}\n🔗 <a href='{url}'>DexScreener</a>"


# 🤖  ASOSIY BOT
class WhaleTrackerV4:
    def __init__(self):
        self.http, self.paused, self._snaps, self._signals_history = HttpClient(), False, [], deque(maxlen=50)
        self.dex, self.goplus, self.moralis, self.trending = DexScreenerAPI(self.http), GoPlusScanner(self.http), MoralisClient(self.http), CoinGeckoTrending(self.http)
        self.neural, self.backtest = NeuralScorer(), None
        self.engine, self.tracker = None, None
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.total_scans, self.total_signals, self.rug_alerts, self.filtered_out, self.start_time = 0, 0, 0, 0, datetime.now()

        # Dashboard App
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template_string(DASHBOARD_HTML)

        @self.app.route("/api/status")
        def get_status():
            uptime = datetime.now() - self.start_time
            h, m = divmod(uptime.seconds // 60, 60)
            return jsonify({
                "uptime": f"{uptime.days}d {h}h {m}m",
                "scans": self.total_scans,
                "signals": self.total_signals,
                "rug_alerts": self.rug_alerts,
                "filtered": self.filtered_out,
                "winrate": self.backtest.overall() or 0,
                "avg_pnl": self.tracker.avg_pl() or 0,
                "active_positions": len(self.tracker.positions),
                "regime": self.engine.regime.current,
                "paused": self.paused
            })

        @self.app.route("/api/signals")
        def get_signals():
            return jsonify([self._signal_to_dict(s) for s in list(self._signals_history)])

        @self.app.route("/api/positions")
        def get_positions():
            return jsonify([self._pos_to_dict(p) for p in self.tracker.positions.values()])

    def _signal_to_dict(self, sig: SignalResult):
        return {
            "symbol": sig.snapshot.token_symbol,
            "type": sig.signal_type,
            "confidence": sig.confidence,
            "price": sig.snapshot.price_usd,
            "chain": sig.snapshot.chain,
            "time": sig.snapshot.timestamp.strftime("%H:%M:%S"),
            "mcap": sig.snapshot.market_cap,
            "liquidity": sig.snapshot.liquidity,
            "risk_score": sig.security.risk_score if sig.security else 0
        }

    def _pos_to_dict(self, pos: OpenPosition):
        pnl = (pos.snap.price_usd/pos.entry_price-1)*100
        return {
            "symbol": pos.snap.token_symbol,
            "entry": pos.entry_price,
            "current": pos.snap.price_usd,
            "pnl": round(pnl, 2),
            "target1": pos.target_1,
            "stop": pos.stop_loss,
            "age": round((datetime.now()-pos.opened_at).total_seconds()/3600, 1)
        }

    async def send(self, text: str, markup=None):
        try: await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=markup)
        except Exception as e: log.error(f"TG: {e}")

    def _kb(self):
        return InlineKeyboardMarkup([[InlineKeyboardButton("📊 Status", callback_data="status"), InlineKeyboardButton("💼 Pozitsiyalar", callback_data="positions")], [InlineKeyboardButton("▶️ Resume" if self.paused else "⏸ Pause", callback_data="pause"), InlineKeyboardButton("🔍 Hozir skan", callback_data="scan_now")]])

    async def scan(self):
        if self.paused: return
        self.total_scans += 1
        await self.trending.refresh()
        raw, sem = [], asyncio.Semaphore(4)
        async def safe_get_pairs(ta):
            async with sem:
                try: return [p for p in await self.dex.get_token_pairs(ta) if p.get("chainId") in WATCH_CHAINS][:3]
                except: return []
        async def safe_search(q, limit=10):
            async with sem:
                try: return (await self.dex.search(q))[:limit]
                except: return []
        res = await asyncio.gather(self.dex.get_latest_profiles(), self.dex.get_boosted_tokens())
        addrs = {p["tokenAddress"] for p in (res[0] or []) if p.get("tokenAddress")} | {b["tokenAddress"] for b in (res[1] or []) if b.get("tokenAddress")}
        if addrs:
            for r in await asyncio.gather(*[safe_get_pairs(a) for a in list(addrs)[:30]]): raw.extend(r)
        for r in await asyncio.gather(*[safe_search(f"{ch} trending") for ch in WATCH_CHAINS]): raw.extend(r)
        snaps, seen = [], set()
        for p in raw:
            if p.get("pairAddress") and p["pairAddress"] not in seen:
                seen.add(p["pairAddress"])
                s = parse_snap(p)
                if s: snaps.append(s)
        self._snaps = snaps
        self.engine.regime.update(snaps)
        await self.backtest.check(snaps)
        await self.tracker.check_all(snaps, self.dex)
        results = await asyncio.gather(*[self.engine.analyze(s) for s in snaps[:60]])
        signals = [r for r in results if r]
        self.filtered_out += (len(snaps[:60]) - len(signals))
        signals.sort(key=lambda x: x.confidence, reverse=True)
        for sig in signals:
            self.total_signals += 1
            self._signals_history.append(sig)
            if sig.signal_type == "RUG_ALERT": self.rug_alerts += 1
            elif sig.security_passed: self.tracker.open(sig)
            await self.send(fmt(sig))
            await asyncio.sleep(1)

    async def run(self):
        self.backtest = BacktestEngine(self.dex, self.neural)
        self.engine = SignalEngine(self.dex, self.goplus, self.moralis, self.trending, self.neural, self.backtest)
        self.tracker = PositionTracker(self.send)

        # Start Flask in thread
        threading.Thread(target=lambda: self.app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False), daemon=True).start()

        await self.send(f"🚀 <b>Whale Tracker Pro v4.5 DashBoard bilan ishga tushdi!</b>\n🌐 Dashboard: <code>http://localhost:5001</code>", markup=self._kb())

        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", lambda u,c: self.send("Panel:", self._kb())))
        app.add_handler(CallbackQueryHandler(self._h_cb))

        sched = AsyncIOScheduler(timezone=timezone.utc)
        sched.add_job(self.scan, "interval", seconds=SCAN_INTERVAL_SEC, next_run_time=datetime.now(timezone.utc))
        sched.start()

        async with app:
            await app.start(); await app.updater.start_polling()
            try: await asyncio.Event().wait()
            finally: await app.updater.stop(); await app.stop()

    async def _h_cb(self, u, c):
        q = u.callback_query; await q.answer(); d = q.data
        if d == "pause": self.paused = not self.paused
        elif d == "scan_now": asyncio.create_task(self.scan())
        await q.edit_message_text("Yangilandi.", reply_markup=self._kb())

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Whale Tracker Pro Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; }
        .stat-val { color: #38bdf8; font-weight: 700; }
    </style>
</head>
<body>
    <div id="app" class="p-4 max-w-7xl mx-auto">
        <header class="flex justify-between items-center mb-8">
            <h1 class="text-2xl font-bold text-sky-400">🐋 Whale Tracker Pro <span class="text-sm font-normal text-slate-400">v4.5</span></h1>
            <div class="flex gap-4">
                <span class="px-3 py-1 rounded-full text-sm" :class="status.paused ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'">
                    {{ status.paused ? 'PAUSED' : 'LIVE' }}
                </span>
                <span class="text-slate-400 text-sm">Uptime: {{ status.uptime }}</span>
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="card p-4">
                <p class="text-slate-400 text-xs uppercase">Total Scans</p>
                <p class="text-2xl stat-val">{{ status.scans }}</p>
            </div>
            <div class="card p-4">
                <p class="text-slate-400 text-xs uppercase">Signals / Rugs</p>
                <p class="text-2xl stat-val">{{ status.signals }} / <span class="text-red-400">{{ status.rug_alerts }}</span></p>
            </div>
            <div class="card p-4">
                <p class="text-slate-400 text-xs uppercase">Win Rate</p>
                <p class="text-2xl stat-val">{{ status.winrate }}%</p>
            </div>
            <div class="card p-4">
                <p class="text-slate-400 text-xs uppercase">Avg P&L</p>
                <p class="text-2xl stat-val" :class="status.avg_pnl >=0 ? 'text-green-400' : 'text-red-400'">{{ status.avg_pnl }}%</p>
            </div>
        </div>

        <div class="grid md:grid-cols-2 gap-8">
            <!-- Recent Signals -->
            <section class="card p-6">
                <h2 class="text-lg font-semibold mb-4 flex items-center gap-2">📢 Recent Signals <span class="text-xs bg-sky-500/20 text-sky-400 px-2 rounded">Live</span></h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead class="text-slate-400 text-xs uppercase border-b border-slate-700">
                            <tr>
                                <th class="pb-2">Token</th>
                                <th class="pb-2 text-center">Type</th>
                                <th class="pb-2 text-center">Conf.</th>
                                <th class="pb-2 text-right">MCap</th>
                            </tr>
                        </thead>
                        <tbody class="text-sm">
                            <tr v-for="sig in signals" :key="sig.time" class="border-b border-slate-800 hover:bg-slate-800/40 transition">
                                <td class="py-3">
                                    <div class="font-bold text-sky-300">{{ sig.symbol }}</div>
                                    <div class="text-xs text-slate-500 uppercase">{{ sig.chain }} | {{ sig.time }}</div>
                                </td>
                                <td class="py-3 text-center">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold"
                                          :class="sig.type === 'RUG_ALERT' ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'">
                                        {{ sig.type.replace('_', ' ') }}
                                    </span>
                                </td>
                                <td class="py-3 text-center">
                                    <div class="w-12 bg-slate-700 h-1.5 rounded-full mx-auto">
                                        <div class="bg-sky-400 h-1.5 rounded-full" :style="{width: sig.confidence + '%'}"></div>
                                    </div>
                                    <span class="text-[10px]">{{ sig.confidence }}%</span>
                                </td>
                                <td class="py-3 text-right">
                                    <div class="text-slate-300">${{ formatNum(sig.mcap) }}</div>
                                    <div class="text-[10px] text-red-400" v-if="sig.risk_score > 0">Risk: {{ sig.risk_score }}</div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <!-- Active Positions -->
            <section class="card p-6">
                <h2 class="text-lg font-semibold mb-4 flex items-center gap-2">💼 Active Positions <span class="text-xs bg-green-500/20 text-green-400 px-2 rounded">{{ positions.length }}</span></h2>
                <div v-if="positions.length === 0" class="text-slate-500 text-center py-10 italic">No active positions</div>
                <div v-else class="space-y-4">
                    <div v-for="pos in positions" :key="pos.symbol" class="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
                        <div class="flex justify-between items-start mb-2">
                            <div>
                                <span class="font-bold text-white text-lg">{{ pos.symbol }}</span>
                                <span class="text-xs text-slate-500 ml-2">{{ pos.age }}h ago</span>
                            </div>
                            <div class="text-right">
                                <p class="text-lg font-bold" :class="pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'">{{ pos.pnl }}%</p>
                                <p class="text-[10px] text-slate-500">Entry: ${{ pos.entry }}</p>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <div class="flex-1 bg-slate-700 h-2 rounded-full overflow-hidden">
                                <div class="bg-green-500 h-full" :style="{width: Math.min(100, Math.max(0, (pos.pnl + 10)*5)) + '%'}"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </div>

    <script>
        const { createApp } = Vue
        createApp({
            data() {
                return {
                    status: {},
                    signals: [],
                    positions: []
                }
            },
            methods: {
                async fetchData() {
                    try {
                        const [status, signals, positions] = await Promise.all([
                            fetch('/api/status').then(r => r.json()),
                            fetch('/api/signals').then(r => r.json()),
                            fetch('/api/positions').then(r => r.json())
                        ]);
                        this.status = status;
                        this.signals = signals.reverse();
                        this.positions = positions;
                    } catch (e) { console.error("Update failed", e); }
                },
                formatNum(n) {
                    if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
                    if (n >= 1e3) return (n/1e3).toFixed(0) + 'K';
                    return n.toFixed(0);
                }
            },
            mounted() {
                this.fetchData();
                setInterval(this.fetchData, 5000);
            }
        }).mount('#app')
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    asyncio.run(WhaleTrackerV4().run())
