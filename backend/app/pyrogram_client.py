# backend/app/pyrogram_client.py
import os
import atexit
from pyrogram import Client

class PyrogramClientManager:
    """
    Manages a single, long-running Pyrogram Client instance for the application.
    """
    _client = None

    @classmethod
    def get_client(cls):
        """
        Returns the singleton Pyrogram client instance.
        Initializes the client if it doesn't exist.
        """
        if cls._client is None:
            api_id = os.environ.get('TELEGRAM_API_ID')
            api_hash = os.environ.get('TELEGRAM_API_HASH')
            session_string = os.environ.get('TELEGRAM_SESSION_STRING')

            if not all([api_id, api_hash, session_string]):
                raise ValueError("Telegram API credentials are not fully configured.")

            cls._client = Client(
                name="app_pyrogram_session",
                api_id=int(api_id),
                api_hash=api_hash,
                session_string=session_string,
                in_memory=True
            )
        return cls._client

    @classmethod
    def start_client(cls):
        """Starts the client if it's not already running."""
        client = cls.get_client()
        if not client.is_connected:
            print("🚀 Starting Pyrogram client...")
            client.start()
            print("✅ Pyrogram client started.")
            # Register the stop method to be called on application exit
            atexit.register(cls.stop_client)
        return client

    @classmethod
    def stop_client(cls):
        """Stops the client if it's running."""
        if cls._client and cls._client.is_connected:
            print("🛑 Stopping Pyrogram client...")
            cls._client.stop()
            print("🔌 Pyrogram client stopped.")

# Instantiate the manager to be imported by the app
pyrogram_manager = PyrogramClientManager()
