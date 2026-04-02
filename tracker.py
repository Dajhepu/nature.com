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

# Wallets to monitor (examples from demo data)
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

# ─────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────

class ExplorerClient:
    def __init__(self):
        self.apis = SCAN_APIS
        self.solana_url = "https://api.mainnet-beta.solana.com"

    def get_token_transactions(self, wallet_addr, chain):
        if chain == "solana":
            return self.get_solana_transactions(wallet_addr)

        scan = self.apis.get(chain)
        if not scan:
            return []

        api_key = BSCSCAN_API_KEY if chain == "bsc" else ETHERSCAN_API_KEY
        params = {
            "module": "account",
            "action": "tokentx",
            "address": wallet_addr,
            "sort": "desc",
            "offset": 20,
            "page": 1,
        }
        if api_key:
            params[scan["key_param"]] = api_key

        try:
            response = requests.get(scan["url"], params=params, timeout=10)
            data = response.json()
            if data.get("status") == "1" and isinstance(data.get("result"), list):
                return data["result"]
        except Exception as e:
            print(f"Error fetching from {scan['label']}: {e}")

        return []

    def get_solana_transactions(self, wallet_addr):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet_addr, {"limit": 20}]
        }
        try:
            response = requests.post(self.solana_url, json=payload, timeout=10)
            data = response.json()
            if "result" in data:
                return data["result"]
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
            if not pairs:
                return None

            chain_map = {
                "eth": "ethereum",
                "bsc": "bsc",
                "base": "base",
                "arbitrum": "arbitrum",
                "polygon": "polygon",
                "avalanche": "avalanche"
            }
            dex_chain = chain_map.get(chain, chain)

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
            }
        except Exception as e:
            print(f"Error fetching DexScreener data: {e}")
            return None

class TelegramClient:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID

    def format_num(self, n):
        if not n or n == 0:
            return "0"
        if n >= 1e9:
            return f"{n/1e9:.2f}B"
        if n >= 1e6:
            return f"{n/1e6:.2f}M"
        if n >= 1e3:
            return f"{n/1e3:.1f}K"
        if n >= 1:
            return f"{n:.2f}"
        return f"{n:.4g}"

    def format_signal_message(self, trade):
        emoji = "🟢" if trade["type"] == "buy" else "🔴" if trade["type"] == "sell" else "⚪"
        action_word = "BUY" if trade["type"] == "buy" else "SELL" if trade["type"] == "sell" else "SWAP"
        usd_str = f"${self.format_num(trade['usd_value'])}" if trade["usd_value"] > 0 else "?"
        td = trade["token_data"]
        chain_up = trade["chain"].upper()

        dex_link = f"https://dexscreener.com/{trade['chain']}/{td['pair_addr']}" if td and td.get("pair_addr") else ""

        expl_links = {
            "eth": f"https://etherscan.io/tx/{trade['hash']}",
            "bsc": f"https://bscscan.com/tx/{trade['hash']}",
            "base": f"https://basescan.org/tx/{trade['hash']}",
            "arbitrum": f"https://arbiscan.io/tx/{trade['hash']}"
        }
        expl_link = expl_links.get(trade["chain"], "")

        msg = f"{emoji} <b>{action_word} SIGNAL</b> — chainEDGE\n\n"
        msg += f"💎 <b>Smart Money:</b> <code>{trade['wallet']['addr'][:6]}...{trade['wallet']['addr'][-4:]}</code> ({trade['wallet']['label']})\n"
        msg += f"📊 <b>Token:</b> <b>${trade['token']}</b>\n"
        msg += f"🔗 <b>Chain:</b> {chain_up}\n"
        msg += f"💰 <b>Value:</b> <b>{usd_str}</b>\n"

        if td:
            msg += f"📈 <b>Price:</b> ${td['price_str']}\n"
            if td.get("mcap", 0) > 0:
                msg += f"💹 <b>Market Cap:</b> ${self.format_num(td['mcap'])}\n"
            if td.get("vol24h", 0) > 0:
                msg += f"📊 <b>24h Volume:</b> ${self.format_num(td['vol24h'])}\n"
            if td.get("liquidity", 0) > 0:
                msg += f"🏊 <b>Liquidity:</b> ${self.format_num(td['liquidity'])}\n"
            if td.get("price_change_24h"):
                change = td["price_change_24h"]
                msg += f"📉 <b>24h Change:</b> {'+' if change > 0 else ''}{change:.1f}%\n"
            if td.get("dex"):
                msg += f"🏦 <b>DEX:</b> {td['dex']}\n"

        msg += f"\n🏦 <b>Wallet Stats:</b>\n"
        msg += f"• Win Rate: {trade['wallet']['winRate']}\n"
        msg += f"• PnL: {trade['wallet']['pnl']}\n"
        msg += f"• Trades (30d): {trade['wallet']['trades30d']}\n"
        if trade["wallet"].get("notes"):
            msg += f"• Notes: {trade['wallet']['notes']}\n"

        msg += "\n"
        links = []
        if dex_link:
            links.append(f'<a href="{dex_link}">DexScreener</a>')
        if expl_link:
            links.append(f'<a href="{expl_link}">TX</a>')

        if links:
            msg += " | ".join(links) + "\n"

        timestamp_str = datetime.fromtimestamp(trade["timestamp"]).strftime("%H:%M:%S")
        msg += f"⏰ {timestamp_str} UTC"

        return msg

    def send_signal(self, trade):
        if not self.token or not self.chat_id:
            return False

        msg = self.format_signal_message(trade)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json().get("ok", False)
        except Exception as e:
            print(f"Error sending Telegram signal: {e}")
            return False

# ─────────────────────────────────────────────
# CORE ENGINE
# ─────────────────────────────────────────────

class Tracker:
    def __init__(self, explorer, dexscreener, telegram, wallets):
        self.explorer = explorer
        self.dex = dexscreener
        self.tg = telegram
        self.wallets = wallets
        self.polled_hashes = {}
        self.state_file = "polled_hashes.json"
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.polled_hashes = {addr: set(hashes) for addr, hashes in data.items()}
            except Exception as e:
                print(f"Error loading state: {e}")

    def save_state(self):
        try:
            with open(self.state_file, "w") as f:
                data = {addr: list(hashes) for addr, hashes in self.polled_hashes.items()}
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving state: {e}")

    def poll_all(self):
        for wallet in self.wallets:
            print(f"Polling {wallet['label']} ({wallet['addr']}) on {wallet['chain']}...")
            txs = self.explorer.get_token_transactions(wallet["addr"], wallet["chain"])
            if not txs:
                continue

            addr = wallet["addr"]
            if addr not in self.polled_hashes:
                self.polled_hashes[addr] = {tx.get("hash") or tx.get("signature") for tx in txs}
                continue

            known = self.polled_hashes[addr]

            by_hash = {}
            for tx in txs:
                tx_id = tx.get("hash") or tx.get("signature")
                if tx_id in known:
                    continue

                if tx_id not in by_hash:
                    by_hash[tx_id] = []
                by_hash[tx_id].append(tx)
                known.add(tx_id)

            for tx_id, tx_group in by_hash.items():
                self.process_tx_group(wallet, tx_group, wallet["chain"], tx_id)

            time.sleep(0.5)

        self.save_state()

    def process_tx_group(self, wallet, tx_group, chain, tx_id):
        if chain == "solana":
            self.process_solana_tx(wallet, tx_id)
            return

        traded_tx = None
        for tx in tx_group:
            sym = (tx.get("tokenSymbol") or "").lower()
            if sym not in STABLES and sym not in WRAPPERS:
                traded_tx = tx
                break

        if not traded_tx:
            traded_tx = tx_group[0]

        token_symbol = traded_tx.get("tokenSymbol") or "UNKNOWN"
        token_addr = traded_tx.get("contractAddress")
        decimals = int(traded_tx.get("tokenDecimal") or 18)
        value = int(traded_tx.get("value") or 0)
        raw_amt = value / (10 ** decimals)

        is_buy = traded_tx.get("to", "").lower() == wallet["addr"].lower()
        trade_type = "buy" if is_buy else "sell"

        token_data = self.dex.get_token_data(token_addr, chain)

        usd_value = 0
        if token_data:
            usd_value = raw_amt * token_data["price"]

        if usd_value > 0 and usd_value < MIN_USD_THRESHOLD:
            return

        trade = {
            "hash": tx_id,
            "type": trade_type,
            "wallet": wallet,
            "chain": chain,
            "token": token_symbol,
            "token_addr": token_addr,
            "amount": raw_amt,
            "usd_value": usd_value,
            "token_data": token_data,
            "timestamp": int(traded_tx.get("timeStamp") or time.time()),
        }

        print(f"New Signal identified: {trade_type.upper()} {token_symbol} (${usd_value:.2f})")
        sent = self.tg.send_signal(trade)
        if sent:
            print("Signal sent to Telegram.")

    def process_solana_tx(self, wallet, tx_id):
        trade = {
            "hash": tx_id,
            "type": "unknown",
            "wallet": wallet,
            "chain": "solana",
            "token": "SOL TX",
            "amount": 0,
            "usd_value": 0,
            "token_data": None,
            "timestamp": int(time.time()),
        }
        print(f"New Solana TX for {wallet['label']}")
        self.tg.send_signal(trade)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("🚀 chainEDGE Python - Starting Smart Money Tracker")
    print(f"Tracking {len(WALLETS)} wallets. Update interval: {UPDATE_INTERVAL}s")

    explorer = ExplorerClient()
    dex = DexScreenerClient()
    tg = TelegramClient()

    tracker = Tracker(explorer, dex, tg, WALLETS)

    try:
        while True:
            tracker.poll_all()
            print(f"Scan complete. Sleeping for {UPDATE_INTERVAL}s...")
            time.sleep(UPDATE_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopping tracker...")
        tracker.save_state()
    except Exception as e:
        print(f"Unexpected error: {e}")
        tracker.save_state()

if __name__ == "__main__":
    main()
