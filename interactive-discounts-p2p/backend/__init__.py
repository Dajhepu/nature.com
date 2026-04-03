import os
from flask import Flask

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)

    # --- Database Configuration ---
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Initialize Extensions ---
    from .extensions import db, bcrypt
    db.init_app(app)
    bcrypt.init_app(app)

    # --- Register Blueprints (Routes) ---
    from .auth import auth as auth_blueprint
    from .offers import offers as offers_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(offers_blueprint)

    # --- Register Models ---
    from . import models

    return app
