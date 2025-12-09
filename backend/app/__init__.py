from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from .config import Config
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app(config_class=Config):
    # Backend papkadan 2 marta yuqoriga chiqib, frontend/dist ga kirish
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    static_dir = os.path.join(base_dir, 'frontend', 'dist')

    app = Flask(__name__,
                static_folder=static_dir,
                static_url_path='/')
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    CORS(app)
    migrate.init_app(app, db)

    with app.app_context():
        from . import routes

    return app
