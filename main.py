import time
from clients.explorer import ExplorerClient
from clients.dexscreener import DexScreenerClient
from clients.telegram import TelegramClient
from engine import Tracker
from config import WALLETS, UPDATE_INTERVAL

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
