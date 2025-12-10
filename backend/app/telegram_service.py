import os
import telegram
from flask import current_app

def send_telegram_message(chat_id, text):
    """
    Sends a message to a Telegram user or group.
    For now, this function will just print the message to the console.
    """
    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("---- Telegram Bot Token not configured. ----")
        return

    print("---- Sending Telegram Message ----")
    print(f"Chat ID: {chat_id}")
    print(f"Text: {text}")
    print("----------------------------------")

    # Uncomment the following to use the actual Telegram Bot API
    # try:
    #     bot = telegram.Bot(token=token)
    #     await bot.send_message(chat_id=chat_id, text=text)
    #     return True
    # except Exception as e:
    #     print(f"Error sending Telegram message: {e}")
    #     return False
