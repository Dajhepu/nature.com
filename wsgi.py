from app import create_app, db

app = create_app()

# Database tables yaratish (har safar startup'da)
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"⚠️ Database error: {e}")

if __name__ == '__main__':
    app.run()
