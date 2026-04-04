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
    pip install aiohttp python-telegram-bot apscheduler colorama python-dotenv

Ishga tushirish:
    python whale_tracker_v4.py
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
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import aiohttp
from colorama import Fore, Style, init

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

# --- Web Dashboard Imports ---
import threading
try:
    from fastapi import FastAPI, Response
    from fastapi.responses import HTMLResponse
    import uvicorn
except ImportError:
    print("❌ Dashboard uchun zarur kutubxonalar yo'q: pip install fastapi uvicorn")
    # Dashboard o'chirilgan holda davom etamiz
    FastAPI = None

init(autoreset=True)

# ══════════════════════════════════════════════════════════════
#  ⚙️  SOZLAMALAR — Hardcoded credentials
# ══════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = "7256069971:AAHNTBZZipJI9mF1K1lRyNiQb2n7qEEDEDY"
TELEGRAM_CHAT_ID   = "798283148"
MORALIS_API_KEY    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6ImM5ZTFhYjE4LTRiNDktNGI5Ni04ZjBkLWRmNTE1MmI3NmQ4MCIsIm9yZ0lkIjoiNTA3NzI2IiwidXNlcklkIjoiNTIyNDE3IiwidHlwZUlkIjoiYjQwZTBiZDAtMDcxMi00ZGI1LWI3OTQtZjU1OGZiYjI2YzZjIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NzQ5NTU2NzAsImV4cCI6NDkzMDcxNTY3MH0.ydI7mToaxqNG2qT5gvPymI4sb-MbjEWW37Ik6IoKpnk"
HELIUS_API_KEY     = "f240c386-6489-4e71-8f68-e0a9fa153185"

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
WATCH_CHAINS        = ["solana"] # Faqat Solana tarmog'i ixtisoslashuvi

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
    level=logging.DEBUG, # Chuqur tahlil uchun DEBUG rejimi yoqildi
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("wtp_v4.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("WTP-v4")

# ══════════════════════════════════════════════════════════════
#  🌐  WEB DASHBOARD STATE & UI
# ══════════════════════════════════════════════════════════════

class GlobalState:
    """Dashboard ma'lumotlarini markaziy boshqarish."""
    def __init__(self):
        self.signals = deque(maxlen=50)
        self.positions = []
        self.top_performers = []
        self.stats = {
            "total_scans": 0,
            "total_signals": 0,
            "rug_alerts": 0,
            "wins": 0,
            "losses": 0,
            "daily_pl": 0.0,
            "active_positions_count": 0,
            "regime": "SIDEWAYS",
            "regime_emoji": "⬜"
        }
        self.last_update = datetime.now()

    def update_stats(self, **kwargs):
        self.stats.update(kwargs)
        self.last_update = datetime.now()

    def add_signal(self, sig):
        self.signals.appendleft(sig)
        self.stats["total_signals"] += 1

    def set_positions(self, pos_list):
        self.positions = pos_list
        self.stats["active_positions_count"] = len(pos_list)

G_STATE = GlobalState()

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Whale Tracker Pro | Interactive Alpha Console</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030712;
            --card-bg: rgba(17, 24, 39, 0.7);
            --accent: #22d3ee;
            --accent-glow: rgba(34, 211, 238, 0.3);
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text-main: #f9fafb;
            --text-dim: #9ca3af;
            --glass-border: rgba(255, 255, 255, 0.08);
            --modal-overlay: rgba(0, 0, 0, 0.85);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(34, 211, 238, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(99, 102, 241, 0.05) 0%, transparent 40%);
        }

        h1, h2, h3 { font-family: 'Outfit', sans-serif; }

        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3rem;
            padding: 1.5rem 2rem;
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }

        .logo-group { display: flex; align-items: center; gap: 1rem; }
        .logo-icon {
            width: 48px; height: 48px;
            background: linear-gradient(135deg, var(--accent), #6366f1);
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.5rem; color: white;
            box-shadow: 0 0 20px var(--accent-glow);
        }
        .logo-text h1 { font-size: 1.5rem; letter-spacing: -0.5px; }
        .logo-text span { font-size: 0.75rem; color: var(--accent); font-weight: 600; text-transform: uppercase; }

        .status-badge {
            display: flex; align-items: center; gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            padding: 0.5rem 1rem;
            border-radius: 99px;
            font-size: 0.875rem; font-weight: 600;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .stat-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            padding: 1.5rem;
            border-radius: 24px;
            transition: transform 0.3s ease;
        }
        .stat-card:hover { transform: translateY(-5px); border-color: var(--accent); }
        .stat-label { font-size: 0.875rem; color: var(--text-dim); margin-bottom: 0.5rem; }
        .stat-value { font-size: 1.75rem; font-weight: 800; font-family: 'Outfit'; color: var(--text-main); }
        .stat-value.accent { color: var(--accent); }
        .stat-value.success { color: var(--success); }

        .dashboard-layout {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
        }

        .section-title {
            display: flex; align-items: center; gap: 0.75rem;
            margin-bottom: 1.5rem;
            font-size: 1.25rem; font-weight: 700;
        }
        .section-title i { color: var(--accent); }

        .signals-stream {
            display: flex; flex-direction: column; gap: 1rem;
        }

        .signal-card {
            background: var(--card-bg);
            backdrop-filter: blur(8px);
            border: 1px solid var(--glass-border);
            padding: 1.25rem;
            border-radius: 20px;
            display: grid;
            grid-template-columns: 80px 1fr auto;
            align-items: center;
            gap: 1.5rem;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .signal-card:hover { 
            transform: translateX(10px); 
            background: rgba(31, 41, 55, 0.9); 
            border-color: var(--accent);
            box-shadow: 0 0 20px rgba(34, 211, 238, 0.1);
        }

        .chain-badge {
            width: 80px; text-align: center;
            padding: 0.25rem; border-radius: 8px;
            background: rgba(255,255,255,0.05);
            font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
            color: var(--text-dim); border: 1px solid var(--glass-border);
        }
        .chain-solana { color: #14f195; border-color: rgba(20, 241, 149, 0.3); }
        .chain-ethereum { color: #627eea; border-color: rgba(98, 126, 234, 0.3); }
        .chain-bsc { color: #f3ba2f; border-color: rgba(243, 186, 47, 0.3); }

        .token-info h3 { font-size: 1.125rem; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.5rem; }
        .token-info p { font-size: 0.875rem; color: var(--text-dim); }
        
        .signal-type {
            padding: 0.15rem 0.5rem; border-radius: 6px; font-size: 0.65rem; font-weight: 800;
            text-transform: uppercase;
        }
        .type-moonshot { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
        .type-strong-buy { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .type-breakout { background: rgba(34, 211, 238, 0.1); color: var(--accent); }

        .confidence-circle { text-align: center; }
        .conf-val { font-size: 1.25rem; font-weight: 800; color: var(--accent); display: block; }
        .conf-label { font-size: 0.65rem; color: var(--text-dim); text-transform: uppercase; }

        /* Detail Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: var(--modal-overlay);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: none;
            align-items: center; justify-content: center;
            opacity: 0; transition: opacity 0.3s ease;
        }
        .modal-overlay.active { display: flex; opacity: 1; }

        .modal-content {
            background: #0f172a;
            width: 90%; max-width: 1200px; height: 85vh;
            border-radius: 32px;
            border: 1px solid var(--glass-border);
            display: grid; grid-template-columns: 1fr 400px;
            overflow: hidden;
            position: relative;
            box-shadow: 0 0 50px rgba(0,0,0,0.8);
            transform: scale(0.95); transition: transform 0.3s ease;
        }
        .modal-overlay.active .modal-content { transform: scale(1); }

        .modal-close {
            position: absolute; top: 1.5rem; right: 1.5rem;
            width: 40px; height: 40px; background: rgba(255,255,255,0.05);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            cursor: pointer; color: white; z-index: 1010; transition: background 0.2s;
        }
        .modal-close:hover { background: var(--danger); }

        .chart-container { background: #000; position: relative; }
        .chart-container iframe { width: 100%; height: 100%; border: none; }

        .details-panel {
            padding: 2rem; overflow-y: auto;
            border-left: 1px solid var(--glass-border);
            background: rgba(15, 23, 42, 0.8);
        }

        .token-header { margin-bottom: 2rem; }
        .token-header h2 { font-size: 2rem; margin-bottom: 0.5rem; }
        .ca-box {
            background: rgba(255,255,255,0.05); padding: 0.75rem 1rem; border-radius: 12px;
            font-family: monospace; font-size: 0.875rem; color: var(--accent);
            display: flex; justify-content: space-between; align-items: center;
            cursor: pointer; transition: background 0.2s;
        }
        .ca-box:hover { background: rgba(255,255,255,0.1); }

        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }
        .info-item { background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 16px; }
        .info-item label { font-size: 0.75rem; color: var(--text-dim); display: block; margin-bottom: 0.25rem; }
        .info-item span { font-weight: 700; font-size: 1rem; }

        .security-section { margin-bottom: 2rem; }
        .sec-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .sec-status { font-weight: 600; }
        .sec-status.pass { color: var(--success); }
        .sec-status.fail { color: var(--danger); }

        .factor-tag {
            display: inline-block; padding: 0.4rem 0.8rem; border-radius: 8px;
            background: rgba(34, 211, 238, 0.1); color: var(--accent);
            font-size: 0.75rem; font-weight: 600; margin: 0.25rem;
        }

        .action-btn {
            width: 100%; padding: 1rem; border-radius: 16px; border: none;
            background: var(--accent); color: #000; font-weight: 800; cursor: pointer;
            text-transform: uppercase; letter-spacing: 1px; transition: transform 0.2s;
        }
        .action-btn:hover { transform: scale(1.02); background: #67e8f9; }

        .side-panel { display: flex; flex-direction: column; gap: 2rem; }
        .panel-card { background: var(--card-bg); border: 1px solid var(--glass-border); padding: 1.5rem; border-radius: 24px; }

        .position-item { display: flex; justify-content: space-between; align-items: center; padding: 1rem 0; border-bottom: 1px solid var(--glass-border); }
        .pos-pnl { font-size: 0.875rem; font-weight: 700; }
        .pnl-plus { color: var(--success); }
        .pnl-minus { color: var(--danger); }

        /* Web Console Styles */
        .log-section {
            margin-top: 3rem; background: #000; border: 1px solid var(--glass-border);
            border-radius: 24px; padding: 1.5rem; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }
        .log-header { 
            display: flex; justify-content: space-between; align-items: center; 
            margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .log-container {
            height: 350px; overflow-y: auto; font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.8125rem; line-height: 1.5; color: #d1d5db; white-space: pre-wrap;
            padding: 1rem; background: rgba(255,255,255,0.02); border-radius: 12px;
            scrollbar-width: thin; scrollbar-color: var(--accent) transparent;
        }
        .log-line-debug { color: #9ca3af; }
        .log-line-info { color: #22d3ee; }
        .log-line-error { color: #f87171; font-weight: 700; }

        @media (max-width: 1024px) {
            .dashboard-layout { grid-template-columns: 1fr; }
            .modal-content { grid-template-columns: 1fr; height: 95vh; margin-top: 5vh; }
            .details-panel { border-left: none; border-top: 1px solid var(--glass-border); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-group">
                <div class="logo-icon">🐋</div>
                <div class="logo-text"><h1>WHALE TRACKER <span>Pro v4.5</span></h1></div>
            </div>
            <div id="regime-status" class="status-badge">
                <span id="regime-emoji">⬜</span> <span id="regime-text">Analysing Market...</span>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card"><p class="stat-label">Total Scanned</p><div id="stat-scans" class="stat-value">0</div></div>
            <div class="stat-card"><p class="stat-label">Signals (24h)</p><div id="stat-signals" class="stat-value accent">0</div></div>
            <div class="stat-card"><p class="stat-label">Wins ✅</p><div id="stat-wins" class="stat-value success">0</div></div>
            <div class="stat-card"><p class="stat-label">Losses ❌</p><div id="stat-losses" class="stat-value" style="color: var(--danger)">0</div></div>
            <div class="stat-card"><p class="stat-label">Active Snipes</p><div id="stat-active" class="stat-value accent">0</div></div>
            <div class="stat-card"><p class="stat-label">Blocked</p><div id="stat-rugs" class="stat-value" style="color: var(--danger)">0</div></div>
        </div>

        <div class="dashboard-layout">
            <main>
                <div class="section-title"><i>📡</i> Live Alpha Stream</div>
                <div id="signals-container" class="signals-stream">
                    <div style="text-align: center; padding: 3rem; color: var(--text-dim)">Waiting for fresh liquidity...</div>
                </div>
            </main>
            <aside class="side-panel">
                <div class="panel-card">
                    <div class="section-title"><i>💼</i> Open Trades</div>
                    <div id="positions-container"></div>
                </div>
                <div class="panel-card" style="background: linear-gradient(135deg, rgba(34,211,238,0.05), rgba(99,102,241,0.05))">
                    <div class="section-title"><i>🛡️</i> Neural Health</div>
                    <p style="font-size: 0.875rem; color: var(--text-dim)">Core weights optimized for ${WATCH_CHAINS.length} chains.</p>
                </div>
            </aside>
        </div>

        <div class="log-section">
            <div class="log-header">
                <div class="section-title"><i>📟</i> Live Console Logs</div>
                <div class="status-badge" style="background: rgba(34,211,238,0.05); color: var(--accent); border-color: rgba(34,211,238,0.1)">
                    Real-time Stream
                </div>
            </div>
            <div id="log-display" class="log-container">Initializing console stream...</div>
        </div>
    </div>

    <!-- Details Modal -->
    <div id="modal" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-close" onclick="closeModal()">✕</div>
            <div class="chart-container" id="chart-area">
                <div style="display:flex; height:100%; align-items:center; justify-content:center; color:white;">Select a coin to load live chart</div>
            </div>
            <div class="details-panel" id="detail-area">
                <!-- Loaded dynamically -->
            </div>
        </div>
    </div>

    <script>
        let currentData = null;

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            alert("Contract Address Copied!");
        }

        function closeModal() {
            document.getElementById('modal').classList.remove('active');
            document.getElementById('chart-area').innerHTML = '';
        }

        function showDetails(sigId) {
            const sig = currentData.signals.find(s => s.id === sigId);
            if (!sig) return;

            const modal = document.getElementById('modal');
            const chartArea = document.getElementById('chart-area');
            const detailArea = document.getElementById('detail-area');

            // Load Chart
            chartArea.innerHTML = `<iframe src="https://dexscreener.com/${sig.chain.toLowerCase()}/${sig.addr}?embed=1&theme=dark&trades=0"></iframe>`;

            const recHtml = sig.recommendation ? `
                <div class="rec-banner" style="background: ${sig.rec_color || '#fbbf24'}; color: #fff; padding: 15px; border-radius: 16px; text-align: center; font-size: 22px; font-weight: 900; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); border: 2px solid rgba(255,255,255,0.2);">
                   ${sig.recommendation}
                </div>` : '';

            // Load Details
            detailArea.innerHTML = `
                ${recHtml}
                <div class="token-header">
                    <h2>$${sig.symbol}</h2>
                    <div class="ca-box" onclick="copyToClipboard('${sig.token_addr}')">
                        ${sig.token_addr.substring(0,10)}...${sig.token_addr.substring(sig.token_addr.length-6)}
                        <span>📋</span>
                    </div>
                </div>

                <div class="info-grid">
                    <div class="info-item"><label>Price (USD)</label><span>$${sig.price}</span></div>
                    <div class="info-item"><label>Market Cap</label><span>$${sig.mcap}</span></div>
                    <div class="info-item"><label>Liquidity</label><span>$${sig.liq}</span></div>
                    <div class="info-item"><label>Token Age</label><span>${sig.age}</span></div>
                </div>

                <div class="security-section" style="border-left: 4px solid ${sig.rec_color || '#71717a'}; background: rgba(0,0,0,0.2); padding: 12px; margin-top: 15px;">
                    <div class="section-title" style="margin-bottom: 8px;">🚩 Analiz Natijasi: ${sig.recommendation}</div>
                    <div style="font-size: 0.95rem; color: #e4e4e7; line-height: 1.5;">
                        ${sig.primary_reason || 'Tahlil kutilmoqda...'}
                    </div>
                </div>

                <div class="security-section">
                    <div class="section-title">🐋 Insider Analysis (SOL Only)</div>
                    <div class="sec-row"><span>Risk Level</span><span class="sec-status ${sig.insider_report && sig.insider_report.risk && sig.insider_report.risk.includes('HIGH') ? 'fail' : 'pass'}">${(sig.insider_report && sig.insider_report.risk) || 'Analyzing...'}</span></div>
                    <div class="sec-row"><span>Top Holders Concentration</span><span class="sec-status">${(sig.insider_report && sig.insider_report.concentration) || 'Waiting...'}</span></div>
                    <div class="sec-row"><span>Launch Snipers (120s)</span><span class="sec-status ${(sig.insider_report && sig.insider_report.snipers_found > 5) ? 'fail' : 'pass'}">${(sig.insider_report && sig.insider_report.snipers_found) || 0} ta</span></div>
                    <div class="sec-row"><span>Scanner Status</span><span class="sec-status">${(sig.insider_report && sig.insider_report.status) || 'Checking SOL RPC...'}</span></div>
                </div>

                <div class="security-section">
                    <div class="section-title">🛡️ Security Report</div>
                    <div class="sec-row"><span>Honeypot Check</span><span class="sec-status ${sig.sec.is_hp ? 'fail' : 'pass'}">${sig.sec.is_hp ? 'FAIL' : 'SAFE'}</span></div>
                    <div class="sec-row"><span>Mint Status</span><span class="sec-status ${sig.sec.has_mint ? 'fail' : 'pass'}">${sig.sec.has_mint ? 'MINTABLE' : 'LOCKED'}</span></div>
                    <div class="sec-row"><span>Top Holder</span><span class="sec-status">${sig.sec.top_pct.toFixed(1)}%</span></div>
                    <div class="sec-row"><span>Buy/Sell Tax</span><span class="sec-status">${sig.sec.btax}% / ${sig.sec.stax}%</span></div>
                </div>

                <div class="security-section">
                    <div class="section-title">🧬 Confluence Factors</div>
                    <div>${sig.confluence.map(f => `<span class="factor-tag">${f}</span>`).join('')}</div>
                </div>

                <div style="margin-top: auto">
                    <button class="action-btn" onclick="window.open('https://dexscreener.com/${sig.chain.toLowerCase()}/${sig.addr}', '_blank')">View on DexScreener</button>
                </div>
            `;

            modal.classList.add('active');
        }

        async function updateDashboard() {
            try {
                const response = await fetch('/api/data');
                currentData = await response.json();
                
                document.getElementById('stat-scans').innerText = currentData.stats.total_scans.toLocaleString();
                document.getElementById('stat-signals').innerText = currentData.stats.total_signals;
                document.getElementById('stat-wins').innerText = currentData.stats.wins;
                document.getElementById('stat-losses').innerText = currentData.stats.losses;
                document.getElementById('stat-active').innerText = currentData.stats.active_positions_count;
                document.getElementById('stat-rugs').innerText = currentData.stats.rug_alerts;
                document.getElementById('regime-text').innerText = 'Market: ' + currentData.stats.regime;
                document.getElementById('regime-emoji').innerText = currentData.stats.regime_emoji;

                const sigContainer = document.getElementById('signals-container');
                if (currentData.signals.length > 0) {
                    sigContainer.innerHTML = currentData.signals.map(s => `
                        <div class="signal-card" onclick="showDetails('${s.id}')">
                            <div class="chain-badge chain-${s.chain.toLowerCase()}">${s.chain}</div>
                            <div class="token-info">
                                <h3>$${s.symbol} <span class="signal-type type-${s.type.toLowerCase().replace('_','-')}">${s.type}</span></h3>
                                <p>${s.name} • $${s.price} • ${s.age}</p>
                                <div style="font-size: 0.75rem; color: #a1a1aa; margin-top: 5px; line-height: 1.2;">
                                    📝 ${s.primary_reason || 'Tahlil yakunlangan'}
                                </div>
                            </div>
                            <div class="confidence-circle">
                                <span class="conf-val">${s.confidence}%</span>
                                <span class="conf-label">Alpha</span>
                            </div>
                        </div>
                    `).join('');
                }

                const posContainer = document.getElementById('positions-container');
                if (currentData.positions.length > 0) {
                    posContainer.innerHTML = currentData.positions.map(p => `
                        <div class="position-item">
                            <div><span class="pos-name">${p.symbol}</span><span style="font-size: 0.75rem; color: var(--text-dim)">$${p.entry}</span></div>
                            <div class="pos-pnl ${p.pnl >= 0 ? 'pnl-plus' : 'pnl-minus'}">${p.pnl >= 0 ? '+' : ''}${p.pnl.toFixed(2)}%</div>
                        </div>
                    `).join('');
                } else {
                    posContainer.innerHTML = '<p style="color: var(--text-dim); padding:1rem;">Waiting for entries...</p>';
                }
            } catch (error) { 
                console.error("Dashboard Sync Error:", error); 
            }
        }

        async function updateLogs() {
            try {
                const response = await fetch('/api/logs');
                const text = await response.text();
                const logDisplay = document.getElementById('log-display');
                
                // Ranglar bilan bezash (Raw \n ishlatiladi)
                const formatted = text.split('\n').map(line => {
                    if (line.includes('[DEBUG]')) return `<span class="log-line-debug">${line}</span>`;
                    if (line.includes('[INFO]')) return `<span class="log-line-info">${line}</span>`;
                    if (line.includes('[ERROR]')) return `<span class="log-line-error">${line}</span>`;
                    return line;
                }).join('\n');

                logDisplay.innerHTML = formatted;
                logDisplay.scrollTop = logDisplay.scrollHeight;
            } catch (error) { console.error("Log Sync Error:", error); }
        }

        setInterval(updateDashboard, 5000);
        setInterval(updateLogs, 4000);
        updateDashboard();
        updateLogs();
    </script>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════
#  🚀  FASTAPI SERVER
# ══════════════════════════════════════════════════════════════

api_app = FastAPI() if FastAPI else None

if api_app:
    @api_app.get("/", response_class=HTMLResponse)
    async def get_dashboard():
        return DASHBOARD_HTML

    @api_app.get("/api/data")
    async def get_data():
        signals_data = []
        for s in G_STATE.signals:
            signals_data.append({
                "id": str(id(s)),
                "chain": s.snapshot.chain.upper(),
                "symbol": s.snapshot.token_symbol,
                "name": s.snapshot.token_name,
                "type": s.signal_type,
                "confidence": s.confidence,
                "price": f"{s.snapshot.price_usd:.10f}",
                "age": f"{s.snapshot.age_hours:.1f}h",
                "addr": s.snapshot.pair_address,
                "token_addr": s.snapshot.token_address,
                "mcap": f"{s.snapshot.market_cap:,.0f}",
                "liq": f"{s.snapshot.liquidity:,.0f}",
                "sec": {
                    "is_hp": s.security.is_honeypot if s.security else False,
                    "has_mint": s.security.has_mint if s.security else False,
                    "top_pct": s.security.top_holder_pct if s.security else 0,
                    "btax": s.security.buy_tax if s.security else 0,
                    "stax": s.security.sell_tax if s.security else 0
                },
                "insider_report": s.insider_report if s.insider_report else {},
                "recommendation": getattr(s, 'recommendation', "WATCH ⚠️"),
                "rec_color": getattr(s, 'rec_color', "#fbbf24"),
                "confluence": s.confluence if s.confluence else []
            })
            
        positions_data = []
        for p in G_STATE.positions:
            # P&L hisoblash
            pnl = 0.0
            cur_p = getattr(p, 'current_price', 0)
            if cur_p > 0 and p.entry_price > 0:
                 pnl = (cur_p / p.entry_price - 1) * 100
            
            positions_data.append({
                "symbol": p.snap.token_symbol,
                "entry": f"{p.entry_price:.8f}",
                "pnl": pnl
            })
            
        return {
            "stats": G_STATE.stats,
            "signals": signals_data,
            "positions": positions_data,
            "last_update": G_STATE.last_update.strftime("%H:%M:%S")
        }

    @api_app.get("/api/logs")
    async def get_logs():
        """Oxirgi 100 qator logni qaytaradi."""
        try:
            log_file = "wtp_v4.log"
            if not os.path.exists(log_file):
                return Response(content="Log fayli hali yaratilmagan.", media_type="text/plain")
            
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                last_logs = "".join(lines[-100:])
                return Response(content=last_logs, media_type="text/plain")
        except Exception as e:
            return Response(content=f"Log o'qishda xatolik: {e}", media_type="text/plain")

def start_server():
    if api_app:
        log.info("🌐 Web Dashboard starting on http://localhost:8000")
        uvicorn.run(api_app, host="0.0.0.0", port=8000, log_level="error")

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
    has_socials:   bool = False
    timestamp:     datetime = field(default_factory=datetime.now)

    @property
    def is_organic_volume(self) -> bool:
        """Wash trading tekshiruvi: 24h Volume / Liquidity > 15x bo'lsa shubhali."""
        if self.liquidity < 5000: return True # Juda kam likvidlikda nisbat noto'g'ri bo'lishi mumkin
        return (self.volume_24h / self.liquidity) < 15.0

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
    security_passed:  bool  = False   
    insider_report:   dict  = field(default_factory=dict) # Insider tahlili natijasi
    recommendation:   str   = "WATCH"                    # Yangi: Aniq tavsiya (BUY/STAY OUT)
    rec_color:        str   = "#fbbf24"                  # Yangi: Tavsiya rangi

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


# ══════════════════════════════════════════════════════════════
#  📡  DEXSCREENER API
# ══════════════════════════════════════════════════════════════

class DexScreenerAPI:
    BASE = "https://api.dexscreener.com"
    # API so'rovlar orasidagi minimal vaqt (ms)
    _MIN_REQUEST_GAP_MS = 200

    def __init__(self, http: HttpClient):
        self.http = http
        self._last_call = 0.0

    async def _get(self, path: str, params: dict = None) -> Optional[Any]:
        """Rate limiting bilan so'rov yuborish."""
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
        """Boost qilingan (reklama) tokenlarni olish."""
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
    """DexScreener pair ma'lumotini MarketSnapshot ga o'girish."""
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
        
        # Socials va Website tekshiruvi
        info = pair.get("info") or {}
        has_soc = bool(info.get("socials") or info.get("websites"))

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
            has_socials=has_soc
        )
    except Exception as e:
        log.debug(f"parse_snap xatosi: {e}")
        return None


# ══════════════════════════════════════════════════════════════
#  🛡️  GOPLUS SECURITY SCANNER — Kuchaytirilgan
# ══════════════════════════════════════════════════════════════

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

        # Xavf bali
        score = 0
        if rep.is_honeypot:
            score += 60; rep.flags.append("☠️ HONEYPOT aniqlandi!")
        if rep.has_mint:
            score += 25; rep.flags.append("🖨️ Cheksiz token chiqarish (Mintable)")
        if rep.has_blacklist:
            score += 20; rep.flags.append("🚫 Blacklist funksiyasi mavjud")
        if rep.has_proxy:
            score += 15; rep.flags.append("🔄 Proxy contract (o'zgartirilishi mumkin)")
        if not rep.owner_renounced:
            score += 10; rep.flags.append("👤 Owner huquqini topshirmagan")
        if rep.sell_tax > MAX_SELL_TAX:
            score += 20; rep.flags.append(f"💸 Sotish solig'i {rep.sell_tax:.0f}% — yuqori!")
        if rep.buy_tax > MAX_BUY_TAX:
            score += 15; rep.flags.append(f"💸 Xarid solig'i {rep.buy_tax:.0f}% — yuqori!")
        if rep.top_holder_pct > MAX_TOP_HOLDER_PCT:
            score += 20; rep.flags.append(f"🐳 Top holder {rep.top_holder_pct:.0f}% ushlab turibdi")
        elif rep.top_holder_pct > 30:
            score += 10; rep.flags.append(f"⚠️ Top holder {rep.top_holder_pct:.0f}%")
        if 0 < rep.holder_count < MIN_HOLDER_COUNT:
            score += 15; rep.flags.append(f"👥 Faqat {rep.holder_count} ta holder — xavfli")

        rep.risk_score = min(100, score)
        return rep

    def passes_strict_filter(self, rep: SecurityReport, snap: "MarketSnapshot") -> tuple[bool, str]:
        """
        Qat'iy xavfsizlik filtri.
        Returns: (o'tdi, sabab)
        """
        if rep.is_honeypot:
            return False, "Honeypot aniqlandi"
        if rep.risk_score > MAX_SECURITY_RISK:
            return False, f"Xavf bali juda yuqori ({rep.risk_score}/100)"
        if rep.sell_tax > MAX_SELL_TAX:
            return False, f"Sotish solig'i {rep.sell_tax:.0f}% > {MAX_SELL_TAX:.0f}%"
        if rep.buy_tax > MAX_BUY_TAX:
            return False, f"Xarid solig'i {rep.buy_tax:.0f}% > {MAX_BUY_TAX:.0f}%"
        if rep.top_holder_pct > MAX_TOP_HOLDER_PCT:
            return False, f"Top holder {rep.top_holder_pct:.0f}% ulushi juda katta"
        if snap.age_hours < MIN_TOKEN_AGE_HOURS:
            return False, f"Token juda yosh ({snap.age_hours:.1f} soat)"
        return True, "OK"


# ══════════════════════════════════════════════════════════════
#  📈  COINGECKO TRENDING
# ══════════════════════════════════════════════════════════════

class CoinGeckoTrending:
    BASE = "https://api.coingecko.com/api/v3"

    def __init__(self, http: HttpClient):
        self.http = http
        self._trending_symbols: set = set()
        self._last_update = 0
        self.TTL = 600

    async def refresh(self):
        if time.time() - self._last_update < self.TTL:
            return
        data = await self.http.get(f"{self.BASE}/search/trending")
        if not data:
            return
        coins = data.get("coins") or []
        self._trending_symbols = {
            c.get("item", {}).get("symbol", "").upper() for c in coins
        }
        self._last_update = time.time()
        log.info(f"CoinGecko trending: {len(self._trending_symbols)} ta token")

    def is_trending(self, symbol: str) -> bool:
        return symbol.upper() in self._trending_symbols


# ══════════════════════════════════════════════════════════════
#  🧠  MORALIS WALLET INTELLIGENCE
# ══════════════════════════════════════════════════════════════

class MoralisClient:
    BASE_EVM = "https://deep-index.moralis.io/api/v2.2"

    def __init__(self, http: HttpClient):
        self.http = http
        self.key  = MORALIS_API_KEY
        self._cache: dict = {}
        self.enabled = bool(self.key)
        if not self.enabled:
            log.info("ℹ️  Moralis API kaliti yo'q — wallet tahlili o'chirilgan")

    async def _get(self, url: str, params: dict = None) -> Optional[Any]:
        if not self.enabled:
            return None
        headers = {"X-API-Key": self.key}
        sess = self.http._get_session()
        try:
            async with sess.get(url, params=params, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    return await r.json()
                elif r.status == 401:
                    log.error("Moralis API kaliti noto'g'ri!")
                    self.enabled = False
                    return None
                else:
                    return None
        except Exception as e:
            log.debug(f"Moralis xatosi: {e}")
            return None

    async def get_token_owners(self, chain: str, token_address: str) -> list:
        chain_map = {"ethereum":"eth","bsc":"bsc","polygon":"polygon",
                     "arbitrum":"arbitrum","base":"base"}
        m_chain = chain_map.get(chain)
        if not m_chain:
            return []
        data = await self._get(
            f"{self.BASE_EVM}/erc20/{token_address}/owners",
            params={"chain": m_chain, "limit": 15}
        )
        return (data or {}).get("result", [])

    async def analyze_wallet(self, chain: str, wallet: str) -> WalletExpertise:
        if wallet in self._cache:
            return self._cache[wallet]

        chain_map = {"ethereum":"eth","bsc":"bsc","polygon":"polygon",
                     "arbitrum":"arbitrum","base":"base"}
        m_chain = chain_map.get(chain)
        if not m_chain:
            return WalletExpertise(address=wallet)

        data = await self._get(
            f"{self.BASE_EVM}/wallets/{wallet}/history",
            params={"chain": m_chain, "limit": 50}
        )
        hist = (data or {}).get("result", [])
        total = len({tx.get("address") for tx in hist if tx.get("address")})
        hits  = min(total // 4, 12)
        rate  = (hits / total * 100) if total >= 5 else (hits * 10)

        perf = WalletExpertise(
            address=wallet, success_rate=round(rate, 1),
            alpha_hits=hits, total_trades=total,
            is_expert=(hits >= 3 and rate > 25)
        )
        self._cache[wallet] = perf
        return perf

    async def detect_smart_money(self, chain: str, token_address: str) -> list:
        if not self.enabled:
            return []
        owners  = await self.get_token_owners(chain, token_address)
        experts = []
        for owner in owners[:8]:
            addr = owner.get("owner_address")
            if addr:
                perf = await self.analyze_wallet(chain, addr)
                if perf.is_expert:
                    experts.append(perf)
            await asyncio.sleep(0.15)
        return experts


# ══════════════════════════════════════════════════════════════
#  🕸️  CROSS-DEX ARBITRAGE DETECTOR
# ══════════════════════════════════════════════════════════════

class ArbitrageDetector:
    def __init__(self):
        self._prices: dict = defaultdict(dict)

    def update(self, snap: MarketSnapshot):
        if snap.price_usd > 0:
            self._prices[snap.token_address][snap.dex] = snap.price_usd

    def check(self, snap: MarketSnapshot) -> tuple:
        prices = self._prices.get(snap.token_address, {})
        if len(prices) < 2:
            return False, 0.0
        vals = list(prices.values())
        mn, mx = min(vals), max(vals)
        if mn <= 0:
            return False, 0.0
        spread = (mx - mn) / mn * 100
        return spread > 2.0, round(spread, 2)


# ══════════════════════════════════════════════════════════════
#  💧  LIQUIDITY MONITOR
# ══════════════════════════════════════════════════════════════

class LiquidityMonitor:
    def __init__(self):
        self._history: dict = defaultdict(lambda: deque(maxlen=20))

    def update(self, snap: MarketSnapshot):
        self._history[snap.pair_address].append(snap.liquidity)

    def analyze(self, snap: MarketSnapshot) -> tuple:
        hist = list(self._history[snap.pair_address])
        if len(hist) < 2:
            return 0.0, []

        prev, curr = hist[-2], hist[-1]
        change = (curr - prev) / prev * 100 if prev > 0 else 0
        flags  = []

        if change > 8:
            flags.append(f"🐋 LP {change:+.1f}% qo'shildi — Kit kirdi")
            return 1.0, flags
        elif change < -8:
            flags.append(f"⚠️ LP {change:+.1f}% chiqarildi — Exit xavfi!")
            return -1.0, flags

        return change / 10, flags


# ══════════════════════════════════════════════════════════════
#  🌊  BOZOR REJIMI ANIQLOVCHI
# ══════════════════════════════════════════════════════════════

class RegimeDetector:
    def __init__(self):
        self._history: deque = deque(maxlen=200)
        self.current: str = "SIDEWAYS"

    def update(self, snaps: list):
        if not snaps:
            return
        sample = snaps[:80]
        avg1h  = sum(s.change_1h  for s in sample) / len(sample)
        avg24h = sum(s.change_24h for s in sample) / len(sample)
        vol    = sum(abs(s.change_1h) for s in sample) / len(sample)
        self._history.append(avg1h)

        if vol > 8:           self.current = "VOLATILE"
        elif avg1h > 2 and avg24h > 5:  self.current = "BULL"
        elif avg1h < -2 and avg24h < -5: self.current = "BEAR"
        else:                 self.current = "SIDEWAYS"

    @property
    def emoji(self) -> str:
        return {"BULL":"🟢","BEAR":"🔴","SIDEWAYS":"⬜","VOLATILE":"🟡"}.get(self.current,"⬜")

    @property
    def confidence_delta(self) -> int:
        return {"BULL": -3, "BEAR": +8, "VOLATILE": +10, "SIDEWAYS": 0}.get(self.current, 0)


# ══════════════════════════════════════════════════════════════
#  🔗  POSITION TRACKER
# ══════════════════════════════════════════════════════════════

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


class PositionTracker:
    def __init__(self, send_fn):
        self.send      = send_fn
        self.positions: dict = {}
        self.closed_pl: list = []  # P&L tarixi

    def open(self, sig: SignalResult):
        self.positions[sig.snapshot.pair_address] = OpenPosition(
            snap=sig.snapshot, signal_type=sig.signal_type,
            entry_price=sig.entry, target_1=sig.target_1,
            target_2=sig.target_2, stop_loss=sig.stop_loss,
            opened_at=datetime.now(), peak_price=sig.entry,
        )

    async def check_all(self, snaps: list, dex_api: 'DexScreenerAPI' = None):
        snap_map = {s.pair_address: s for s in snaps}
        to_close = []

        for addr, pos in self.positions.items():
            cur = snap_map.get(addr)
            if not cur:
                # Agar snap ichida bo'lmasa, API dan to'g'ridan-to'g'ri so'raymiz
                if dex_api:
                    try:
                        pair_data = await dex_api.get_pair(pos.snap.chain, addr)
                        if pair_data:
                            cur = parse_snap(pair_data)
                    except Exception as e:
                        log.debug(f"Position tracker API error ({addr}): {e}")

            if not cur:
                continue

            p   = cur.price_usd
            sym = pos.snap.token_symbol

            # Peak price yangilash (trailing stop logic uchun)
            if p > pos.peak_price:
                pos.peak_price = p

            pnl_pct = (p / pos.entry_price - 1) * 100

            # O'sish milestones (har 50% o'sishda xabar yuborish)
            current_milestone = math.floor(pnl_pct / 50) * 50
            if current_milestone > pos.last_milestone and current_milestone >= 50:
                pos.last_milestone = current_milestone
                await self.send(
                    f"📈 <b>{html.escape(sym)} — KUCHLI O'SISH!</b>\n"
                    f"Signal berilgandan beri: <b>+{pnl_pct:.1f}%</b> o'sdi! 🔥\n"
                    f"Kirish: <code>${pos.entry_price:.8f}</code> → Hozir: <code>${p:.8f}</code>\n"
                    f"🚀 Moonshot davom etmoqda!"
                )

            # Maqsad 1
            if not pos.t1_hit and p >= pos.target_1:
                pos.t1_hit = True
                await self.send(
                    f"🎯 <b>{html.escape(sym)} — MAQSAD 1 HIT!</b>\n"
                    f"Kirish: <code>${pos.entry_price:.8f}</code> → "
                    f"Hozir: <code>${p:.8f}</code> "
                    f"(<b>+{pnl_pct:.1f}%</b>)\n"
                    f"💡 50% foyda oling, qolganini ushlab turing!"
                )

            # Maqsad 2
            elif pos.t1_hit and not pos.t2_hit and p >= pos.target_2:
                pos.t2_hit = True
                self.closed_pl.append(pnl_pct)
                await self.send(
                    f"🚀 <b>{html.escape(sym)} — MAQSAD 2 HIT!</b>\n"
                    f"Kirish: <code>${pos.entry_price:.8f}</code> → "
                    f"Hozir: <code>${p:.8f}</code> "
                    f"(<b>+{pnl_pct:.1f}%</b>)\n"
                    f"✅ To'liq foyda oling!"
                )
                to_close.append(addr)

            # Stop-loss
            elif not pos.sl_hit and p <= pos.stop_loss:
                pos.sl_hit = True
                self.closed_pl.append(pnl_pct)
                await self.send(
                    f"🛑 <b>{html.escape(sym)} — STOP-LOSS!</b>\n"
                    f"Kirish: <code>${pos.entry_price:.8f}</code> → "
                    f"Hozir: <code>${p:.8f}</code> "
                    f"(<b>{pnl_pct:.1f}%</b>)\n"
                    f"❌ Pozitsiyani yoping. Bozor shundaydir."
                )
                to_close.append(addr)

            # 48 soat limit
            elif (datetime.now() - pos.opened_at).total_seconds() > 172800:
                self.closed_pl.append(pnl_pct)
                to_close.append(addr)

        for addr in to_close:
            self.positions.pop(addr, None)

    def avg_pl(self) -> Optional[float]:
        if not self.closed_pl:
            return None
        return round(sum(self.closed_pl) / len(self.closed_pl), 2)


# ══════════════════════════════════════════════════════════════
#  🧬  NEURAL SCORING ENGINE — 17 faktor
# ══════════════════════════════════════════════════════════════

class NeuralScorer:
    DEFAULT_WEIGHTS = {
        "buy_ratio_5m":       12.0,
        "buy_ratio_1h":       15.0,
        "buy_ratio_24h":      10.0,
        "volume_accel":        8.0,
        "price_momentum_5m":   7.0,
        "price_momentum_1h":   9.0,
        "liquidity_depth":     6.0,
        "liq_to_mcap":         5.0,
        "vol_to_liq":          6.0,   # Yangi: hajm/likvidlik nisbati
        "age_score":           6.0,
        "tx_count_quality":    5.0,
        "spread_quality":      4.0,
        "security_score":     10.0,   # v3: 8 → v4: 10 (muhimroq)
        "trending_bonus":      5.0,
        "arb_bonus":           3.0,
        "regime_alignment":    6.0,
        "expert_wallet_bonus": 8.0,
        "lp_momentum_bonus":   8.0,
    }

    def __init__(self):
        self.weights = dict(self.DEFAULT_WEIGHTS)

    @staticmethod
    def _sigmoid(x: float, center: float = 0, scale: float = 1) -> float:
        try:
            return 1 / (1 + math.exp(-scale * (x - center)))
        except OverflowError:
            return 1.0 if x > center else 0.0

    def _compute(self, snap: MarketSnapshot, sec: SecurityReport,
                 is_trending: bool, arb: bool, regime: str,
                 lp_score: float) -> dict:
        f = {}
        s = self._sigmoid

        f["buy_ratio_5m"]  = s(snap.buy_ratio_5m,  0.55, 8)
        f["buy_ratio_1h"]  = s(snap.buy_ratio_1h,  0.55, 8)
        f["buy_ratio_24h"] = s(snap.buy_ratio_24h, 0.55, 6)

        # Hajm tezlanishi
        accel = snap.volume_5m / (snap.volume_1h / 12 + 1) if snap.volume_1h > 0 else 0.5
        f["volume_accel"] = s(accel, 1.5, 2)

        f["price_momentum_5m"] = s(snap.change_5m, 2, 0.3)
        f["price_momentum_1h"] = s(snap.change_1h, 3, 0.2)

        f["liquidity_depth"] = s(math.log10(max(snap.liquidity, 1)), 5, 1.5)

        f["liq_to_mcap"] = s(snap.liquidity / snap.market_cap, 0.15, 10) \
                           if snap.market_cap > 0 else 0.4

        # Hajm/Likvidlik nisbati (yangi)
        f["vol_to_liq"] = s(snap.vol_to_liq_ratio, 0.5, 2)

        f["age_score"] = s(math.log10(max(snap.age_hours, 0.1)), 1.5, 2)

        total_tx = snap.total_txns_24h
        f["tx_count_quality"] = s(total_tx, 300, 0.008)

        if total_tx > 10:
            spread = abs(snap.buy_ratio_24h - 0.5)
            f["spread_quality"] = 1.0 - s(spread, 0.35, 10)
        else:
            f["spread_quality"] = 0.3

        # Security (xavfsizlik bali)
        f["security_score"] = 1.0 - sec.risk_score / 100 if sec.scanned else 0.5

        f["trending_bonus"] = 0.9 if is_trending else 0.3
        f["arb_bonus"]      = 0.8 if arb else 0.3

        # Expert hamyon bonus
        experts = getattr(sec, "expert_holders", [])
        f["expert_wallet_bonus"] = min(1.0, len(experts) * 0.2 + 0.3) if experts else 0.3

        f["lp_momentum_bonus"] = s(lp_score, 0.0, 4)

        # Rejim uyg'unligi
        bullish = snap.change_1h > 0 and snap.buy_ratio_1h > 0.5
        f["regime_alignment"] = {
            "BULL":     1.0 if bullish else 0.2,
            "BEAR":     0.7 if not bullish else 0.2,
            "SIDEWAYS": 0.5,
            "VOLATILE": 0.4,
        }.get(regime, 0.5)

        return f

    def score(self, snap: MarketSnapshot, sec: SecurityReport,
              is_trending: bool, arb: bool, regime: str,
              lp_score: float) -> tuple:
        factors   = self._compute(snap, sec, is_trending, arb, regime, lp_score)
        total_w   = sum(self.weights.values())
        weighted  = sum(factors[k] * self.weights[k] for k in factors if k in self.weights)
        raw       = weighted / total_w
        confidence = max(0, min(100, int(raw * 100)))
        return confidence, factors

    def adapt(self, factors: dict, win: bool):
        """Adaptive weight yangilash."""
        lr = 0.04
        for k, v in factors.items():
            if k not in self.weights or v < 0.3:
                continue
            if win and v > 0.65:
                self.weights[k] = min(30.0, self.weights[k] * (1 + lr * v))
            elif not win and v > 0.65:
                self.weights[k] = max(1.0, self.weights[k] * (1 - lr * 0.5))


# ══════════════════════════════════════════════════════════════
#  🧠  SMC ANALYZER
# ══════════════════════════════════════════════════════════════

class SMCAnalyzer:
    def __init__(self):
        self._hist: dict = defaultdict(lambda: deque(maxlen=30))

    def analyze(self, snap: MarketSnapshot) -> tuple:
        h = self._hist[snap.pair_address]
        h.append(snap.price_usd)
        if len(h) < 4:
            return None, 0

        p = list(h)
        p1, p2, p3, p4 = p[-4], p[-3], p[-2], p[-1]

        if p2 < p1 and p3 < p2 and p4 > p1:
            return "Break of Structure (Bullish BOS)", 15
        if p2 > p1 and p3 > p2 and p4 < p1:
            return "Change of Character (Bearish CHoCH)", -12
        if p4 > 0 and p1 > 0 and (p4-p1)/p1 > 0.08 and snap.change_1h > 5:
            return "Fair Value Gap (Bullish FVG)", 13
        if snap.change_5m < -4 and snap.change_1h > 3 and snap.buy_ratio_1h > 0.62:
            return "Liquidity Sweep + Recovery", 18
        if abs(snap.change_6h) < 2.5 and snap.volume_1h > snap.volume_6h / 3:
            return "Order Block (Accumulation Zone)", 10

        return None, 0


# ══════════════════════════════════════════════════════════════
#  📊  MULTI-TIMEFRAME CONFLUENCE
# ══════════════════════════════════════════════════════════════

class MTFConfluence:
    def analyze(self, snap: MarketSnapshot) -> tuple:
        tf = {}
        bonus = 0

        def add(name, bias, change, ratio=None):
            tf[name] = {"bias": bias, "change": change}
            if ratio is not None:
                tf[name]["buy_ratio"] = round(ratio * 100)

        r5 = snap.buy_ratio_5m
        add("5m", "bull" if r5>0.58 else "bear" if r5<0.42 else "neutral", snap.change_5m, r5)
        if r5 > 0.70: bonus += 10

        r1 = snap.buy_ratio_1h
        add("1h", "bull" if r1>0.58 else "bear" if r1<0.42 else "neutral", snap.change_1h, r1)
        if r1 > 0.67: bonus += 13

        b6 = "bull" if snap.change_6h > 3 else "bear" if snap.change_6h < -3 else "neutral"
        add("6h", b6, snap.change_6h)
        if snap.change_6h > 5: bonus += 10

        b24 = "bull" if snap.change_24h > 5 else "bear" if snap.change_24h < -5 else "neutral"
        add("24h", b24, snap.change_24h)
        if snap.change_24h > 12: bonus += 9

        biases = [v["bias"] for v in tf.values()]
        if biases.count("bull") == 4: bonus += 22
        elif biases.count("bull") == 3: bonus += 10
        elif biases.count("bear") == 4: bonus -= 18

        return tf, bonus


# ══════════════════════════════════════════════════════════════
#  ⏱️  TIMING PREDICTOR
# ══════════════════════════════════════════════════════════════

class TimingPredictor:
    def predict(self, snap: MarketSnapshot, target_pct: float) -> Optional[float]:
        if abs(snap.change_1h) < 0.2:
            return None
        rate = abs(snap.change_1h)
        return round(target_pct / rate * 1.4, 1)  # 40% susayish koeffitsienti


# ══════════════════════════════════════════════════════════════
#  📚  BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════

class BacktestEngine:
    def __init__(self, dex: DexScreenerAPI, neural: NeuralScorer):
        self.dex      = dex
        self.neural   = neural
        self._pending: dict = {}
        self._results: dict = defaultdict(list)
        self._factors: dict = {}

    def record(self, sig: SignalResult, factors: dict):
        self._pending[sig.snapshot.pair_address] = {
            "chain":  sig.snapshot.chain, "entry": sig.entry,
            "target": sig.target_1, "stop": sig.stop_loss,
            "signal": sig.signal_type, "time": datetime.now(),
        }
        self._factors[sig.snapshot.pair_address] = factors

    async def check(self, snaps: list):
        snap_map  = {s.pair_address: s for s in snaps}
        completed = []
        now       = datetime.now()

        for addr, entry in list(self._pending.items()):
            elapsed = (now - entry["time"]).total_seconds() / 3600
            if elapsed < 2:
                continue

            cur = snap_map.get(addr)
            if not cur:
                pair = await self.dex.get_pair(entry["chain"], addr)
                if pair:
                    cur = parse_snap(pair)

            if cur:
                win  = cur.price_usd >= entry["target"]
                loss = cur.price_usd <= entry["stop"]
                if win or loss or elapsed >= 24:
                    result = win if (win or loss) else (cur.price_usd > entry["entry"])
                    self._results[entry["signal"]].append(result)
                    completed.append(addr)
                    if addr in self._factors:
                        self.neural.adapt(self._factors[addr], result)
                    log.info(f"BT: {entry['signal']} → {'WIN ✅' if result else 'LOSS ❌'}")
            elif elapsed > 24:
                self._results[entry["signal"]].append(False)
                completed.append(addr)

        for addr in completed:
            self._pending.pop(addr, None)
            self._factors.pop(addr, None)

    def winrate(self, stype: str) -> Optional[float]:
        r = self._results.get(stype, [])
        return round(sum(r) / len(r) * 100, 1) if len(r) >= 3 else None

    def overall(self) -> Optional[float]:
        all_r = [x for v in self._results.values() for x in v]
        return round(sum(all_r) / len(all_r) * 100, 1) if len(all_r) >= 5 else None

    def summary(self) -> str:
        lines = []
        for st, results in self._results.items():
            if results:
                wr = sum(results) / len(results) * 100
                emoji = "✅" if wr >= 55 else "⚠️" if wr >= 40 else "❌"
                lines.append(
                    f"{emoji} <code>{html.escape(st)}</code>: "
                    f"<code>{wr:.0f}%</code> ({len(results)} signal)"
                )
        return "\n".join(lines) if lines else "<i>Hali ma'lumot yo'q (kamida 3 signal kerak)</i>"


# ══════════════════════════════════════════════════════════════
#  🚫  RUG DETECTOR — Kuchaytirilgan
# ══════════════════════════════════════════════════════════════

class RugDetector:
    STABLES = {"USDT","USDC","DAI","BUSD","TUSD","FRAX","LUSD","MIM", "USDD","USDP","USDE","PYUSD","FDUSD","CRVUSD","GHO"}

    def __init__(self):
        self._liq_hist: dict = defaultdict(lambda: deque(maxlen=8))

    def check(self, snap: MarketSnapshot, sec: SecurityReport) -> tuple:
        flags  = list(sec.flags)
        is_rug = sec.is_honeypot or sec.risk_score >= 55
        is_wash = False

        # Likvidlik tushishi monitoringi
        hist = self._liq_hist[snap.pair_address]
        if hist and hist[-1] > 0:
            drop = (hist[-1] - snap.liquidity) / hist[-1]
            if drop > 0.20:
                flags.append(f"💧 Likvidlik {drop*100:.0f}% kamaydi!")
                is_rug = True
        hist.append(snap.liquidity)

        # Juda yosh token
        if snap.age_hours < MIN_TOKEN_AGE_HOURS:
            flags.append(f"🕐 Token juda yosh ({snap.age_hours:.1f}s)")
            is_rug = True

        # Honeypot belgisi
        if snap.sells_24h == 0 and snap.buys_24h > 20:
            flags.append("🍯 Honeypot: 24s da 0 ta sotish!")
            is_rug = True

        # Wash trading
        total_tx = snap.total_txns_24h
        if total_tx > 0 and snap.volume_24h > 300_000:
            avg_size = snap.volume_24h / total_tx
            if avg_size > 50_000:
                if snap.volume_1h > 0 and snap.volume_5m / (snap.volume_1h / 12 + 1) > 5:
                    flags.append("🤖 Wash trading (sun'iy hajm)")
                    is_wash = True

        # Narx/Hajm nisbati anomaliyasi
        if snap.volume_24h > 0 and snap.market_cap > 0:
            if snap.volume_24h / snap.market_cap > 20:
                flags.append("⚠️ Hajm MCap dan 20x ko'p — anomaliya!")

        return is_rug, is_wash, flags


# ══════════════════════════════════════════════════════════════
#  🐋  SOLANA INSIDER SCANNER — Early Entry Analyzer
# ══════════════════════════════════════════════════════════════

class SolanaInsiderScanner:
    def __init__(self, http: HttpClient):
        self.http = http
        # Helius API Key bo'lsa, undan foydalanamiz, bo'lmasa zaxira RPC'lar
        self.RPCS = [
            f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}" if HELIUS_API_KEY else "https://api.mainnet-beta.solana.com",
            "https://solana-mainnet.rpc.extrnode.com",
            "https://rpc.ankr.com/solana"
        ]
        self._current_rpc_idx = 0
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self):
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def _rpc_call(self, method: str, params: list, retries: int = 3) -> Optional[dict]:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        sess = await self._get_session()
        
        for i in range(retries):
            rpc_url = self.RPCS[self._current_rpc_idx % len(self.RPCS)]
            try:
                async with sess.post(rpc_url, json=payload) as r:
                    if r.status == 200:
                        data = await r.json()
                        if "result" in data: return data
                    elif r.status in (429, 503, 504):
                        # Keyingi serverga o'tish
                        self._current_rpc_idx += 1
                        await asyncio.sleep(0.5 * (i + 1))
            except Exception as e:
                log.error(f"❌ RPC xatosi ({rpc_url}): {str(e)}", exc_info=True)
                self._current_rpc_idx += 1
                await asyncio.sleep(0.5)
        return None

    async def analyze(self, token_address: str, chain: str) -> dict:
        if chain.lower() != "solana": return {}

        log.info(f"🔍 Insider tahlili boshlandi: {token_address}")
        
        try:
            # 1. Total Supply ni aniqlash
            supply_res = await self._rpc_call("getTokenSupply", [token_address])
            if not supply_res or "result" not in supply_res:
                return {"status": "limit", "risk": "Scanning (Busy)...", "concentration": "0%", "snipers_found": 0, "reason": "RPC supply busy"}
            
            supply_data = supply_res["result"]["value"]
            total_supply = float(supply_data.get("uiAmount") or 1)

            # 2. Top Holders olish
            res = await self._rpc_call("getTokenLargestAccounts", [token_address])
            if not res or "result" not in res:
                return {"status": "limit", "risk": "Scanning (Queue)...", "concentration": "0%", "snipers_found": 0, "reason": "RPC holders busy"}

            holders = res["result"]["value"][:12]
            top_amount = sum(float(h.get("uiAmount", 0)) for h in holders)
            total_top_pct = (top_amount / total_supply) * 100 if total_supply > 0 else 0

            # 3. Sniper Detection (Free via Signatures)
            snipers_count = 0
            launch_signatures = await self._rpc_call("getSignaturesForAddress", [token_address, {"limit": 20}])
            
            if launch_signatures and "result" in launch_signatures:
                sigs = launch_signatures["result"]
                if len(sigs) > 1:
                    launch_time = sigs[-1].get("blockTime")
                    if launch_time:
                        snipers_count = sum(1 for s in sigs if (s.get("blockTime", 0) - launch_time) < 120)
            else:
                log.warning(f"⚠️ Signaturalarni olib bo'lmadi: {token_address}")

            # Risk Scoreni aniqlash
            risk_level = "LOW"
            if total_top_pct > 45 or snipers_count > 8: 
                risk_level = "⚠️ VERY HIGH (Sniper/Insider Risk)"
            elif total_top_pct > 30 or snipers_count > 4: 
                risk_level = "MEDIUM"

            log.info(f"✅ Insider tahlili yakunlandi: {token_address} | Snipers: {snipers_count}")

            return {
                "status": "ready",
                "risk": risk_level,
                "concentration": f"{total_top_pct:.1f}%",
                "top_holders_count": len(holders),
                "snipers_found": snipers_count,
                "early_whale_check": "Sniper Analysis Complete" if snipers_count > 0 else "Analyzing..."
            }

        except Exception as e:
            log.error(f"❌ Insider tahlilida kutilmagan xato: {str(e)}", exc_info=True)
            return {"status": "error", "risk": "ERROR", "concentration": "0%", "reason": str(e)}


# ══════════════════════════════════════════════════════════════
#  ⚙️  SIGNAL ENGINE — Kuchaytirilgan filtrlar
# ══════════════════════════════════════════════════════════════

class SignalEngine:
    def __init__(self, dex, goplus, moralis, trending, neural, backtest):
        self.dex      = dex
        self.goplus   = goplus
        self.moralis  = moralis
        self.trending = trending
        self.neural   = neural
        self.backtest = backtest
        self.rug      = RugDetector()
        self.smc      = SMCAnalyzer()
        self.mtf      = MTFConfluence()
        self.arb      = ArbitrageDetector()
        self.lp       = LiquidityMonitor()
        self.regime   = RegimeDetector()
        self.timing   = TimingPredictor()
        self.insider  = SolanaInsiderScanner(HttpClient()) # Yangi

        self._seen:      dict = {}
        self._hour_count = 0
        self._hour_reset = datetime.now()

    def _rate_ok(self, addr: str) -> bool:
        now = datetime.now()
        if (now - self._hour_reset).total_seconds() >= 3600:
            self._hour_count = 0
            self._hour_reset = now
        if self._hour_count >= MAX_SIGNALS_PER_HR:
            return False
        if addr in self._seen:
            return (now - self._seen[addr]) > timedelta(minutes=COOLDOWN_MINUTES)
        return True

    async def analyze(self, snap: MarketSnapshot) -> Optional[SignalResult]:
        # LP monitoring
        self.lp.update(snap)
        lp_score, lp_flags = self.lp.analyze(snap)

        # 1. Stable coin filtri
        if snap.token_symbol.upper() in RugDetector.STABLES:
            return None

        # 2. YANGI TOKEN FILTRI: Faqat 0.25-6 soatlik tokenlar
        if snap.age_hours <= 0 or snap.age_hours > NEW_TOKEN_MAX_HOURS:
            return None
        if snap.age_hours < NEW_TOKEN_MIN_HOURS:
            return None  # 15 daqiqadan kichik — juda xavfli

        # 3. Asosiy likvidlik/hajm filtri
        is_moonshot = (
            MOONSHOT_MIN_MCAP < snap.market_cap < MOONSHOT_MAX_MCAP and
            snap.buy_ratio_5m > MOONSHOT_MIN_BUY_RATIO and
            snap.volume_5m > MOONSHOT_MIN_VOL_5M and
            snap.age_hours >= MOONSHOT_MIN_AGE_HOURS
        )

        # EXPERT FILTR 1: Social Proof (Website yoki Socials majburiy)
        if not snap.has_socials:
            log.debug(f"Expert filter: {snap.token_symbol} — Social links yo'q. Skip.")
            return None

        # EXPERT FILTR 2: Organic Volume (Wash tradingga qarshi)
        if not snap.is_organic_volume:
            log.debug(f"Expert filter: {snap.token_symbol} — Wash trading shubha. Skip.")
            return None

        # Yosh tokenlar uchun dinamik minimal hajm
        vol_factor = min(1.0, max(0.2, snap.age_hours))
        dynamic_vol_1h = MIN_VOLUME_1H * vol_factor

        liq_min = MIN_LIQUIDITY * 0.5 if is_moonshot else MIN_LIQUIDITY
        vol_ok = snap.volume_1h >= dynamic_vol_1h or snap.volume_24h >= MIN_VOLUME_24H

        if snap.liquidity < liq_min or not vol_ok:
            return None

        # EXPERT FILTR 3: Bozor Rejimiga moslashuvchan Threshold
        current_regime = self.regime.current
        effective_min_conf = MIN_CONFIDENCE
        if current_regime == "BEAR":
            effective_min_conf += 8  # Ayiq bozorida talab qattiqroq
        elif current_regime == "VOLATILE":
            effective_min_conf += 5
        
        if snap.price_usd <= 0 or not self._rate_ok(snap.pair_address):
            return None

        # 4. GoPlus xavfsizlik skaneri (MAJBURIY)
        sec = await self.goplus.scan(snap.chain, snap.token_address)
        sec.expert_holders = []

        # 5. Qat'iy xavfsizlik filtri
        passed, reason = self.goplus.passes_strict_filter(sec, snap)
        if not passed:
            log.debug(f"Security filter: {snap.token_symbol} — {reason}")
            return None

        # 6. Signal turi
        signal_type = self._classify(snap)
        if not signal_type:
            return None

        # 7. Insider tahlili (Faqat Solana uchun)
        insider_data = {}
        if snap.chain.lower() == "solana":
            insider_data = await self.insider.analyze(snap.token_address, snap.chain)

        # 8. Moralis expert tahlili (faqat yaxshi signallarda)
        if "BUY" in signal_type and snap.liquidity > MIN_LIQUIDITY and MORALIS_API_KEY:
            sec.expert_holders = await self.moralis.detect_smart_money(snap.chain, snap.token_address)

        # 8. Rug tekshiruvi
        is_rug, is_wash, risk_flags = self.rug.check(snap, sec)
        risk_flags.extend(lp_flags)

        # 9. Cross-DEX arbitraj
        self.arb.update(snap)
        arb_detected, arb_spread = self.arb.check(snap)
        is_trending = self.trending.is_trending(snap.token_symbol)

        # Rug alert
        if is_rug:
            self._seen[snap.pair_address] = datetime.now()
            self._hour_count += 1
            return SignalResult(
                snapshot=snap, signal_type="RUG_ALERT",
                confidence=90, primary_reason="Rug pull / Honeypot belgilari!",
                confluence=[], risk_flags=risk_flags, security=sec,
                smc_pattern=None, regime=self.regime.current,
                timeframe_align={}, neural_scores={},
                backtest_winrate=None, risk_reward=0,
                entry=snap.price_usd, target_1=0, target_2=0,
                stop_loss=snap.price_usd * 0.5,
                is_trending=is_trending, is_boosted=False,
                arb_detected=arb_detected, security_passed=False,
            )

        # 10. Neural scoring
        confidence, factors = self.neural.score(
            snap, sec, is_trending, arb_detected, self.regime.current, lp_score
        )

        # Bonuslar
        if is_moonshot:
            confidence += 12
            if is_trending: confidence += 8
        if len(sec.expert_holders) >= 2:
            confidence += 10
        if len(sec.expert_holders) >= 4:
            confidence += 5

        smc_pattern, smc_bonus = self.smc.analyze(snap)
        confidence += smc_bonus

        tf_data, mtf_bonus = self.mtf.analyze(snap)
        confidence += mtf_bonus // 3

        confidence += self.regime.confidence_delta

        if is_wash:
            confidence -= 22

        # Backtest korreksiyasi
        wr = self.backtest.winrate(signal_type)
        if wr is not None:
            if wr >= 70:   confidence += 8
            elif wr >= 55: confidence += 4
            elif wr < 40:  confidence -= 15

        confidence = max(0, min(100, confidence))

        # Minimal confidence tekshiruvi (EXPERT FILTR 3 qo'llash)
        if confidence < effective_min_conf:
            return None

        # 11. Maqsadlar va R:R tekshiruvi
        entry, t1, t2, sl = self._targets(snap, signal_type)
        rr = abs(t1 - entry) / max(abs(entry - sl), 1e-10)

        # Minimal R:R filtri (yangi)
        if rr < MIN_RR_RATIO and signal_type not in ("MOONSHOT_ALPHA", "RUG_ALERT"):
            return None

        est_hours = self.timing.predict(snap, TARGET_1_PCT)
        primary   = self._build_reason(snap, signal_type)

        # Confluence
        confluence = []
        if smc_pattern: confluence.append(f"SMC: {smc_pattern}")
        if is_trending:  confluence.append("CoinGecko Trending ro'yxatida! 🔥")
        if arb_detected: confluence.append(f"Cross-DEX arbitraj: {arb_spread:.1f}% spread")
        if snap.age_hours > 720: confluence.append("1 oy+ barqaror token ✅")
        if sec.risk_score < 10 and sec.scanned:
            confluence.append("GoPlus: Xavfsiz contract ✅")
        tf_bull = sum(1 for v in tf_data.values() if v.get("bias") == "bull")
        if tf_bull >= 3:
            confluence.append(f"Multi-TF: {tf_bull}/4 bullish ✅")
        if snap.vol_to_liq_ratio > 1.0:
            confluence.append(f"Yuqori hajm/likvidlik: {snap.vol_to_liq_ratio:.1f}x")

        # 12. Rekommendatsiya (O'TA QAT'IY FILTRLAR — ANTI-FAKE)
        # ──────────────────────────────────────────────────────────
        rec = "WATCH ⚠️"
        color = "#fbbf24" # Sariq (Default)
        
        # Insider / Concentration ko'rsatkichlari (Ultra qat'iy)
        top_h = (sec.top_holder_pct if sec else 0)
        sol_h = insider_data.get("concentration", "0%").replace("%","")
        try: sol_h_val = float(sol_h)
        except: sol_h_val = 0
        
        is_insider = (top_h > 18 or sol_h_val > 18 or insider_data.get("risk", "").startswith("⚠️ VERY HIGH"))
        snipers_found = insider_data.get("snipers_found", 0)

        # BUY NOW (Sotib ol) - Faqat Ideal shartlar!
        if confidence >= 85 and not is_insider and (sec and not sec.is_honeypot):
            if snipers_found <= 2:
                rec = "BUY NOW 🔥✅"
                color = "#10b981" # Yashil

        # STAY OUT (Kirmang/Xavf) - Xatarli yoki Soxta koinlar
        elif confidence < 65 or (sec and sec.is_honeypot) or is_insider or is_wash:
            rec = "STAY OUT 🚫❌"
            color = "#ef4444" # Qizil
            reasons = []
            if sec and sec.is_honeypot: reasons.append("⚠️ HONEYPOT! (Sotish imkoniyat yo'q)")
            if is_insider:            reasons.append(f"🐋 INSIDER/WHALE XAVFI! (Top hamyonlar: {sol_h_val}%)")
            if is_wash:               reasons.append("🚫 WASH TRADING (Sun'iy hajm aniqlandi)")
            if confidence < 60:       reasons.append(f"📉 ISHONCH JUDA PAST ({confidence}%)")
            primary = " | ".join(reasons) if reasons else "⚠️ XATARLI KOIN (Ehtiyot bo'ling!)"

        # MOONSHOT (Katta risk/Katta foyda - Faqat yangi koinlar)
        elif signal_type == "MOONSHOT_ALPHA" and confidence >= 72 and not is_insider:
            rec = "MOONSHOT 🚀💎"
            color = "#a855f7" # Binafsha

        result = SignalResult(
            snapshot=snap, signal_type=signal_type,
            confidence=confidence, primary_reason=primary,
            confluence=confluence, risk_flags=risk_flags, security=sec,
            smc_pattern=smc_pattern, regime=self.regime.current,
            timeframe_align=tf_data, neural_scores=factors,
            backtest_winrate=wr, risk_reward=round(rr, 2),
            entry=entry, target_1=t1, target_2=t2, stop_loss=sl,
            is_trending=is_trending, is_boosted=False,
            arb_detected=arb_detected, estimated_hours=est_hours,
            security_passed=True,
            insider_report=insider_data,
            recommendation=rec, rec_color=color
        )
        if snap.chain.lower() == "solana":
            log.info(f"📊 Solana Insider Data for {snap.token_symbol}: {insider_data}")

        self._seen[snap.pair_address] = datetime.now()
        self._hour_count += 1
        self.backtest.record(result, factors)
        
        # Dashboardni yangilash
        G_STATE.add_signal(result)
        
        return result

    def _classify(self, snap: MarketSnapshot) -> Optional[str]:
        """
        Faqat 4 ta signal turi: MOONSHOT_ALPHA, STRONG_BUY, BREAKOUT, RUG_ALERT
        Yangi tokenlar (0-6 soat) uchun moslantirilgan shartlar.
        """
        r5  = snap.buy_ratio_5m
        r1h = snap.buy_ratio_1h

        # RUG_ALERT — rug detect() dan keladi, bu yerda faqat tekshiriladi
        # (rug_detect() chaqiruvi analyze() da alohida amalga oshiriladi)

        # MOONSHOT_ALPHA — past kapital, yuqori xarid bosimi
        if (MOONSHOT_MIN_MCAP < snap.market_cap < MOONSHOT_MAX_MCAP and
                r5 > MOONSHOT_MIN_BUY_RATIO and
                snap.volume_5m > MOONSHOT_MIN_VOL_5M):
            return "MOONSHOT_ALPHA"

        # STRONG_BUY — kuchli xarid bosimi (yangi token uchun biroz yumshoqroq)
        if r5 > 0.72 and r1h > 0.65 and snap.change_5m > 1.5 and snap.volume_5m > 500:
            return "STRONG_BUY"

        # BREAKOUT — yangi tokenda tez ko'tarilish
        if snap.change_1h > 10 and snap.change_5m > 3 and r5 > 0.58:
            return "BREAKOUT"

        # Ruxsat berilmagan signallar (BUY, ACCUMULATION, DISTRIBUTION, DUMP_RISK) — o'tkazilmaydi
        return None

    def _targets(self, snap: MarketSnapshot, st: str) -> tuple:
        p = snap.price_usd
        if st == "MOONSHOT_ALPHA":
            # Yangi past kapital tokenlar uchun katta maqsad
            return p, p * 1.80, p * 4.0, p * 0.85
        if st in ("STRONG_BUY", "BREAKOUT"):
            return (p,
                    p * (1 + TARGET_1_PCT / 100),
                    p * (1 + TARGET_2_PCT / 100),
                    p * (1 - STOP_LOSS_PCT / 100))
        # RUG_ALERT uchun (pozitsiya ochilmaydi)
        return p, 0, 0, p * 0.5

    def _build_reason(self, snap: MarketSnapshot, st: str) -> str:
        age_str = f"{snap.age_hours*60:.0f} daqiqa" if snap.age_hours < 1 else f"{snap.age_hours:.1f} soat"
        reasons = {
            "MOONSHOT_ALPHA": (
                f"🆕 YANGI GEM ({age_str}): MCap ${snap.market_cap:,.0f}, "
                f"xarid {snap.buy_ratio_5m:.0%}, 5m hajm ${snap.volume_5m:,.0f}"
            ),
            "STRONG_BUY": (
                f"🆕 Yangi token ({age_str}): kuchli xarid "
                f"5m {snap.buy_ratio_5m:.0%} | 1h {snap.buy_ratio_1h:.0%}, "
                f"narx {snap.change_5m:+.1f}%"
            ),
            "BREAKOUT": (
                f"🆕 Yangi token ({age_str}): BREAKOUT "
                f"1h {snap.change_1h:+.1f}%, 5m {snap.change_5m:+.1f}%"
            ),
        }
        return reasons.get(st, f"Yangi token signal ({age_str})")


# ══════════════════════════════════════════════════════════════
#  💬  TELEGRAM XABAR FORMATI — Yangilangan
# ══════════════════════════════════════════════════════════════

def fmt(sig: SignalResult) -> str:
    s = sig.snapshot
    url = f"https://dexscreener.com/{s.chain}/{s.pair_address}"
    p = s.price_usd

    # Timeframe qatori
    tf_parts = []
    for name, d in sig.timeframe_align.items():
        em = "🟢" if d["bias"]=="bull" else "🔴" if d["bias"]=="bear" else "⬜"
        tf_parts.append(f"{em}<code>{name}:{d['change']:+.1f}%</code>")
    tf_str = "  ".join(tf_parts)

    # Confluence
    cf = "".join(f"  ✅ {html.escape(f)}\n" for f in sig.confluence[:5])

    # Xavf belgilari
    rf = "".join(f"  ⚠️ {html.escape(r)}\n" for r in sig.risk_flags[:4])

    # Backtest
    bt_wr = f"<code>{sig.backtest_winrate:.0f}%</code>" if sig.backtest_winrate else "<code>—</code>"

    # Security
    sec = sig.security
    sec_str = ""
    if sec and sec.scanned:
        sc = ("🟢 Xavfsiz" if sec.risk_score < 20 else
              "🟡 Ehtiyotkor" if sec.risk_score < 40 else "🔴 Xavfli")
        sec_str = (
            f"\n🛡️ <b>GoPlus Security:</b> {sc} (xavf: {sec.risk_score}/100)\n"
            f"  Holderlar: <code>{sec.holder_count:,}</code> | "
            f"Top: <code>{sec.top_holder_pct:.1f}%</code> | "
            f"Tax: <code>{sec.buy_tax:.0f}%/{sec.sell_tax:.0f}%</code>"
        )
        if getattr(sec, "expert_holders", []):
            sec_str += (
                f"\n🧠 <b>Smart Money:</b> {len(sec.expert_holders)} expert hamyon"
            )

    # Vaqt
    time_str = f"\n⏱️ Taxminiy vaqt: <code>~{sig.estimated_hours:.1f} soat</code>" \
               if sig.estimated_hours else ""

    extras = ""
    if sig.is_trending: extras += " 🔥Trending"
    if sig.arb_detected: extras += " ⚡Arb"

    # RUG ALERT
    if sig.signal_type == "RUG_ALERT":
        return (
            f"☠️ <b>RUG / HONEYPOT XAVFI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 <b>{html.escape(s.token_symbol)}</b> | "
            f"<code>{s.chain.upper()}</code>\n"
            f"💵 <code>${p:.8f}</code>\n"
            f"{sec_str}\n"
            f"⚠️ <b>Xavf belgilari:</b>\n{rf}"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href='{url}'>DexScreener</a>\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')} | WTP v4.0"
        )

    # STAY OUT (Kirmang) uchun maxsus shablon
    if "STAY OUT" in sig.recommendation:
        return (
            f"⚠️ <b>DIQQAT: {sig.recommendation}</b>\n\n"
            f"❌ <b>XAVF ANIQLANDI — {html.escape(s.token_symbol)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🚩 <b>SABAB: {html.escape(sig.primary_reason)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 <code>{html.escape(s.token_name)}</code> | "
            f"<code>{s.chain.upper()}</code>\n"
            f"💵 <code>${p:.10f}</code>\n"
            f"💧 Liq: <code>${s.liquidity:,.0f}</code> | "
            f"Hajm: <code>${s.volume_24h:,.0f}</code>\n"
            f"📊 MCap: <code>${s.market_cap:,.0f}</code>\n"
            f"{sec_str}\n"
            f"\n🚫 <b>BU KOINGA KIRISH TAVSIYA ETILMAYDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href='{url}'>DexScreener</a>\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')} | WTP v4.5"
        )

    h_emoji = "🚀🌕" if sig.signal_type == "MOONSHOT_ALPHA" else ""
    return (
        f"<b>🚀 TAVSIYA: {sig.recommendation}</b>\n\n"
        f"{sig.emoji} <b>{h_emoji}{sig.signal_type.replace('_',' ')} — "
        f"{html.escape(s.token_symbol)}</b>{extras}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 <code>{html.escape(s.token_name)}</code> | "
        f"<code>{s.chain.upper()}</code> | <code>{s.dex}</code>\n"
        f"💵 <code>${p:.10f}</code>\n"
        f"💧 Liq: <code>${s.liquidity:,.0f}</code> | "
        f"Hajm: <code>${s.volume_24h:,.0f}</code>\n"
        f"📊 MCap: <code>${s.market_cap:,.0f}</code> | "
        f"Yosh: <code>{s.age_hours:.0f}s</code> | "
        f"Hajm/Liq: <code>{s.vol_to_liq_ratio:.1f}x</code>\n"
        f"\n📈 <b>TF tahlili:</b> {tf_str}\n"
        f"🌊 Rejim: <code>{sig.regime}</code> {sig.emoji if sig.regime=='BULL' else ''}\n"
        f"\n🎯 <b>Signal kuchi:</b> <code>{sig.bar}</code> <b>{sig.confidence}/100</b>\n"
        f"📌 <i>{html.escape(sig.primary_reason)}</i>\n"
        f"{f'✅ <b>Confluence:</b>{chr(10)}{cf}' if cf else ''}"
        f"{sec_str}\n"
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 <b>Savdo rejasi:</b>\n"
        f"  🟡 Kirish:    <code>${sig.entry:.10f}</code>\n"
        f"  🎯 Maqsad 1: <code>${sig.target_1:.10f}</code> (+{TARGET_1_PCT:.0f}%)\n"
        f"  🚀 Maqsad 2: <code>${sig.target_2:.10f}</code> (+{TARGET_2_PCT:.0f}%)\n"
        f"  🛑 Stop:      <code>${sig.stop_loss:.10f}</code> (-{STOP_LOSS_PCT:.0f}%)\n"
        f"  ⚖️ R:R: <code>{sig.risk_reward:.2f}:1</code>{time_str}\n"
        f"\n📚 Tarixiy to'g'rilik: {bt_wr}\n"
        f"{f'⚠️ <b>Xavf:</b>{chr(10)}{rf}' if rf else ''}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <a href='{url}'>DexScreener</a>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')} | WTP v4.5"
    )


# ══════════════════════════════════════════════════════════════
#  🤖  ASOSIY BOT
# ══════════════════════════════════════════════════════════════

class WhaleTrackerV4:
    def __init__(self):
        self.http     = HttpClient()
        self.dex      = DexScreenerAPI(self.http)
        self.goplus   = GoPlusScanner(self.http)
        self.moralis  = MoralisClient(self.http)
        self.trending = CoinGeckoTrending(self.http)
        self.neural   = NeuralScorer()
        self.backtest = BacktestEngine(self.dex, self.neural)
        self.engine   = SignalEngine(
            self.dex, self.goplus, self.moralis, self.trending,
            self.neural, self.backtest
        )
        self.tracker  = None
        self.bot      = Bot(token=TELEGRAM_BOT_TOKEN)
        self._snaps:  list = []

        self.total_scans   = 0
        self.total_signals = 0
        self.rug_alerts    = 0
        self.filtered_out  = 0   # Yangi: filtrda qolgan tokenlar
        self.start_time    = datetime.now()
        self.paused        = False

    async def send(self, text: str, markup=None):
        try:
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=markup,
            )
        except Exception as e:
            log.error(f"Telegram xatosi: {e}")

    def _kb(self):
        pause_lbl = "▶️ Resume" if self.paused else "⏸ Pause"
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Status",      callback_data="status"),
             InlineKeyboardButton("📈 Top 5",       callback_data="top5")],
            [InlineKeyboardButton(pause_lbl,        callback_data="pause"),
             InlineKeyboardButton("📚 Winrate",     callback_data="winrate")],
            [InlineKeyboardButton("🧬 Weights",     callback_data="weights"),
             InlineKeyboardButton("🌊 Rejim",       callback_data="regime")],
            [InlineKeyboardButton("🔍 Hozir skan",  callback_data="scan_now"),
             InlineKeyboardButton("💼 Pozitsiyalar", callback_data="positions")],
        ])

    async def startup(self):
        moralis_status = "✅ Faol" if MORALIS_API_KEY else "⬜ O'chirilgan"
        chains = ", ".join(c.upper() for c in WATCH_CHAINS)
        await self.send(
            f"🐋 <b>Whale Tracker Pro v4.5 — NEW TOKENS ONLY</b>\n\n"
            f"⏰ <b>Kuzatiladigan yosh:</b> <code>{NEW_TOKEN_MIN_HOURS*60:.0f} daqiqa → {NEW_TOKEN_MAX_HOURS:.0f} soat</code>\n"
            f"📢 <b>Signallar:</b> <code>MOONSHOT | STRONG_BUY | BREAKOUT | RUG_ALERT</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ GoPlus Scanner: Majburiy ✅\n"
            f"🧬 Neural Scoring: 18 faktor ✅\n"
            f"🧠 Moralis Wallet: {moralis_status}\n"
            f"📈 CoinGecko Trending ✅\n"
            f"⚡ Cross-DEX Arbitraj ✅\n"
            f"📊 Position Tracker ✅\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ Min confidence: <code>{MIN_CONFIDENCE}/100</code>\n"
            f"💧 Min likvidlik: <code>${MIN_LIQUIDITY:,}</code>\n"
            f"📦 Min hajm (1h): <code>${MIN_VOLUME_1H:,}</code>\n"
            f"⚖️ Min R:R: <code>{MIN_RR_RATIO}:1</code>\n"
            f"🔒 Max xavf bali: <code>{MAX_SECURITY_RISK}/100</code>\n"
            f"📡 Zanjirlar: <code>{chains}</code>\n"
            f"⏱ Skan intervali: <code>{SCAN_INTERVAL_SEC}s</code>",
            markup=self._kb()
        )

    async def scan(self):
        if self.paused:
            return
        self.total_scans += 1
        
        # Backtest natijalarini olish
        wins, losses = 0, 0
        if hasattr(self, 'backtest'):
            for results in self.backtest._results.values():
                wins += sum(1 for r in results if r is True)
                losses += sum(1 for r in results if r is False)

        # Dashboard stats yangilash
        G_STATE.update_stats(
            total_scans=self.total_scans,
            wins=wins,
            losses=losses,
            regime=self.engine.regime.current,
            regime_emoji=self.engine.regime.emoji,
            active_positions_count=len(self.tracker.positions) if self.tracker else 0
        )
        if self.tracker:
            G_STATE.set_positions(list(self.tracker.positions.values()))

        log.info(f"{'─'*55}")
        log.info(f"🔍 SKAN #{self.total_scans} | Rejim: {self.engine.regime.current}")

        await self.trending.refresh()

        raw: list = []
        sem = asyncio.Semaphore(4)  # v3: 5 → v4: 4 (API cheklovlari uchun)

        async def safe_get_pairs(ta):
            async with sem:
                try:
                    pairs = await self.dex.get_token_pairs(ta)
                    return [p for p in pairs if p.get("chainId") in WATCH_CHAINS][:3]
                except Exception as e:
                    log.debug(f"get_token_pairs xatosi: {e}")
                    return []

        async def safe_search(q, limit=12):
            async with sem:
                try:
                    return (await self.dex.search(q))[:limit]
                except Exception as e:
                    log.debug(f"search xatosi: {e}")
                    return []

        # 1. So'nggi profillar va Boosted tokenlar
        discovery_tasks = [
            self.dex.get_latest_profiles(),
            self.dex.get_boosted_tokens()
        ]
        discovery_results = await asyncio.gather(*discovery_tasks)

        profiles = discovery_results[0] or []
        boosts   = discovery_results[1] or []

        all_token_addresses = set()
        for pr in profiles[:25]:
            if pr.get("tokenAddress"): all_token_addresses.add(pr["tokenAddress"])
        for b in boosts[:25]:
            if b.get("tokenAddress"): all_token_addresses.add(b["tokenAddress"])

        if all_token_addresses:
            tasks   = [safe_get_pairs(ta) for ta in list(all_token_addresses)]
            results = await asyncio.gather(*tasks)
            for r in results: raw.extend(r)

        # 2. Har bir chain qidirish
        search_queries = (
            [f"{ch} trending" for ch in WATCH_CHAINS] +
            [f"{ch} new tokens" for ch in WATCH_CHAINS[:3]]
        )
        search_tasks   = [safe_search(q) for q in search_queries]
        search_results = await asyncio.gather(*search_tasks)
        for r in search_results: raw.extend(r)

        # 3. CoinGecko trending tokenlar
        if self.trending._trending_symbols:
            cg_tasks = [safe_search(sym, 4)
                        for sym in list(self.trending._trending_symbols)[:8]]
            cg_res   = await asyncio.gather(*cg_tasks)
            for r in cg_res: raw.extend(r)

        # Deduplikatsiya va parsing
        snaps: list = []
        seen  = set()
        for p in raw:
            addr = p.get("pairAddress", "")
            if addr and addr not in seen:
                seen.add(addr)
                s = parse_snap(p)
                if s:
                    snaps.append(s)

        log.info(f"Snapshots: {len(snaps)} ta")
        self._snaps = snaps
        self.engine.regime.update(snaps)

        await self.backtest.check(snaps)
        await self.tracker.check_all(snaps, dex_api=self.dex)

        # Parallel analiz
        analyzed = 0
        filtered = 0

        async def safe_analyze(snap):
            async with sem:
                try:
                    return await self.engine.analyze(snap)
                except Exception as e:
                    log.error(f"Analyze xatosi ({snap.token_symbol}): {e}")
                    return None

        tasks   = [safe_analyze(s) for s in snaps[:80]]
        results = await asyncio.gather(*tasks)
        signals = []

        for res in results:
            if res is not None:
                signals.append(res)
                analyzed += 1
            else:
                filtered += 1

        self.filtered_out += filtered

        # Signal yuborish (eng yuqori confidence birinchi)
        signals.sort(key=lambda x: x.confidence, reverse=True)

        for sig in signals:
            self.total_signals += 1
            if sig.signal_type == "RUG_ALERT":
                self.rug_alerts += 1
            elif sig.security_passed:
                self.tracker.open(sig)

            # FAQAT 'BUY NOW' yoki 'MOONSHOT' signallarni Telegram'ga yuboramiz. 
            # 'WATCH' va 'STAY OUT' larni Telegram'dan filtrlaymiz (Shovqinni kamaytirish uchun).
            if "BUY NOW" in sig.recommendation or "MOONSHOT" in sig.recommendation:
                await self.send(fmt(sig))
            log.info(
                f"{Fore.GREEN if 'BUY' in sig.signal_type or 'MOON' in sig.signal_type else Fore.RED}"
                f"{'✅' if sig.security_passed else '☠️'} {sig.emoji} "
                f"{sig.snapshot.token_symbol} [{sig.signal_type}] "
                f"{sig.confidence}/100{Style.RESET_ALL}"
            )
            await asyncio.sleep(1.5)

        log.info(
            f"✅ Skan #{self.total_scans} | "
            f"Juftliklar: {len(snaps)} | Signallar: {len(signals)} | "
            f"Filtrlangan: {filtered} | Jami: {self.total_signals}"
        )

    # ── Telegram handlers ──────────────────────────────────

    async def _status_text(self) -> str:
        uptime = datetime.now() - self.start_time
        h, m   = divmod(uptime.seconds // 60, 60)
        wr     = self.backtest.overall()
        wr_s   = f"<code>{wr:.0f}%</code>" if wr else "<code>—</code>"
        pos_n  = len(self.tracker.positions) if self.tracker else 0
        pl     = self.tracker.avg_pl() if self.tracker else None
        pl_s   = f"<code>{pl:+.1f}%</code>" if pl is not None else "<code>—</code>"

        top3   = sorted(self.neural.weights.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_s = ", ".join(f"{k[:12]}:{v:.1f}" for k,v in top3)

        return (
            f"📊 <b>WTP v4.5 — NEW TOKENS ONLY</b>\n\n"
            f"⏰ Kuzatish oynasi: <code>{NEW_TOKEN_MIN_HOURS*60:.0f}daq → {NEW_TOKEN_MAX_HOURS:.0f}soat</code>\n"
            f"⏱ Ishlash: <code>{uptime.days}k {h}s {m}d</code>\n"
            f"🔍 Skanlar: <code>{self.total_scans}</code>\n"
            f"📨 Signallar: <code>{self.total_signals}</code>\n"
            f"☠️ Rug alertlar: <code>{self.rug_alerts}</code>\n"
            f"🚫 Filtrlangan: <code>{self.filtered_out}</code>\n"
            f"📚 Umumiy to'g'rilik: {wr_s}\n"
            f"💰 O'rtacha P&L: {pl_s}\n"
            f"💼 Ochiq pozitsiyalar: <code>{pos_n}</code>\n"
            f"🌊 Rejim: <code>{self.engine.regime.current}</code>\n"
            f"🧬 Top weights: <code>{html.escape(top3_s)}</code>\n"
            f"⏸ Holat: <code>{'TOXTATILGAN' if self.paused else 'FAOL'}</code>"
        )

    def _is_auth(self, u: Update) -> bool:
        """Faqat egasi (TELEGRAM_CHAT_ID) botni boshqarishi mumkin."""
        uid = u.effective_user.id if u.effective_user else None
        # Ikkalasi ham int yoki string bo'lishi mumkin, shuning uchun stringga o'tkazamiz
        return str(uid) == str(TELEGRAM_CHAT_ID)

    async def h_start(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not self._is_auth(u): return
        await u.message.reply_text(
            "🐋 <b>Whale Tracker Pro v4.0</b>\nBoshqaruv paneli:",
            parse_mode=ParseMode.HTML, reply_markup=self._kb()
        )

    async def h_status(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not self._is_auth(u): return
        await u.message.reply_text(
            await self._status_text(), parse_mode=ParseMode.HTML, reply_markup=self._kb()
        )

    async def h_setlimit(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not self._is_auth(u): return
        try:
            v = int(c.args[0])
            if v < 10_000:
                await u.message.reply_text("❌ Minimal limit $10,000")
                return
            global MIN_VOLUME_24H
            MIN_VOLUME_24H = v
            await u.message.reply_text(
                f"✅ Yangi hajm limiti: <code>${v:,}</code>",
                parse_mode=ParseMode.HTML
            )
        except (IndexError, ValueError):
            await u.message.reply_text("Foydalanish: /setlimit 150000")

    async def h_setconf(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        """Minimal confidence darajasini sozlash."""
        if not self._is_auth(u): return
        try:
            v = int(c.args[0])
            if not (50 <= v <= 95):
                await u.message.reply_text("❌ Qiymat 50-95 oralig'ida bo'lishi kerak")
                return
            global MIN_CONFIDENCE
            MIN_CONFIDENCE = v
            await u.message.reply_text(
                f"✅ Yangi min confidence: <code>{v}/100</code>",
                parse_mode=ParseMode.HTML
            )
        except (IndexError, ValueError):
            await u.message.reply_text("Foydalanish: /setconf 70")

    async def h_cb(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not self._is_auth(u): return
        q = u.callback_query
        await q.answer()
        d = q.data

        async def edit(txt):
            try:
                await q.edit_message_text(
                    txt, parse_mode=ParseMode.HTML, reply_markup=self._kb()
                )
            except Exception as e:
                if "not modified" not in str(e).lower():
                    log.debug(f"edit_message xatosi: {e}")

        if d == "status":
            await edit(await self._status_text())

        elif d == "top5":
            if not self._snaps:
                await q.message.reply_text("Hali skan amalga oshirilmagan.")
                return
            top = sorted(self._snaps, key=lambda s: s.volume_24h, reverse=True)[:5]
            lines = ["📈 <b>Top 5 (hajm bo'yicha)</b>\n"]
            for i, s in enumerate(top, 1):
                lines.append(
                    f"{i}. <code>{html.escape(s.token_symbol)}</code> "
                    f"({s.chain.upper()}) "
                    f"<code>${s.volume_24h:,.0f}</code> | "
                    f"<code>{s.change_24h:+.1f}%</code>"
                )
            await edit("\n".join(lines))

        elif d == "pause":
            self.paused = not self.paused
            await edit(await self._status_text())

        elif d == "winrate":
            await edit(f"📚 <b>Signal to'g'riligi:</b>\n\n{self.backtest.summary()}")

        elif d == "weights":
            wt   = self.neural.weights
            top  = sorted(wt.items(), key=lambda x: x[1], reverse=True)[:8]
            lines = ["🧬 <b>Neural og'irliklar (adaptive):</b>\n"]
            for k, v in top:
                bar = "█" * int(v / 3) + "░" * max(0, 10 - int(v / 3))
                lines.append(f"<code>{bar}</code> {html.escape(k)}: <code>{v:.2f}</code>")
            await edit("\n".join(lines))

        elif d == "regime":
            r    = self.engine.regime
            hist = list(r._history)[-5:]
            trend = " → ".join(f"{x:+.1f}%" for x in hist) if hist else "—"
            await edit(
                f"🌊 <b>Bozor Rejimi:</b> <code>{r.current}</code>\n\n"
                f"So'nggi o'zgarishlar:\n<code>{trend}</code>\n\n"
                f"Confidence delta: <code>{r.confidence_delta:+d}</code>"
            )

        elif d == "scan_now":
            asyncio.create_task(self.scan())
            await q.message.reply_text("🔍 Skan boshlandi...")

        elif d == "positions":
            if not self.tracker or not self.tracker.positions:
                await q.message.reply_text("💼 Hozircha ochiq pozitsiyalar yo'q.")
                return
            lines = ["💼 <b>Ochiq pozitsiyalar:</b>\n"]
            for addr, pos in list(self.tracker.positions.items())[:8]:
                elapsed = (datetime.now() - pos.opened_at).total_seconds() / 3600
                lines.append(
                    f"• <code>{html.escape(pos.snap.token_symbol)}</code> "
                    f"[{pos.signal_type}] "
                    f"${pos.entry_price:.8f} | "
                    f"{elapsed:.1f}s | "
                    f"T1:{'✅' if pos.t1_hit else '○'}"
                )
            await edit("\n".join(lines))

    async def h_error(self, u: object, c: ContextTypes.DEFAULT_TYPE):
        log.error(f"TG xatosi: {c.error}")

    async def run(self):
        print(f'''
╔══════════════════════════════════════════════════════════╗
║       WHALE TRACKER PRO v4.5 — NEW TOKENS ONLY           ║
╠══════════════════════════════════════════════════════════╣
║  Kuzatish: {NEW_TOKEN_MIN_HOURS*60:.0f} daqiqa → {NEW_TOKEN_MAX_HOURS:.0f} soat yosh tokenlar              ║
║  Signallar: MOONSHOT | STRONG_BUY | BREAKOUT | RUG      ║
╚══════════════════════════════════════════════════════════╝''')

        self.tracker = PositionTracker(self.send)
        await self.startup()

        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_error_handler(self.h_error)
        app.add_handler(CommandHandler("start",    self.h_start))
        app.add_handler(CommandHandler("status",   self.h_status))
        app.add_handler(CommandHandler("setlimit", self.h_setlimit))
        app.add_handler(CommandHandler("setconf",  self.h_setconf))
        app.add_handler(CallbackQueryHandler(self.h_cb))

        sched = AsyncIOScheduler(timezone=timezone.utc)
        sched.add_job(
            self.scan, "interval",
            seconds=SCAN_INTERVAL_SEC,
            next_run_time=datetime.now(timezone.utc)
        )
        sched.start()

        log.info("🚀 WTP v4.0 ishga tushdi. To'xtatish: Ctrl+C")
        async with app:
            await app.start()
            await app.updater.start_polling()
            try:
                while True:
                    await asyncio.sleep(60)
            except (KeyboardInterrupt, SystemExit):
                log.info("To'xtatilmoqda...")
            finally:
                await app.updater.stop()
                await app.stop()

        sched.shutdown()
        await self.http.close()
        log.info("WTP v4.0 to'xtatildi.")


# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Web serverni alohida thread da ishga tushirish
    threading.Thread(target=start_server, daemon=True).start()
    
    try:
        asyncio.run(WhaleTrackerV4().run())
    except KeyboardInterrupt:
        pass
