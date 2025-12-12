import os
from dotenv import load_dotenv

load_dotenv()

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))
# Construct the absolute path to the instance folder
instance_dir = os.path.join(basedir, '..', 'instance')
# Ensure the instance directory exists
os.makedirs(instance_dir, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key'

    # Railway'da Postgres, local'da SQLite
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        # Railway'ning eski formatini yangilash
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///' + os.path.join(instance_dir, 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    INSTAGRAM_SESSIONID = os.environ.get('INSTAGRAM_SESSIONID')

    # Flask-RQ2 configuration
    RQ_REDIS_URL = os.environ.get('RQ_REDIS_URL') or 'redis://localhost:6379/0'
    RQ_ASYNC = True

    # Google Gemini API Key
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
