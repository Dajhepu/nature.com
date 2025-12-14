import os
from pyrogram import Client
from flask import g

# --- Environment Variables ---
API_ID = os.environ.get('TELEGRAM_API_ID')
API_HASH = os.environ.get('TELEGRAM_API_HASH')
SESSION_STRING = os.environ.get('TELEGRAM_SESSION_STRING')


def get_pyrogram_client():
    """
    Initializes and returns a Pyrogram Client.
    Stores the client in the Flask application context (g) to ensure it's
    a singleton per request, preventing multiple initializations.
    """
    if 'pyrogram_client' not in g:
        if not all([API_ID, API_HASH, SESSION_STRING]):
            raise ValueError("Telegram API credentials (API_ID, API_HASH, SESSION_STRING) are not configured.")

        # Create and store the client
        client = Client(
            name="shared_pyrogram_session",
            api_id=int(API_ID),
            api_hash=API_HASH,
            session_string=SESSION_STRING,
            in_memory=True  # Use in-memory storage for server environments
        )
        g.pyrogram_client = client

    return g.pyrogram_client
