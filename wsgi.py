import sys
import os

# 'backend' papkasini Python yo'liga qo'shish
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import create_app

# WSGI server uchun Flask ilovasini yaratish
app = create_app()
