import os
import telegram
from flask import current_app
import asyncio


def send_telegram_message(chat_id, text):
    """
    Sends a message to a Telegram user.
    """
    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not token:
        current_app.logger.warning("TELEGRAM_BOT_TOKEN not configured. Message not sent.")
        return False

    async def _send_async():
        try:
            bot = telegram.Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=text)
            current_app.logger.info(f"Message sent successfully to chat_id: {chat_id}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send message to {chat_id}: {e}")
            return False

    try:
        # Simplest way, works if no event loop is running.
        return asyncio.run(_send_async())
    except RuntimeError:
        # Fallback for environments where an event loop is already running (e.g., gevent).
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_send_async())
        finally:
            loop.close()
