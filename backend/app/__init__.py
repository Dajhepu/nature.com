from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
# from flask_rq2 import RQ
from .config import Config
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
import nest_asyncio
# rq = RQ()

def create_app(config_class=Config):
    nest_asyncio.apply()
    app = Flask(__name__)
    app.config.from_object(config_class)

    # CORS - API uchun
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    # rq.init_app(app)

    # Pyrogram Client ni ishga tushirish
    try:
        from .pyrogram_client import pyrogram_manager
        pyrogram_manager.start_client()
        print("Pyrogram client integrated and started.")
    except ValueError as e:
        print(f"WARNING: Pyrogram client not started. {e}")
    except Exception as e:
        print(f"An unexpected error occurred while starting Pyrogram client: {e}")


    with app.app_context():
        from . import routes
        from . import models

    return app