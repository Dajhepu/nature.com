# backend/app/telegram_scraper.py

import os
import asyncio
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import UserStatusOnline, UserStatusRecently
from telethon.errors.rpcerrorlist import SessionPasswordNeededError

API_ID = os.environ.get('TELEGRAM_API_ID')
API_HASH = os.environ.get('TELEGRAM_API_HASH')
SESSION_STRING = os.environ.get('TELEGRAM_SESSION_STRING')

# --- Main Scraper Logic ---
async def get_group_members_async(group_link, max_members=100):
    """
    Scrapes active members from a public Telegram group using a session string.
    """
    print("--- 🕵️ Starting Telegram Scraper Diagnosis 🕵️ ---")

    # 1. Check if variables exist
    if not API_ID:
        print("❌ ERROR: TELEGRAM_API_ID is not set in environment variables.")
        return {"error": "TELEGRAM_API_ID is not configured."}
    if not API_HASH:
        print("❌ ERROR: TELEGRAM_API_HASH is not set in environment variables.")
        return {"error": "TELEGRAM_API_HASH is not configured."}
    if not SESSION_STRING:
        print("❌ ERROR: TELEGRAM_SESSION_STRING is not set in environment variables.")
        return {"error": "TELEGRAM_SESSION_STRING is not set. Please generate it first."}

    # 2. Log variable types and partial values for debugging
    print(f"✅ API_ID loaded: {API_ID[:4]}... (Type: {type(API_ID)})")
    print(f"✅ API_HASH loaded: {API_HASH[:4]}... (Type: {type(API_HASH)})")
    print(f"✅ SESSION_STRING loaded: {SESSION_STRING[:10]}... (Length: {len(SESSION_STRING)})")

    try:
        # 3. Try to cast API_ID to int
        try:
            api_id_int = int(API_ID)
            print(f"✅ API_ID successfully cast to integer: {api_id_int}")
        except (ValueError, TypeError):
            print(f"❌ CRITICAL ERROR: Could not convert API_ID ('{API_ID}') to an integer.")
            return {"error": f"Invalid API_ID format: '{API_ID}'. It must be a number."}

        # Use a context manager to ensure the client is properly closed
        async with TelegramClient(StringSession(SESSION_STRING), api_id_int, API_HASH) as client:
            print("▶️ Connecting to Telegram via session string...")
            is_connected = await client.is_user_authorized()
            if not is_connected:
                error_message = "❌ Client not authorized. The session string might be invalid or expired."
                print(error_message)
                return {"error": error_message}

            print(f"✅ Connection successful. Scraping group: {group_link}")

            try:
                entity = await client.get_entity(group_link)
            except (ValueError, TypeError) as e:
                 error_message = f"❌ Invalid group link ('{group_link}'). It might be incorrect or you may not have access. Details: {e}"
                 print(error_message)
                 return {"error": error_message}

            members_data = []
            count = 0

            async for user in client.iter_participants(entity, limit=max_members * 2):
                if count >= max_members:
                    break

                if not user.bot and not user.deleted:
                    if isinstance(user.status, (UserStatusOnline, UserStatusRecently)):
                        members_data.append({
                            'user_id': user.id,
                            'username': user.username,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'status': type(user.status).__name__
                        })
                        count += 1
                        print(f"  [{count}/{max_members}] Found active user: {user.username or user.first_name}")

            print(f"✅ Scraping complete. Total active members found: {len(members_data)}")
            return {"members": members_data}

    except Exception as e:
        error_message = f"❌ An unexpected error occurred: {e}"
        print(f"Error Type: {type(e)}")
        print(error_message)
        return {"error": error_message}

def get_group_members(group_link, max_members=100):
    """Synchronous wrapper to run the async scraper."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_group_members_async(group_link, max_members))
