from flask import request, jsonify
from . import db
from .models import User, Business, Lead, Campaign, Message
from .scraper import find_dissatisfied_customers
from .email_service import send_email
from flask import current_app as app


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(username=username).first() or \
       User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        return jsonify({"message": "Login successful"}), 200

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/business', methods=['POST'])
def add_business():
    data = request.get_json()
    name = data.get('name')
    business_type = data.get('business_type')
    location = data.get('location')
    status = data.get('status')
    user_id = data.get('user_id')  # In a real app, get this from the session/token

    if not all([name, business_type, location, user_id]):
        return jsonify({"error": "Missing required fields"}), 400

    new_business = Business(
        name=name,
        business_type=business_type,
        location=location,
        status=status,
        user_id=user_id
    )
    db.session.add(new_business)
    db.session.commit()

    return jsonify({"message": "Business added successfully"}), 201


@app.route('/business/<int:business_id>/generate_leads', methods=['POST'])
def generate_leads(business_id):
    business = Business.query.get_or_404(business_id)

    # In a real app, you might have more complex logic to determine
    # the search parameters for the scraper
    dissatisfied_customers = find_dissatisfied_customers(
        business.business_type, business.location
    )

    for customer_data in dissatisfied_customers:
        new_lead = Lead(
            customer_name=customer_data['customer_name'],
            source=customer_data['source'],
            review_text=customer_data['review_text'],
            sentiment=customer_data['sentiment'],
            business_id=business.id
        )
        db.session.add(new_lead)

    db.session.commit()

    return jsonify({
        "message": f"{len(dissatisfied_customers)} leads generated for {business.name}"
    }), 201


@app.route('/campaigns', methods=['POST'])
def create_campaign():
    data = request.get_json()
    name = data.get('name')
    business_id = data.get('business_id')

    if not all([name, business_id]):
        return jsonify({"error": "Missing required fields"}), 400

    business = Business.query.get_or_404(business_id)

    new_campaign = Campaign(name=name, business_id=business.id)
    db.session.add(new_campaign)
    db.session.commit()

    # Simulate sending the first email to all leads
    for lead in business.leads:
        subject = f"A special offer for {lead.customer_name}"
        body = f"Hi {lead.customer_name}, we saw your review and wanted to offer you a discount."

        # In a real app, you would get the lead's email from the database
        to_email = f"{lead.customer_name.replace(' ', '.').lower()}@example.com"

        send_email(to_email, subject, body)

        new_message = Message(
            campaign_id=new_campaign.id,
            lead_id=lead.id,
            subject=subject,
            body=body
        )
        db.session.add(new_message)

    db.session.commit()

    return jsonify({
        "message": f"Campaign '{name}' created and initiated for {business.name}"
    }), 201


@app.route('/business/<int:business_id>/leads', methods=['GET'])
def get_leads(business_id):
    business = Business.query.get_or_404(business_id)
    leads = [
        {
            "id": lead.id,
            "customer_name": lead.customer_name,
            "review_text": lead.review_text,
            "sentiment": lead.sentiment,
        }
        for lead in business.leads
    ]
    return jsonify(leads), 200


@app.route('/campaigns/<int:campaign_id>/metrics', methods=['GET'])
def get_campaign_metrics(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)

    total_leads = len(campaign.messages)
    # Mock conversion rate and ROI for now
    conversion_rate = 0.15  # 15%
    roi = 2.5  # 250%

    return jsonify({
        "campaign_name": campaign.name,
        "total_leads": total_leads,
        "conversion_rate": conversion_rate,
        "roi": roi,
        "guarantee_progress": (total_leads * conversion_rate) / 15 * 100
    }), 200
