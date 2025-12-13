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
    message_templates = db.relationship('MessageTemplate', backref='business', lazy=True)


class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=True)
    activity_score = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(50), nullable=False) # e.g., 'telegram_group_a'
    status = db.Column(db.String(50), default='New', nullable=False)  # New, Contacted, Interested, Converted, etc.
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    messages = db.relationship('Message', backref='lead', lazy=True)


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    message_template_id = db.Column(db.Integer, db.ForeignKey('message_template.id'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    messages = db.relationship('Message', backref='campaign', lazy=True)
    message_template = db.relationship('MessageTemplate')


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True),
                          server_default=func.now())
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed


# =============================================
# Trend Analysis Models
# =============================================

class MonitoredGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_link = db.Column(db.String(255), unique=True, nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    last_scraped_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class WordFrequency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    frequency = db.Column(db.Integer, nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False, index=True)

    __table_args__ = (db.UniqueConstraint('word', 'date', 'business_id', name='_word_date_business_uc'),)

class Trend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    trend_score = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    sentiment = db.Column(db.String(20), default='neutral') # positive, negative, neutral
    summary = db.Column(db.Text, nullable=True)
