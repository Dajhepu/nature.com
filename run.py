import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/backend')

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
