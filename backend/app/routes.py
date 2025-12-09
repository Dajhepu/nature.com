from flask import request, jsonify, send_from_directory
from . import db
from .models import User, Business, Lead, Campaign, Message
from .scraper import find_dissatisfied_customers
from .telegram_service import send_telegram_message
from . import instagram_scraper
from flask import current_app as app
import asyncio
import os

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/register', methods=['POST'])
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


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        return jsonify({"message": "Login successful"}), 200

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/api/business', methods=['POST'])
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


@app.route('/api/business/<int:business_id>/generate_leads', methods=['POST'])
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


@app.route('/api/campaigns', methods=['POST'])
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

    async def _send_messages():
        for lead in business.leads:
            message_text = (
                f"Yangi kampaniya: '{name}'\n"
                f"Potensial mijoz: {lead.customer_name}\n"
                f"Manba: {lead.source}\n"
                f"Izoh: {lead.review_text}"
            )
            await send_telegram_message(chat_id='5073336035', text=message_text)

            new_message = Message(
                campaign_id=new_campaign.id,
                lead_id=lead.id,
                subject=f"Telegram message for {lead.customer_name}",
                body=message_text,
                status="sent_telegram"
            )
            db.session.add(new_message)

    asyncio.run(_send_messages())
    db.session.commit()

    return jsonify({
        "message": f"Campaign '{name}' created and initiated for {business.name}"
    }), 201


@app.route('/api/scrape_instagram', methods=['POST'])
def scrape_instagram():
    data = request.get_json()
    soha = data.get('soha')
    business_id = data.get('business_id')

    if not all([soha, business_id]):
        return jsonify({"error": "Missing soha or business_id"}), 400

    async def _scrape():
        # 1. Soha bo'yicha foydalanuvchilarni topish
        usernames = await instagram_scraper.search_posts_by_hashtag(soha, max_posts=10)
        if not usernames:
            return []

        all_comments_data = []
        # 2. Har bir foydalanuvchining ma'lumotlarini yig'ish
        for username in usernames:
            profile = await instagram_scraper.get_user_profile(username)
            if not profile or profile.get('is_private'):
                continue

            user_id = profile['user_id']
            posts = await instagram_scraper.get_user_posts(user_id, max_posts=5)

            for post in posts:
                comments = await instagram_scraper.get_post_comments(post['shortcode'], max_comments=10)
                all_comments_data.extend(comments)

        return all_comments_data

    comments_data = asyncio.run(_scrape())

    if not comments_data:
        return jsonify({"message": f"No comments found for soha '{soha}'."}), 200

    for comment in comments_data:
        # Duplikatlarni oldini olish
        existing_lead = Lead.query.filter_by(
            customer_name=comment['author_username'],
            review_text=comment['text'],
            business_id=business_id
        ).first()

        if not existing_lead:
            new_lead = Lead(
                customer_name=comment['author_username'],
                source='Instagram',
                review_text=comment['text'],
                sentiment='neutral',
                business_id=business_id,
            )
            db.session.add(new_lead)

    db.session.commit()

    return jsonify({"message": f"Scraped {len(comments_data)} comments for soha '{soha}'."}), 200


@app.route('/api/business/<int:business_id>/leads', methods=['GET'])
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


@app.route('/api/campaigns/<int:campaign_id>/metrics', methods=['GET'])
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


@app.route('/health')
def health():
    import os
    return jsonify({
        "status": "ok",
        "cwd": os.getcwd(),
        "static_folder": app.static_folder,
        "static_exists": os.path.exists(app.static_folder) if app.static_folder else False
    })
