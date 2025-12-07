from flask import Blueprint, request, jsonify, render_template
from .models import User
from .extensions import db, bcrypt

auth = Blueprint('auth', __name__) # Removed url_prefix for HTML routes

# --- HTML Routes ---
@auth.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@auth.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# --- API Routes ---
@auth.route('/api/auth/register', methods=['POST'])
def register():
    """Registers a new consumer user."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered.'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(email=email, password_hash=hashed_password, user_type='consumer')

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully.'}), 201

@auth.route('/api/auth/login', methods=['POST'])
def login():
    """Logs in a user."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        # In a real app, you would return a JWT token here
        return jsonify({'message': 'Login successful.', 'user_id': user.id}), 200

    return jsonify({'error': 'Invalid credentials.'}), 401
