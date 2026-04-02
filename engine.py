import time
import json
import os
from config import STABLES, WRAPPERS, MIN_USD_THRESHOLD

class Tracker:
    def __init__(self, explorer, dexscreener, telegram, wallets):
        self.explorer = explorer
        self.dex = dexscreener
        self.tg = telegram
        self.wallets = wallets
        self.polled_hashes = {} # {wallet_addr: set(hashes)}
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

            # Deduplicate and group by hash
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

            time.sleep(0.5) # Rate limiting

        self.save_state()

    def process_tx_group(self, wallet, tx_group, chain, tx_id):
        if chain == "solana":
            self.process_solana_tx(wallet, tx_id)
            return

        # Find the traded token (non-stable, non-wrapper)
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

        # BUY if wallet is 'to'
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
        # Solana monitoring is basic in JS as well
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
