import requests
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

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
