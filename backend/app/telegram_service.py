import asyncio
from flask import current_app

async def send_telegram_message_async(app, chat_id, text):
    """
    Asynchronously sends a message to a Telegram user using an active Pyrogram client.
    Returns True on success, False on failure.
    """
    try:
        await app.send_message(chat_id=chat_id, text=text)
        current_app.logger.info(f"Message sent successfully to chat_id: {chat_id}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send message to {chat_id}: {e}", exc_info=True)
        return False

# The synchronous wrapper is no longer needed here.
# The client lifecycle will be managed directly in the route for batch sending.
