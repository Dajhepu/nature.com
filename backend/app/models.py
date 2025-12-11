from . import db, bcrypt
from sqlalchemy.sql import func


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    businesses = db.relationship('Business', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    business_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    leads = db.relationship('Lead', backref='business', lazy=True)
    campaigns = db.relationship('Campaign', backref='business', lazy=True)


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=True)
    activity_score = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(50), nullable=False) # e.g., 'telegram_group_a'
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    messages = db.relationship('Message', backref='lead', lazy=True)


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    messages = db.relationship('Message', backref='campaign', lazy=True)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True),
                          server_default=func.now())
    status = db.Column(db.String(20), default='sent')  # e.g., sent, opened, replied
