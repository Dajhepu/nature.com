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
# rq = RQ()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # CORS - API uchun
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    # rq.init_app(app)

    with app.app_context():
        from . import routes
        from . import models

    return app