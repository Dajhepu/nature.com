from app import create_app

# Create Flask application for WSGI server
app = create_app()

if __name__ == '__main__':
    app.run()
