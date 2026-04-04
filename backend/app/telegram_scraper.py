# backend/app/telegram_scraper.py

import asyncio
from pyrogram.enums import UserStatus
from flask import current_app
from .pyrogram_client import pyrogram_manager

async def get_group_members_async(app, group_link, max_members=100):
    """
    Scrapes active members from a public Telegram group using an active Pyrogram client.
    """
    members_data = []
    count = 0
    print(f"Scraping group: {group_link}")
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
                current_app.logger.info(f"  [{count}/{max_members}] Found active user: {full_name} (Score: {score})")
    current_app.logger.info(f"Scraping complete for {group_link}. Found {len(members_data)} members.")
    return members_data

def get_group_members(group_link, max_members=100):
    """Synchronous wrapper to run the async scraper with the managed client."""
    with current_app.app_context():
        client = pyrogram_manager.get_client()
        async def _run():
            member_list = await get_group_members_async(client, group_link, max_members)
            return {"members": member_list}
        return asyncio.run(_run())


async def get_group_messages_async(app, group_link, limit=100):
    """
    Scrapes recent text messages from a public Telegram group using an active client.
    """
    messages_data = []
    current_app.logger.info(f"Scraping messages from {group_link}")
    async for message in app.get_chat_history(group_link, limit=limit):
        if message.text:
            messages_data.append({
                'message_id': message.id,
                'content': message.text,
                'sent_at': message.date
            })
    current_app.logger.info(f"Found {len(messages_data)} text messages in {group_link}.")
    return messages_data

def get_group_messages(group_link, limit=100):
    """Synchronous wrapper to run the async message scraper with the managed client."""
    with current_app.app_context():
        client = pyrogram_manager.get_client()
        async def _run():
            messages_list = await get_group_messages_async(client, group_link, limit)
            return {"messages": messages_list}
        return asyncio.run(_run())
