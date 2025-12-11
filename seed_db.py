
from backend.app import create_app, db
from backend.app.models import User, Business

def seed_database():
    """Seeds the database with a test user and business."""
    app = create_app()
    with app.app_context():
        # Check if user with id=1 already exists
        if not User.query.get(1):
            print("Creating test user...")
            test_user = User(id=1, username='testuser', email='test@example.com')
            test_user.set_password('password')
            db.session.add(test_user)

        # Check if business with id=1 already exists
        if not Business.query.get(1):
            print("Creating test business...")
            test_business = Business(
                id=1,
                name='Test Business',
                business_type='Test Type',
                location='Test Location',
                user_id=1
            )
            db.session.add(test_business)

        db.session.commit()
        print("Database seeded successfully.")

if __name__ == '__main__':
    seed_database()
