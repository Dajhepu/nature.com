import requests

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

            # Chain mapping from config-like names to DexScreener names
            chain_map = {
                "eth": "ethereum",
                "bsc": "bsc",
                "base": "base",
                "arbitrum": "arbitrum",
                "polygon": "polygon",
                "avalanche": "avalanche"
            }
            dex_chain = chain_map.get(chain, chain)

            # Filter pairs by chain
            chain_pairs = [p for p in pairs if p.get("chainId") == dex_chain]
            if not chain_pairs:
                pair = pairs[0]
            else:
                # Sort by liquidity
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
