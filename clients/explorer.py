import requests
import time
from config import SCAN_APIS, ETHERSCAN_API_KEY, BSCSCAN_API_KEY

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
