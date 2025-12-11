from flask import request, jsonify, send_from_directory
from . import db
from .models import User, Business, Lead, Campaign, Message
from .scraper import find_dissatisfied_customers
from .telegram_service import send_telegram_message
from .telegram_scraper import get_group_members
from flask import current_app as app
import os

# =============================================
# API ROUTES (BIRINCHI!)
# =============================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "ok", "message": "Backend is running"}), 200


@app.route('/api/register', methods=['POST'])
def register():
    """User registration"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Foydalanuvchiga tegishli biznesni qidirish
            business = Business.query.filter_by(user_id=user.id).first()
            business_data = None
            if business:
                business_data = {"id": business.id, "name": business.name}

            return jsonify({
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username
                },
                "business": business_data  # Biznes ma'lumotlarini qo'shish
            }), 200

        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/business', methods=['POST'])
def add_business():
    """Add business"""
    try:
        data = request.get_json()
        name = data.get('name')
        business_type = data.get('business_type')
        location = data.get('location')
        status = data.get('status')
        user_id = data.get('user_id')

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

        return jsonify({"message": "Business added successfully", "business_id": new_business.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/business/<int:business_id>/generate_leads', methods=['POST'])
def generate_leads(business_id):
    """Generate leads"""
    try:
        business = Business.query.get_or_404(business_id)

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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/business/<int:business_id>/leads', methods=['GET'])
def get_leads(business_id):
    """Get leads"""
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    """Create campaign"""
    try:
        data = request.get_json()
        name = data.get('name')
        business_id = data.get('business_id')

        if not all([name, business_id]):
            return jsonify({"error": "Missing required fields"}), 400

        business = Business.query.get_or_404(business_id)

        new_campaign = Campaign(name=name, business_id=business.id)
        db.session.add(new_campaign)
        db.session.commit()

        # for lead in business.leads:
        #     message_text = (
        #         f"Yangi kampaniya: '{name}'\n"
        #         f"Potensial mijoz: {lead.customer_name}\n"
        #         f"Manba: {lead.source}\n"
        #         f"Izoh: {lead.review_text}"
        #     )
        #     send_telegram_message(chat_id='5073336035', text=message_text)

        #     new_message = Message(
        #         campaign_id=new_campaign.id,
        #         lead_id=lead.id,
        #         subject=f"Telegram message for {lead.customer_name}",
        #         body=message_text,
        #         status="sent_telegram"
        #     )
        #     db.session.add(new_message)

        db.session.commit()

        return jsonify({
            "message": f"Campaign '{name}' created and initiated for {business.name}",
            "campaign_id": new_campaign.id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/campaigns/<int:campaign_id>/metrics', methods=['GET'])
def get_campaign_metrics(campaign_id):
    """Get campaign metrics"""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)

        total_leads = len(campaign.messages)
        conversion_rate = 0.15
        roi = 2.5

        return jsonify({
            "campaign_name": campaign.name,
            "total_leads": total_leads,
            "conversion_rate": conversion_rate,
            "roi": roi,
            "guarantee_progress": (total_leads * conversion_rate) / 15 * 100
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/telegram/scrape_group', methods=['POST'])
def scrape_telegram_group():
    """Scrapes members from a Telegram group and saves them as Leads."""
    try:
        data = request.get_json()
        group_link = data.get('group_link')
        business_id = data.get('business_id', 1) # Standart business_id=1

        if not group_link:
            return jsonify({"error": "Missing 'group_link' in request"}), 400

        print(f"🚀 Starting Telegram group scraping for: {group_link}")
        result = get_group_members(group_link, max_members=100)

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        members = result.get("members", [])
        if not members:
            return jsonify({"message": "No active members found.", "saved_leads": 0}), 200

        saved_count = 0
        for member in members:
            customer_name = member['username'] or f"{member['first_name'] or ''} {member['last_name'] or ''}".strip()

            # Agar mavjud bo'lsa, o'tkazib yuborish
            existing_lead = Lead.query.filter_by(
                customer_name=customer_name,
                business_id=business_id
            ).first()

            if not existing_lead:
                new_lead = Lead(
                    customer_name=customer_name,
                    source='Telegram',
                    review_text=f"User ID: {member['user_id']}", # Qo'shimcha ma'lumot
                    sentiment='neutral',
                    business_id=business_id,
                )
                db.session.add(new_lead)
                saved_count += 1

        db.session.commit()

        return jsonify({
            "message": f"Successfully scraped {len(members)} members and saved {saved_count} new leads.",
            "saved_leads": saved_count
        }), 200

    except Exception as e:
        print(f"❌ Error in scrape_telegram_group endpoint: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================
# FRONTEND ROUTES (OXIRIDA!)
# =============================================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve frontend files"""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dist_dir = os.path.join(base_dir, 'frontend', 'dist')

    # Agar path API ga tegishli bo'lsa, 404 qaytarish
    if path.startswith('api/'):
        return jsonify({"error": "API endpoint not found"}), 404

    if path != "" and os.path.exists(os.path.join(dist_dir, path)):
        return send_from_directory(dist_dir, path)
    else:
        index_path = os.path.join(dist_dir, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(dist_dir, 'index.html')
        else:
            return jsonify({"error": "Frontend not built"}), 404
