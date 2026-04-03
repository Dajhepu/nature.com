import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY", "")
ARBISCAN_API_KEY = os.getenv("ARBISCAN_API_KEY", "")
POLYGONSCAN_API_KEY = os.getenv("POLYGONSCAN_API_KEY", "")
SNOWTRACE_API_KEY = os.getenv("SNOWTRACE_API_KEY", "")

UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 30))
MIN_USD_THRESHOLD = float(os.getenv("MIN_USD_THRESHOLD", 5000))

# Professional Filtering Thresholds
FILTER_WIN_RATE = float(os.getenv("FILTER_WIN_RATE", 70.0))
FILTER_PNL = float(os.getenv("FILTER_PNL", 100000.0))
FILTER_MIN_TRADES = int(os.getenv("FILTER_MIN_TRADES", 20))

SCAN_APIS = {
    "eth": {"url": "https://api.etherscan.io/api", "key_param": "apikey", "label": "Etherscan", "dex_chain": "ethereum", "api_key": ETHERSCAN_API_KEY},
    "bsc": {"url": "https://api.bscscan.com/api", "key_param": "apikey", "label": "BSCScan", "dex_chain": "bsc", "api_key": BSCSCAN_API_KEY},
    "base": {"url": "https://api.basescan.org/api", "key_param": "apikey", "label": "Basescan", "dex_chain": "base", "api_key": BASESCAN_API_KEY},
    "arbitrum": {"url": "https://api.arbiscan.io/api", "key_param": "apikey", "label": "Arbiscan", "dex_chain": "arbitrum", "api_key": ARBISCAN_API_KEY},
    "polygon": {"url": "https://api.polygonscan.com/api", "key_param": "apikey", "label": "Polygonscan", "dex_chain": "polygon", "api_key": POLYGONSCAN_API_KEY},
    "avalanche": {"url": "https://api.snowtrace.io/api", "key_param": "apikey", "label": "Snowtrace", "dex_chain": "avalanche", "api_key": SNOWTRACE_API_KEY},
}

STABLES = {"usdt", "usdc", "dai", "busd", "tusd", "usdp", "frax", "lusd", "gusd", "susd", "cusd", "usd+"}
WRAPPERS = {"weth", "wbnb", "wmatic", "wavax", "wftm"}

# ─────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────

class ExplorerClient:
    def __init__(self):
        self.apis = SCAN_APIS
        self.solana_url = "https://api.mainnet-beta.solana.com"

    def get_token_transactions(self, wallet_addr, chain, limit=20):
        if chain == "solana":
            return self.get_solana_transactions(wallet_addr, limit)

        scan = self.apis.get(chain)
        if not scan: return []

        api_key = scan.get("api_key")
        params = {
            "module": "account", "action": "tokentx", "address": wallet_addr,
            "sort": "desc", "offset": limit, "page": 1,
        }
        if api_key: params[scan["key_param"]] = api_key

        try:
            response = requests.get(scan["url"], params=params, timeout=10)
            data = response.json()
            if data.get("status") == "1" and isinstance(data.get("result"), list):
                return data["result"]
        except Exception as e:
            print(f"Error fetching from {scan['label']}: {e}")
        return []

    def get_solana_transactions(self, wallet_addr, limit=20):
        payload = {
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [wallet_addr, {"limit": limit}]
        }
        try:
            response = requests.post(self.solana_url, json=payload, timeout=10)
            data = response.json()
            if "result" in data: return data["result"]
        except Exception as e:
            print(f"Error fetching from Solana: {e}")
        return []

class DexScreenerClient:
    BASE_URL = "https://api.dexscreener.com"

    def get_token_data(self, token_addr, chain):
        try:
            url = f"{self.BASE_URL}/latest/dex/tokens/{token_addr}"
            response = requests.get(url, timeout=10)
            data = response.json()
            pairs = data.get("pairs", [])
            if not pairs: return None

            dex_chain = SCAN_APIS.get(chain, {}).get("dex_chain", chain)
            chain_pairs = [p for p in pairs if p.get("chainId") == dex_chain]
            if not chain_pairs:
                pair = pairs[0]
            else:
                pair = sorted(chain_pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)[0]

            return {
                "price": float(pair.get("priceUsd", 0)),
                "price_str": pair.get("priceUsd", "—"),
                "mcap": pair.get("fdv") or pair.get("marketCap") or 0,
                "vol24h": pair.get("volume", {}).get("h24", 0),
                "price_change_24h": pair.get("priceChange", {}).get("h24", 0),
                "pair_addr": pair.get("pairAddress"),
                "dex": pair.get("dexId"),
                "liquidity": pair.get("liquidity", {}).get("usd", 0),
                "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
            }
        except Exception as e:
            print(f"Error fetching DexScreener data: {e}")
            return None

    def get_trending_tokens(self):
        try:
            url = f"{self.BASE_URL}/token-boosts/latest/v1"
            response = requests.get(url, timeout=10)
            return response.json()
        except Exception as e:
            print(f"Error fetching trending tokens: {e}")
            return []

class TelegramClient:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_update_id = 0

    def format_num(self, n):
        if not n or n == 0: return "0"
        if abs(n) >= 1e9: return f"{n/1e9:.2f}B"
        if abs(n) >= 1e6: return f"{n/1e6:.2f}M"
        if abs(n) >= 1e3: return f"{n/1e3:.1f}K"
        if abs(n) >= 1: return f"{n:.2f}"
        return f"{n:.4g}"

    def send_message(self, text, chat_id=None):
        target = chat_id or self.chat_id
        if not self.token or not target: return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": target, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.json().get("ok", False)
        except: return False

    def get_updates(self):
        if not self.token: return []
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 2}
        try:
            res = requests.get(url, params=params, timeout=5)
            data = res.json()
            if data.get("ok"):
                updates = data.get("result", [])
                if updates:
                    self.last_update_id = updates[-1]["update_id"]
                return updates
        except: pass
        return []

# ─────────────────────────────────────────────
# ANALYTICS ENGINE
# ─────────────────────────────────────────────

class StatsManager:
    def __init__(self, explorer, dex):
        self.explorer = explorer
        self.dex = dex

    def calculate_wallet_stats(self, addr, chain):
        txs = self.explorer.get_token_transactions(addr, chain, limit=100)
        if not txs: return {"win_rate": 0, "pnl": 0, "trades": 0}

        tokens = {}
        for tx in txs:
            t_addr = tx.get("contractAddress")
            if not t_addr: continue
            sym = (tx.get("tokenSymbol") or "").lower()
            if sym in STABLES or sym in WRAPPERS: continue
            if t_addr not in tokens: tokens[t_addr] = {"buy_amt": 0, "sell_amt": 0}
            decimals = int(tx.get("tokenDecimal") or 18)
            amt = int(tx.get("value") or 0) / (10**decimals)
            if tx.get("to", "").lower() == addr.lower(): tokens[t_addr]["buy_amt"] += amt
            else: tokens[t_addr]["sell_amt"] += amt

        total_pnl = 0
        wins = 0
        trade_count = 0
        for t_addr, data in tokens.items():
            if data["buy_amt"] == 0: continue
            t_data = self.dex.get_token_data(t_addr, chain)
            if not t_data: continue
            price = t_data["price"]
            current_value = (data["buy_amt"] - data["sell_amt"]) * price
            if current_value < 0: current_value = 0
            change_pct = t_data["price_change_24h"]
            estimated_entry_price = price / (1 + (change_pct / 100))
            estimated_cost = data["buy_amt"] * estimated_entry_price
            estimated_revenue = data["sell_amt"] * price + current_value
            pnl = estimated_revenue - estimated_cost
            total_pnl += pnl
            if pnl > 0: wins += 1
            trade_count += 1
        win_rate = (wins / trade_count * 100) if trade_count > 0 else 0
        return {"win_rate": win_rate, "pnl": total_pnl, "trades": trade_count}

# ─────────────────────────────────────────────
# MAIN TRACKER
# ─────────────────────────────────────────────

class Tracker:
    def __init__(self):
        self.explorer = ExplorerClient()
        self.dex = DexScreenerClient()
        self.tg = TelegramClient()
        self.stats = StatsManager(self.explorer, self.dex)
        self.wallets = []
        self.polled_hashes = {}
        self.state_file = "tracker_state.json"
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    self.wallets = state.get("wallets", [])
                    hashes = state.get("polled_hashes", {})
                    self.polled_hashes = {addr: set(h) for addr, h in hashes.items()}
            except: pass

    def save_state(self):
        try:
            with open(self.state_file, "w") as f:
                hashes = {addr: list(h) for addr, h in self.polled_hashes.items()}
                json.dump({"wallets": self.wallets, "polled_hashes": hashes}, f)
        except: pass

    def discover_wallets(self):
        print("Running Discovery Engine...")
        trending = self.dex.get_trending_tokens()
        new_wallets = []
        for item in trending[:5]:
            t_addr = item.get("tokenAddress")
            chain = item.get("chainId")
            scan_chain = next((k for k, v in SCAN_APIS.items() if v["dex_chain"] == chain), chain)
            txs = self.explorer.get_token_transactions(t_addr, scan_chain, limit=50)
            for tx in txs:
                buyer_addr = tx.get("to")
                if buyer_addr and buyer_addr.lower() not in [w["addr"].lower() for w in self.wallets]:
                    s = self.stats.calculate_wallet_stats(buyer_addr, scan_chain)
                    if s["win_rate"] >= FILTER_WIN_RATE and s["pnl"] >= FILTER_PNL and s["trades"] >= FILTER_MIN_TRADES:
                        new_wallet = {
                            "addr": buyer_addr, "chain": scan_chain, "label": f"Smart_{buyer_addr[:4]}",
                            "win_rate": s["win_rate"], "pnl": s["pnl"], "trades": s["trades"], "active": True
                        }
                        new_wallets.append(new_wallet)
                        self.tg.send_message(f"✨ <b>Smart Wallet Found!</b>\n\nAddr: <code>{buyer_addr}</code>\nWin Rate: {s['win_rate']:.1f}%\nPnL: ${self.tg.format_num(s['pnl'])}\nTrades: {s['trades']}")
        self.wallets.extend(new_wallets)
        self.save_state()

    def poll_wallets(self):
        for wallet in self.wallets:
            if not wallet.get("active"): continue
            addr = wallet["addr"]
            chain = wallet["chain"]
            txs = self.explorer.get_token_transactions(addr, chain)
            if not txs: continue
            if addr not in self.polled_hashes:
                self.polled_hashes[addr] = {tx.get("hash") or tx.get("signature") for tx in txs}
                continue
            known = self.polled_hashes[addr]
            by_hash = {}
            for tx in txs:
                tid = tx.get("hash") or tx.get("signature")
                if tid in known: continue
                if tid not in by_hash: by_hash[tid] = []
                by_hash[tid].append(tx)
                known.add(tid)
            for tid, group in by_hash.items():
                self.process_signal(wallet, group, chain, tid)
        self.save_state()

    def process_signal(self, wallet, group, chain, tid):
        traded_tx = next((tx for tx in group if tx.get("tokenSymbol", "").lower() not in STABLES | WRAPPERS), group[0])
        t_symbol = traded_tx.get("tokenSymbol", "UNKNOWN")
        t_addr = traded_tx.get("contractAddress")
        is_buy = traded_tx.get("to", "").lower() == wallet["addr"].lower()
        t_data = self.dex.get_token_data(t_addr, chain)
        if not t_data: return
        decimals = int(traded_tx.get("tokenDecimal") or 18)
        amt = int(traded_tx.get("value") or 0) / (10**decimals)
        usd_val = amt * t_data["price"]
        if usd_val < MIN_USD_THRESHOLD: return
        msg = f"{'🟢 BUY' if is_buy else '🔴 SELL'} <b>{t_symbol}</b> (${self.tg.format_num(usd_val)})\n"
        msg += f"Wallet: {wallet['label']} (WR: {wallet['win_rate']:.1f}%)\n"
        msg += f"Price: ${t_data['price_str']} | MCAP: ${self.tg.format_num(t_data['mcap'])}\n"
        msg += f"<a href='https://dexscreener.com/{chain}/{t_data['pair_addr']}'>DexScreener</a>"
        self.tg.send_message(msg)

    def handle_commands(self):
        updates = self.tg.get_updates()
        for u in updates:
            msg = u.get("message", {})
            text = msg.get("text", "")
            cid = msg.get("chat", {}).get("id") or msg.get("from", {}).get("id")
            if not text.startswith("/"): continue
            parts = text.split()
            cmd = parts[0]
            args = parts[1:]
            if cmd == "/start":
                self.tg.send_message("🚀 <b>Smart Money Tracker PRO</b>\n\nCommands:\n/list - Monitored wallets\n/add &lt;addr&gt; &lt;chain&gt; - Add wallet\n/remove &lt;addr&gt; - Remove wallet\n/find - Trigger discovery\n/stats &lt;addr&gt; &lt;chain&gt; - Get metrics", cid)
            elif cmd == "/list":
                res = "<b>Monitored Wallets:</b>\n"
                for w in self.wallets:
                    res += f"• {w['label']} ({w['chain']}): {w['win_rate']:.1f}% WR, ${self.tg.format_num(w['pnl'])} PnL\n"
                self.tg.send_message(res, cid)
            elif cmd == "/add" and len(args) >= 2:
                addr, chain = args[0], args[1]
                s = self.stats.calculate_wallet_stats(addr, chain)
                w = {"addr": addr, "chain": chain, "label": f"Manual_{addr[:4]}", "win_rate": s["win_rate"], "pnl": s["pnl"], "trades": s["trades"], "active": True}
                self.wallets.append(w)
                self.tg.send_message(f"✅ Added {addr} on {chain}\nWR: {s['win_rate']:.1f}%, PnL: ${self.tg.format_num(s['pnl'])}", cid)
                self.save_state()
            elif cmd == "/remove" and len(args) >= 1:
                addr = args[0]
                self.wallets = [w for w in self.wallets if w["addr"].lower() != addr.lower()]
                self.tg.send_message(f"🗑 Removed {addr}", cid)
                self.save_state()
            elif cmd == "/find":
                self.tg.send_message("🔍 Starting discovery engine...", cid)
                self.discover_wallets()
            elif cmd == "/stats" and len(args) >= 2:
                addr, chain = args[0], args[1]
                s = self.stats.calculate_wallet_stats(addr, chain)
                res = f"📊 <b>Stats for {addr}</b>\nWin Rate: {s['win_rate']:.1f}%\nPnL: ${self.tg.format_num(s['pnl'])}\nTotal Trades: {s['trades']}"
                self.tg.send_message(res, cid)

def main():
    tracker = Tracker()
    print("Tracker started...")
    last_discovery = 0
    last_poll = 0
    while True:
        tracker.handle_commands()
        now = time.time()
        if now - last_poll > UPDATE_INTERVAL:
            tracker.poll_wallets()
            last_poll = now
        if now - last_discovery > 3600:
            tracker.discover_wallets()
            last_discovery = now
        time.sleep(1)

if __name__ == "__main__":
    main()
