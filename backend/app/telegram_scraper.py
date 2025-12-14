# backend/app/telegram_scraper.py

import asyncio
from pyrogram.enums import UserStatus
from flask import current_app
from .pyrogram_client import get_pyrogram_client

async def get_group_members_async(group_link, max_members=100):
    """
    Scrapes active members from a public Telegram group using the shared Pyrogram client.
    """
    print("--- 🕵️ Starting Pyrogram Scraper 🕵️ ---")

    try:
        app = get_pyrogram_client()
        members_data = []
        count = 0

        await app.start()
        print(f"✅ Connection successful. Scraping group: {group_link}")

        try:
            async for member in app.get_chat_members(group_link):
                if count >= max_members:
                    break
                user = member.user
                if not user.is_bot and not user.is_deleted:
                    score = 0
                    if user.status == UserStatus.ONLINE: score += 50
                    elif user.status == UserStatus.RECENTLY: score += 40
                    if user.photo: score += 20
                    if getattr(user, 'bio', None): score += 10

                    if score >= 40:
                        full_name = ((user.first_name or "") + " " + (user.last_name or "")).strip() or user.username or f"User_{user.id}"
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
            error_message = f"❌ Could not access group '{group_link}'. Details: {e}"
            print(error_message)
            return {"error": error_message}
        finally:
            await app.stop()

        print(f"✅ Scraping complete. Total active members found: {len(members_data)}")
        return {"members": members_data}

    except Exception as e:
        error_message = f"❌ An unexpected error occurred: {e}"
        print(error_message)
        return {"error": error_message}

def get_group_members(group_link, max_members=100):
    """Synchronous wrapper to run the async Pyrogram scraper."""
    with current_app.app_context():
        return asyncio.run(get_group_members_async(group_link, max_members))


async def get_group_messages_async(group_link, limit=100):
    """
    Scrapes recent text messages from a public Telegram group using the shared client.
    """
    print(f"--- 📜 Starting Message Scraper for {group_link} 📜 ---")

    try:
        app = get_pyrogram_client()
        messages_data = []

        await app.start()
        print("✅ Connection for message scraping successful.")
        try:
            async for message in app.get_chat_history(group_link, limit=limit):
                if message.text:
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
        finally:
            await app.stop()

        return {"messages": messages_data}

    except Exception as e:
        error_message = f"❌ An unexpected error occurred: {e}"
        print(error_message)
        return {"error": error_message}

def get_group_messages(group_link, limit=100):
    """Synchronous wrapper to run the async Pyrogram message scraper."""
    with current_app.app_context():
        return asyncio.run(get_group_messages_async(group_link, limit))
