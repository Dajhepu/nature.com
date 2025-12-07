from backend import create_app
from backend.extensions import db

# Create the Flask application instance
app = create_app()

# --- Main execution ---
if __name__ == '__main__':
    with app.app_context():
        # Create the database tables if they don't exist
        db.create_all()
        print("Database tables created successfully.")

    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
