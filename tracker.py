"""
╔══════════════════════════════════════════════════════════════╗
║         💎 Smart Money Finder & Tracker  v1.0              ║
║   Blockchain smart wallet discovery & real-time alerts      ║
╚══════════════════════════════════════════════════════════════╝

O'rnatish:
    pip install python-telegram-bot aiohttp aiosqlite python-dotenv colorlog

Ishga tushirish:
    python tracker.py
"""

import asyncio
import logging
import os
import sys
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import aiosqlite
import colorlog
from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

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
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    for lib in ("httpx", "httpcore", "telegram", "aiohttp"):
        logging.getLogger(lib).setLevel(logging.WARNING)

log = logging.getLogger("SmartMoney")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class ChainConfig:
    name: str
    native_symbol: str
    dex_id: str
    explorer_api: str
    explorer_url: str
    api_key_env: str

CHAINS = {
    "eth": ChainConfig("Ethereum", "ETH", "ethereum", "https://api.etherscan.io/api", "https://etherscan.io", "ETHERSCAN_API_KEY"),
    "bsc": ChainConfig("BSC", "BNB", "bsc", "https://api.bscscan.com/api", "https://bscscan.com", "BSCSCAN_API_KEY"),
    "base": ChainConfig("Base", "ETH", "base", "https://api.basescan.org/api", "https://basescan.org", "BASESCAN_API_KEY"),
    "arbitrum": ChainConfig("Arbitrum", "ETH", "arbitrum", "https://api.arbiscan.io/api", "https://arbiscan.io", "ARBISCAN_API_KEY"),
    "polygon": ChainConfig("Polygon", "MATIC", "polygon", "https://api.polygonscan.com/api", "https://polygonscan.com", "POLYGONSCAN_API_KEY"),
    "avalanche": ChainConfig("Avalanche", "AVAX", "avalanche", "https://api.snowtrace.io/api", "https://snowtrace.io", "SNOWTRACE_API_KEY"),
}

STABLES = {"usdt", "usdc", "dai", "busd", "tusd", "usdp", "frax", "lusd", "gusd", "susd", "cusd"}
WRAPPERS = {"weth", "wbnb", "wmatic", "wavax", "wftm"}

EMOJI = {
    "buy": "🟢", "sell": "🔴", "wallet": "👛", "chart": "📊", "star": "⭐",
    "fire": "🔥", "search": "🔍", "check": "✅", "cross": "❌", "link": "🔗", "clock": "⏳"
}

@dataclass
class AppConfig:
    bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    allowed_users: List[int] = field(default_factory=lambda: [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()])
    min_win_rate: float = field(default_factory=lambda: float(os.getenv("MIN_WIN_RATE", "70")))
    min_pnl_usd: float = field(default_factory=lambda: float(os.getenv("MIN_PNL_USD", "100000")))
    min_trade_count: int = field(default_factory=lambda: int(os.getenv("MIN_TRADE_COUNT", "20")))
    monitor_interval: int = field(default_factory=lambda: int(os.getenv("MONITOR_INTERVAL", "30")))
    discovery_interval: int = field(default_factory=lambda: int(os.getenv("DISCOVERY_INTERVAL", "3600")))
    db_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "smart_money.db"))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

CFG = AppConfig()

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wallets (
    address TEXT NOT NULL,
    chain TEXT NOT NULL,
    label TEXT DEFAULT '',
    win_rate REAL DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    PRIMARY KEY (address, chain)
);
CREATE TABLE IF NOT EXISTS processed_tx (
    hash TEXT PRIMARY KEY,
    timestamp TEXT
);
"""

class Database:
    def __init__(self):
        self._conn = None

    async def connect(self):
        self._conn = await aiosqlite.connect(CFG.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def add_wallet(self, addr, chain, stats, label=""):
        await self._conn.execute(
            "INSERT OR REPLACE INTO wallets (address, chain, label, win_rate, total_pnl, trade_count, is_active) VALUES (?,?,?,?,?,?,1)",
            (addr.lower(), chain, label, stats['win_rate'], stats['pnl'], stats['trades'])
        )
        await self._conn.commit()

    async def get_active_wallets(self):
        async with self._conn.execute("SELECT * FROM wallets WHERE is_active=1") as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def remove_wallet(self, addr):
        await self._conn.execute("UPDATE wallets SET is_active=0 WHERE address=?", (addr.lower(),))
        await self._conn.commit()

    async def is_tx_processed(self, tx_hash):
        async with self._conn.execute("SELECT 1 FROM processed_tx WHERE hash=?", (tx_hash,)) as cur:
            return await cur.fetchone() is not None

    async def mark_tx_processed(self, tx_hash):
        await self._conn.execute("INSERT OR IGNORE INTO processed_tx (hash, timestamp) VALUES (?,?)", (tx_hash, datetime.now().isoformat()))
        await self._conn.commit()

DB = Database()

# ─────────────────────────────────────────────
# API CLIENTS
# ─────────────────────────────────────────────

async def fetch_json(url, params=None, headers=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=15) as resp:
                if resp.status == 200: return await resp.json()
                elif resp.status == 429:
                    log.warning("Rate limit hit, sleeping...")
                    await asyncio.sleep(5)
    except: pass
    return None

class DexScreener:
    @staticmethod
    async def get_token(addr):
        data = await fetch_json(f"https://api.dexscreener.com/latest/dex/tokens/{addr}")
        if data and data.get("pairs"):
            # Get best pair by liquidity
            pairs = [p for p in data["pairs"] if p.get("liquidity", {}).get("usd", 0) > 1000]
            if not pairs: pairs = data["pairs"]
            pair = sorted(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)[0]
            return {
                "price": float(pair.get("priceUsd", 0)),
                "mcap": pair.get("fdv", 0) or pair.get("marketCap", 0),
                "symbol": pair.get("baseToken", {}).get("symbol", "???"),
                "name": pair.get("baseToken", {}).get("name", "Unknown"),
                "change24h": float(pair.get("priceChange", {}).get("h24", 0)),
                "pair_url": pair.get("url", "")
            }
        return None

    @staticmethod
    async def get_trending():
        data = await fetch_json("https://api.dexscreener.com/token-boosts/latest/v1")
        return data if isinstance(data, list) else []

class Explorer:
    @staticmethod
    async def get_txs(addr, chain, limit=50):
        cfg = CHAINS.get(chain)
        if not cfg: return []
        params = {
            "module": "account", "action": "tokentx", "address": addr,
            "sort": "desc", "offset": limit, "page": 1, "apikey": os.getenv(cfg.api_key_env, "")
        }
        data = await fetch_json(cfg.explorer_api, params=params)
        return data.get("result", []) if data and data.get("status") == "1" else []

    @staticmethod
    async def get_early_buyers(token_addr, chain):
        cfg = CHAINS.get(chain)
        if not cfg: return []
        params = {
            "module": "account", "action": "tokentx", "contractaddress": token_addr,
            "sort": "asc", "offset": 50, "page": 1, "apikey": os.getenv(cfg.api_key_env, "")
        }
        data = await fetch_json(cfg.explorer_api, params=params)
        if data and data.get("status") == "1":
            return list(set(tx.get("to", "").lower() for tx in data["result"] if tx.get("to")))
        return []

# ─────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────

class Analyzer:
    @staticmethod
    async def get_wallet_stats(addr, chain):
        txs = await Explorer.get_txs(addr, chain, limit=100)
        if not txs: return {"win_rate": 0, "pnl": 0, "trades": 0}

        tokens = defaultdict(lambda: {"buys": 0, "sells": 0})
        for tx in txs:
            t_addr = tx.get("contractAddress", "").lower()
            if not t_addr or (tx.get("tokenSymbol", "").lower() in STABLES | WRAPPERS): continue

            decimals = int(tx.get("tokenDecimal") or 18)
            amt = int(tx.get("value") or 0) / (10**decimals)
            if tx.get("to", "").lower() == addr.lower(): tokens[t_addr]["buys"] += amt
            else: tokens[t_addr]["sells"] += amt

        total_pnl, wins, count = 0, 0, 0
        # Optimization: Only check top 10 tokens to avoid rate limits
        token_list = list(tokens.items())[:15]
        for t_addr, data in token_list:
            if data["buys"] == 0: continue
            info = await DexScreener.get_token(t_addr)
            if not info: continue

            price = info["price"]
            # Estimate entry price based on 24h change (approximation)
            entry = price / (1 + (info["change24h"] / 100))
            pnl = (data["sells"] * price + (data["buys"] - data["sells"]) * price) - (data["buys"] * entry)
            total_pnl += pnl
            if pnl > 0: wins += 1
            count += 1
            await asyncio.sleep(0.2)

        return {"win_rate": (wins/count*100) if count > 0 else 0, "pnl": total_pnl, "trades": count}

# ─────────────────────────────────────────────
# CORE ENGINE
# ─────────────────────────────────────────────

class Engine:
    def __init__(self, bot):
        self.bot = bot
        self.is_running = True

    async def discover(self, chat_id=None):
        if chat_id: await self.bot.send_message(chat_id, f"{EMOJI['search']} Yangi aqlli hamyonlar qidirilmoqda...")
        trending = await DexScreener.get_trending()
        if not trending: return

        found_any = False
        for item in trending[:5]:
            t_addr = item.get("tokenAddress")
            chain = item.get("chainId")
            c_key = next((k for k, v in CHAINS.items() if v.dex_id == chain), None)
            if not c_key: continue

            buyers = await Explorer.get_early_buyers(t_addr, c_key)
            for b_addr in buyers[:10]:
                stats = await Analyzer.get_wallet_stats(b_addr, c_key)
                if stats["win_rate"] >= CFG.min_win_rate and stats["pnl"] >= CFG.min_pnl_usd and stats["trades"] >= CFG.min_trade_count:
                    await DB.add_wallet(b_addr, c_key, stats, f"Auto_{b_addr[:4]}")
                    msg = (f"✨ <b>Yangi aqlli hamyon topildi!</b>\n\n"
                           f"Manzil: <code>{b_addr}</code>\nTarmoq: {c_key.upper()}\n"
                           f"Win Rate: {stats['win_rate']:.1f}%\nPnL: ${stats['pnl']:,.0f}\n"
                           f"Savdolar: {stats['trades']}")
                    await self.bot.send_message(CFG.telegram_chat_id, msg)
                    found_any = True
        if chat_id and not found_any: await self.bot.send_message(chat_id, "❌ Hozircha yangi aqlli hamyonlar topilmadi.")
        elif chat_id: await self.bot.send_message(chat_id, "✅ Qidiruv yakunlandi.")

    async def monitor(self):
        while self.is_running:
            try:
                wallets = await DB.get_active_wallets()
                for w in wallets:
                    txs = await Explorer.get_txs(w["address"], w["chain"], limit=5)
                    for tx in reversed(txs):
                        h = tx.get("hash")
                        if not h or await DB.is_tx_processed(h): continue
                        await self.alert_tx(w, tx)
                        await DB.mark_tx_processed(h)
                    await asyncio.sleep(0.5)
            except Exception as e:
                log.error(f"Monitor xatosi: {e}")
            await asyncio.sleep(CFG.monitor_interval)

    async def alert_tx(self, wallet, tx):
        is_buy = tx.get("to", "").lower() == wallet["address"].lower()
        t_addr = tx.get("contractAddress")
        info = await DexScreener.get_token(t_addr)
        if not info: return

        decimals = int(tx.get("tokenDecimal") or 18)
        amt = int(tx.get("value") or 0) / (10**decimals)
        usd = amt * info["price"]
        if usd < 100: return # Skip dust

        msg = (f"{EMOJI['buy'] if is_buy else EMOJI['sell']} <b>{'SOTIB OLINDI' if is_buy else 'SOTILDI'}</b>\n"
               f"Hamyon: {wallet['label']} ({wallet['win_rate']:.1f}% WR)\n"
               f"Token: {info['symbol']} (${usd:,.2f})\n"
               f"Narx: ${info['price']:.8f} | MCAP: ${info['mcap']:,.0f}\n"
               f"<a href='{info['pair_url']}'>DexScreener orqali ko'rish</a>")
        await self.bot.send_message(CFG.telegram_chat_id, msg)

# ─────────────────────────────────────────────
# BOT HANDLERS
# ─────────────────────────────────────────────

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("💎 <b>Smart Money Tracker PRO</b>\n\n"
                               "/list - Kuzatuvdagi hamyonlar\n"
                               "/find - Yangi aqlli hamyonlarni qidirish\n"
                               "/add <manzil> <tarmoq> - Hamyon qo'shish\n"
                               "/remove <manzil> - Kuzatuvdan o'chirish\n"
                               "/stats <manzil> <tarmoq> - Statistika", parse_mode=ParseMode.HTML)

async def cmd_list(u: Update, c: ContextTypes.DEFAULT_TYPE):
    wallets = await DB.get_active_wallets()
    if not wallets: return await u.message.reply_text("Hozircha kuzatuvda hamyonlar yo'q.")
    res = "📋 <b>Kuzatuvdagi hamyonlar:</b>\n\n"
    for i, w in enumerate(wallets, 1):
        res += f"{i}. <code>{w['address'][:10]}...</code> ({w['chain'].upper()})\n   └ WR: {w['win_rate']:.1f}%, PnL: ${w['total_pnl']:,.0f}\n"
    await u.message.reply_text(res, parse_mode=ParseMode.HTML)

async def cmd_add(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if len(c.args) < 2: return await u.message.reply_text("Foydalanish: /add <manzil> <tarmoq>\nTarmoqlar: eth, bsc, base, arbitrum, polygon, avalanche")
    addr, chain = c.args[0], c.args[1].lower()
    if chain not in CHAINS: return await u.message.reply_text("Noto'g'ri tarmoq.")

    msg = await u.message.reply_text(f"{EMOJI['clock']} Hamyon tahlil qilinmoqda...")
    stats = await Analyzer.get_wallet_stats(addr, chain)
    await DB.add_wallet(addr, chain, stats, f"Manual_{addr[:4]}")
    await msg.edit_text(f"✅ Hamyon qo'shildi!\nWin Rate: {stats['win_rate']:.1f}%, PnL: ${stats['pnl']:,.0f}")

async def cmd_remove(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args: return await u.message.reply_text("Foydalanish: /remove <manzil>")
    await DB.remove_wallet(c.args[0])
    await u.message.reply_text(f"🗑 Hamyon o'chirildi: {c.args[0]}")

async def cmd_stats(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if len(c.args) < 2: return await u.message.reply_text("Foydalanish: /stats <manzil> <tarmoq>")
    addr, chain = c.args[0], c.args[1].lower()
    msg = await u.message.reply_text(f"{EMOJI['clock']} Statistika hisoblanmoqda...")
    stats = await Analyzer.get_wallet_stats(addr, chain)
    res = (f"📊 <b>Statistika: {addr[:10]}...</b>\n\n"
           f"Win Rate: {stats['win_rate']:.1f}%\n"
           f"PnL: ${stats['pnl']:,.0f}\n"
           f"Jami savdolar: {stats['trades']}")
    await msg.edit_text(res, parse_mode=ParseMode.HTML)

async def main():
    if not CFG.bot_token:
        print("XATO: TELEGRAM_BOT_TOKEN topilmadi.")
        return

    await DB.connect()
    _setup_logging()

    app = Application.builder().token(CFG.bot_token).build()
    engine = Engine(app.bot)

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("stats", cmd_stats))

    async def handle_find(u, c):
        await engine.discover(u.effective_chat.id)
    app.add_handler(CommandHandler("find", handle_find))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    log.info("Dastur ishga tushdi.")

    # Background discovery task
    async def background_discovery():
        while True:
            await asyncio.sleep(CFG.discovery_interval)
            await engine.discover()

    # Run tasks
    try:
        await asyncio.gather(
            engine.monitor(),
            background_discovery()
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("To'xtatilmoqda...")
    finally:
        engine.is_running = False
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
