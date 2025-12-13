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
            print(f"✅ Connection successful. Scraping group: {group_link}")

            try:
                # Iterate through members of the specified group
                async for member in app.get_chat_members(group_link):
                    if count >= max_members:
                        break

                    user = member.user
                    if not user.is_bot and not user.is_deleted:
                        # Filter for users who were recently active
                        # Calculate activity score
                        score = 0
                        if user.status == UserStatus.ONLINE:
                            score += 50
                        elif user.status == UserStatus.RECENTLY:
                            score += 40

                        if user.photo:
                            score += 20
                        if getattr(user, 'bio', None):
                            score += 10

                        # Only include users with a minimum score
                        if score >= 40:
                            # Construct full_name safely
                            full_name = (user.first_name or "") + " " + (user.last_name or "")
                            full_name = full_name.strip()
                            if not full_name:
                                full_name = user.username or f"User_{user.id}"

                            members_data.append({
                                'user_id': user.id,
                                'full_name': full_name,
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                'username': user.username,
                                'activity_score': score,
                                'status': user.status.name if user.status else "UNKNOWN"
                            })
                            count += 1
                            print(f"  [{count}/{max_members}] Found active user: {full_name} (Score: {score})")

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

async def get_group_messages_async(group_link, limit=100):
    """
    Scrapes recent text messages from a public Telegram group using Pyrogram.
    """
    if not all([API_ID, API_HASH, SESSION_STRING]):
        error_message = "❌ Telegram credentials are not fully configured."
        print(error_message)
        return {"error": error_message}

    print(f"--- 📜 Starting Message Scraper for {group_link} 📜 ---")

    try:
        app = Client(
            name="pyrogram_session_messages",
            api_id=int(API_ID),
            api_hash=API_HASH,
            session_string=SESSION_STRING,
            in_memory=True
        )

        messages_data = []
        async with app:
            print("✅ Connection for message scraping successful.")
            try:
                async for message in app.get_chat_history(group_link, limit=limit):
                    if message.text: # Only process messages with text content
                        messages_data.append({
                            'message_id': message.id,
                            'content': message.text,
                            'sent_at': message.date
                        })
                print(f"✅ Found {len(messages_data)} text messages.")
            except Exception as e:
                error_message = f"❌ Could not access messages for group '{group_link}'. Details: {e}"
                print(error_message)
                return {"error": error_message}

        return {"messages": messages_data}

    except Exception as e:
        error_message = f"❌ An unexpected error occurred during message scraping client initialization: {e}"
        print(error_message)
        return {"error": error_message}

def get_group_messages(group_link, limit=100):
    """Synchronous wrapper to run the async Pyrogram message scraper."""
    return asyncio.run(get_group_messages_async(group_link, limit))
