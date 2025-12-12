from flask import request, jsonify, send_from_directory
from . import db
from .models import User, Business, Lead, Campaign, Message
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




@app.route('/api/business/<int:business_id>/generate_leads', methods=['POST'])
def generate_leads(business_id):
    """Generate mock leads"""
    try:
        business = Business.query.get_or_404(business_id)

        mock_leads_data = [
            {'full_name': 'Mock Lead 1', 'telegram_user_id': 9990001, 'username': 'mocklead1', 'activity_score': 75, 'source': 'mock_generation'},
            {'full_name': 'Mock Lead 2', 'telegram_user_id': 9990002, 'username': 'mocklead2', 'activity_score': 50, 'source': 'mock_generation'},
        ]

        saved_count = 0
        for lead_data in mock_leads_data:
            # Check if a lead with this telegram_user_id already exists for this business
            existing_lead = Lead.query.filter_by(
                telegram_user_id=lead_data['telegram_user_id'],
                business_id=business_id
            ).first()

            if not existing_lead:
                new_lead = Lead(
                    full_name=lead_data['full_name'],
                    telegram_user_id=lead_data['telegram_user_id'],
                    username=lead_data['username'],
                    activity_score=lead_data['activity_score'],
                    source=lead_data['source'],
                    business_id=business_id,
                )
                db.session.add(new_lead)
                saved_count += 1

        db.session.commit()

        return jsonify({
            "message": f"Successfully generated and saved {saved_count} new mock leads for {business.name}."
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/business/<int:business_id>/leads', methods=['GET'])
def get_leads(business_id):
    """Get leads for a business"""
    try:
        business = Business.query.get_or_404(business_id)
        leads = [
            {
                "id": lead.id,
                "full_name": lead.full_name,
                "username": lead.username,
                "activity_score": lead.activity_score,
                "source": lead.source,
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
        #         f"Potensial mijoz: {lead.full_name}\n"
        #         f"Manba: {lead.source}\n"
        #         f"Izoh: {lead.review_text}"
        #     )
        #     send_telegram_message(chat_id='5073336035', text=message_text)

        #     new_message = Message(
        #         campaign_id=new_campaign.id,
        #         lead_id=lead.id,
        #         subject=f"Telegram message for {lead.full_name}",
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
    """Scrapes members from a Telegram group, filters them, and saves them as Leads."""
    try:
        data = request.get_json()
        group_link = data.get('group_link')
        business_id = data.get('business_id')

        if not group_link or not business_id:
            return jsonify({"error": "Missing 'group_link' or 'business_id' in request"}), 400

        business = Business.query.get(business_id)
        if not business:
            return jsonify({"error": f"Business with id {business_id} not found."}), 404

        print(f"🚀 Starting Telegram group scraping for: {group_link}")
        result = get_group_members(group_link, max_members=100)

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        members = result.get("members", [])
        if not members:
            return jsonify({"message": "No active members found meeting the criteria.", "saved_leads": 0}), 200

        saved_count = 0
        for member in members:
            existing_lead = Lead.query.filter_by(
                telegram_user_id=member['user_id'],
                business_id=business_id
            ).first()

            if not existing_lead:
                new_lead = Lead(
                    full_name=member['full_name'],
                    telegram_user_id=member['user_id'],
                    username=member['username'],
                    activity_score=member['activity_score'],
                    source=group_link,
                    business_id=business_id,
                )
                db.session.add(new_lead)
                saved_count += 1

        db.session.commit()

        return jsonify({
            "message": f"Successfully scraped {len(members)} members and saved {saved_count} new leads.",
            "saved_leads": saved_count
        }), 201

    except Exception as e:
        print(f"❌ Error in scrape_telegram_group endpoint: {e}")
        db.session.rollback()
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
