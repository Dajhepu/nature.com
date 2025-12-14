import asyncio
from flask import current_app
from .pyrogram_client import get_pyrogram_client

async def send_telegram_message_async(chat_id, text):
    """
    Asynchronously sends a message to a Telegram user using the shared Pyrogram client.
    """
    print(f"--- 🚀 Preparing to send message to {chat_id} 🚀 ---")
    try:
        app = get_pyrogram_client()
        await app.start()
        try:
            await app.send_message(chat_id=chat_id, text=text)
            print(f"✅ Message sent successfully to chat_id: {chat_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to send message to {chat_id}: {e}")
            return False
        finally:
            await app.stop()
            print("🛑 Pyrogram client stopped.")
    except Exception as e:
        print(f"❌ An error occurred during Pyrogram client handling: {e}")
        return False

def send_telegram_message(chat_id, text):
    """
    Synchronous wrapper to run the async Pyrogram message sender.
    """
    with current_app.app_context():
        return asyncio.run(send_telegram_message_async(chat_id, text))
