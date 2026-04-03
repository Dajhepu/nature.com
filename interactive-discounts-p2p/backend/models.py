import uuid
from datetime import datetime, timedelta
from .extensions import db # Import db from the extensions file

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    user_type = db.Column(db.String(50), nullable=False, default='consumer') # 'consumer', 'merchant', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Merchant(db.Model):
    __tablename__ = 'merchants'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    business_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    max_discount_percent = db.Column(db.Integer, default=30)
    subscription_status = db.Column(db.String(50), default='free') # 'free', 'premium'
    user = db.relationship('User', backref=db.backref('merchant', uselist=False))

class Offer(db.Model):
    __tablename__ = 'offers'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consumer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    merchant_id = db.Column(db.String(36), db.ForeignKey('merchants.id'), nullable=True) # Can be null initially
    original_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)
    final_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='pending') # 'pending', 'accepted', 'rejected', 'expired'
    expiration_time = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    certificate_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    consumer = db.relationship('User', backref='offers')
    merchant = db.relationship('Merchant', backref='offers')
