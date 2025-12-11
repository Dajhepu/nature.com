# backend/app/telegram_scraper.py

import os
import asyncio
from pyrogram import Client
from pyrogram.enums import UserStatus

API_ID = os.environ.get('TELEGRAM_API_ID')
API_HASH = os.environ.get('TELEGRAM_API_HASH')
SESSION_STRING = os.environ.get('TELEGRAM_SESSION_STRING')

async def get_group_members_async(group_link, max_members=100):
    """
    Scrapes active members from a public Telegram group using Pyrogram.
    """
    if not all([API_ID, API_HASH, SESSION_STRING]):
        error_message = "❌ Telegram credentials (API_ID, API_HASH, SESSION_STRING) are not fully configured."
        print(error_message)
        return {"error": error_message}

    print("--- 🕵️ Starting Pyrogram Scraper 🕵️ ---")

    try:
        # Initialize the Pyrogram Client with the session string
        app = Client(
            name="pyrogram_session",
            api_id=int(API_ID),
            api_hash=API_HASH,
            session_string=SESSION_STRING,
            in_memory=True # Use in-memory storage to avoid creating a .session file
        )

        members_data = []
        count = 0

        async with app:
            # Sanitize the group link to ensure it starts with '@'
            username = group_link.split('/')[-1]
            if not username.startswith('@'):
                username = '@' + username
            print(f"✅ Connection successful. Scraping username: {username}")

            try:
                # Iterate through members of the specified group
                async for member in app.get_chat_members(username):
                    if count >= max_members:
                        break

                    user = member.user
                    if not user.is_bot and not user.is_deleted:
                        # Filter for users who were recently active
                        if user.status in [UserStatus.ONLINE, UserStatus.RECENTLY]:
                            members_data.append({
                                'user_id': user.id,
                                'username': user.username,
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                'status': user.status.name if user.status else "UNKNOWN"
                            })
                            count += 1
                            print(f"  [{count}/{max_members}] Found active user: {user.username or user.first_name}")

            except Exception as e:
                # Handle cases where the group link is invalid or inaccessible
                error_message = f"❌ Could not access group '{group_link}'. It might be private, invalid, or you may not be a member. Details: {e}"
                print(error_message)
                return {"error": error_message}

        print(f"✅ Scraping complete. Total active members found: {len(members_data)}")
        return {"members": members_data}

    except Exception as e:
        error_message = f"❌ An unexpected error occurred during client initialization: {e}"
        print(error_message)
        return {"error": error_message}

def get_group_members(group_link, max_members=100):
    """Synchronous wrapper to run the async Pyrogram scraper."""
    return asyncio.run(get_group_members_async(group_link, max_members))
