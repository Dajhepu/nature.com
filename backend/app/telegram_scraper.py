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

# --- Session Generation ---
# This part is for the first-time setup to generate a session string.
# It should be run locally, not on the server.
async def generate_session_string():
    """One-time script to generate a session string."""
    if not API_ID or not API_HASH:
        print("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables.")
        return

    async with TelegramClient(StringSession(), int(API_ID), API_HASH) as client:
        print("A confirmation code will be sent to your Telegram account.")

        try:
            # This will prompt for phone number, code, and 2FA password if needed
            await client.send_code_request(await client.get_me(input_request=True))
            await client.sign_in(await client.get_me(input_request=True), input('Enter the code: '))

            # Check for 2FA
            if await client.is_user_authorized() == False:
                 await client.sign_in(password=input('Please enter your 2FA password: '))

            print("\nSuccessfully logged in!")
            session_str = client.session.save()
            print("Your session string is (copy this to TELEGRAM_SESSION_STRING in Railway):")
            print(f"--> {session_str} <--")

        except SessionPasswordNeededError:
            password = input("Your 2FA password is required: ")
            await client.sign_in(password=password)

            print("\nSuccessfully logged in with 2FA!")
            session_str = client.session.save()
            print("Your session string is (copy this to TELEGRAM_SESSION_STRING in Railway):")
            print(f"--> {session_str} <--")

        except Exception as e:
            print(f"An error occurred: {e}")

# --- Main Scraper Logic ---
async def get_group_members_async(group_link, max_members=100):
    """
    Scrapes active members from a public Telegram group using a session string.
    """
    if not all([API_ID, API_HASH]):
        error_message = "❌ Telegram API_ID and API_HASH are not configured."
        print(error_message)
        return {"error": error_message}

    if not SESSION_STRING:
        error_message = "❌ TELEGRAM_SESSION_STRING is not set. Please generate it first."
        print(error_message)
        return {"error": error_message}

    try:
        # Use a context manager to ensure the client is properly closed
        async with TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH) as client:
            print("Connecting to Telegram via session string...")
            is_connected = await client.is_user_authorized()
            if not is_connected:
                error_message = "❌ Client is not authorized. The session string might be invalid or expired."
                print(error_message)
                return {"error": error_message}

            print(f"✅ Connection successful. Scraping group: {group_link}")

            try:
                entity = await client.get_entity(group_link)
            except (ValueError, TypeError):
                 error_message = f"❌ Invalid group link or username: '{group_link}'. Please use a valid t.me/ link or @username."
                 print(error_message)
                 return {"error": error_message}

            members_data = []
            count = 0

            async for user in client.iter_participants(entity, limit=max_members * 2): # Iterate more to find active ones
                if count >= max_members:
                    break

                if not user.bot and not user.deleted:
                    # Filter for users who were active recently
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
        print(error_message)
        return {"error": error_message}

def get_group_members(group_link, max_members=100):
    """Synchronous wrapper to run the async scraper."""
    # This ensures a new event loop is created if one isn't running
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_group_members_async(group_link, max_members))

# To run the session generator:
# In your local terminal, navigate to the `backend` folder and run:
# `python -c 'import asyncio; from app.telegram_scraper import generate_session_string; asyncio.run(generate_session_string())'`
