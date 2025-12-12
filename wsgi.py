from app import create_app, db
from app.models import User, Business

app = create_app()

# Database tables yaratish (har safar startup'da)
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created/verified")

        # Create a default user and business if they don't exist
        if not User.query.get(1):
            print("Creating default user...")
            default_user = User(id=1, username='default_user', email='default@example.com')
            default_user.set_password('password')
            db.session.add(default_user)
            db.session.commit()

        if not Business.query.get(1):
            print("Creating default business...")
            default_business = Business(
                id=1,
                name='Default Business',
                business_type='General',
                location='Online',
                user_id=1
            )
            db.session.add(default_business)
            db.session.commit()

    except Exception as e:
        print(f"⚠️ Database error during initialization: {e}")

if __name__ == '__main__':
    app.run()
