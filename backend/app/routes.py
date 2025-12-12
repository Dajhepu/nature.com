from flask import request, jsonify, send_from_directory
from . import db
from .models import User, Business, Lead, Campaign, Message, MessageTemplate
from .telegram_service import send_telegram_message
from .telegram_scraper import get_group_members
from .tasks import send_message_job
from flask import current_app as app
import os

# =============================================
# HELPERS
# =============================================
def _get_current_user():
    """Mock user fetching. In a real app, this would use session or JWT."""
    return User.query.get(1)

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


@app.route('/api/campaigns/start', methods=['POST'])
def start_campaign():
    """Start a messaging campaign"""
    try:
        data = request.get_json()
        name = data.get('name', 'New Campaign')
        business_id = data.get('business_id')
        template_id = data.get('template_id')
        lead_ids = data.get('lead_ids')

        if not all([business_id, template_id, lead_ids]):
            return jsonify({"error": "Missing required fields"}), 400

        business = Business.query.get_or_404(business_id)
        template = db.session.get(MessageTemplate, template_id)
        if not template or template.business_id != business.id:
            return jsonify({"error": "MessageTemplate not found or access denied"}), 404

        new_campaign = Campaign(
            name=name,
            business_id=business.id,
            message_template_id=template.id
        )
        db.session.add(new_campaign)
        db.session.flush()

        messages_queued = 0
        for lead_id in lead_ids:
            lead = db.session.get(Lead, lead_id)
            if lead and lead.business_id == business.id:
                new_message = Message(
                    campaign_id=new_campaign.id,
                    lead_id=lead.id,
                    status='queued'
                )
                db.session.add(new_message)
                db.session.flush()  # Ensure the message gets an ID
                send_message_job.queue(new_message.id)
                messages_queued += 1

        db.session.commit()

        return jsonify({
            "message": f"Campaign '{name}' started and {messages_queued} messages have been queued.",
            "campaign_id": new_campaign.id
        }), 201
    except Exception as e:
        db.session.rollback()
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

# =============================================
# MESSAGE TEMPLATE ROUTES
# =============================================

@app.route('/api/business/<int:business_id>/templates', methods=['POST'])
def create_template(business_id):
    """Create a new message template"""
    try:
        data = request.get_json()
        name = data.get('name')
        content = data.get('content')

        if not all([name, content]):
            return jsonify({"error": "Missing 'name' or 'content'"}), 400

        business = Business.query.get_or_404(business_id)

        new_template = MessageTemplate(
            name=name,
            content=content,
            business_id=business.id
        )
        db.session.add(new_template)
        db.session.commit()

        return jsonify({
            "message": "Template created successfully",
            "template": {
                "id": new_template.id,
                "name": new_template.name,
                "content": new_template.content
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/business/<int:business_id>/templates', methods=['GET'])
def get_templates(business_id):
    """Get all message templates for a business"""
    try:
        business = Business.query.get_or_404(business_id)
        templates = [
            {"id": t.id, "name": t.name, "content": t.content}
            for t in business.message_templates
        ]
        return jsonify(templates), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """Update a message template"""
    try:
        data = request.get_json()
        template = db.session.get(MessageTemplate, template_id)
        if not template:
            return jsonify({"error": "Template not found"}), 404

        current_user = _get_current_user()
        business = Business.query.get_or_404(template.business_id)
        if business.user_id != current_user.id:
            return jsonify({"error": "Access denied"}), 403

        template.name = data.get('name', template.name)
        template.content = data.get('content', template.content)
        db.session.commit()

        return jsonify({"message": "Template updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a message template"""
    try:
        template = db.session.get(MessageTemplate, template_id)
        if not template:
            return jsonify({"error": "Template not found"}), 404

        current_user = _get_current_user()
        business = Business.query.get_or_404(template.business_id)
        if business.user_id != current_user.id:
            return jsonify({"error": "Access denied"}), 403

        db.session.delete(template)
        db.session.commit()

        return jsonify({"message": "Template deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


import openai

# =============================================
# AI ROUTES
# =============================================

@app.route('/api/ai/generate_template', methods=['POST'])
def generate_ai_template():
    """Generate message templates using OpenAI"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        if not app.config['OPENAI_API_KEY']:
            return jsonify({"error": "OpenAI API key is not configured"}), 500

        client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])

        system_prompt = (
            "You are an expert copywriter specializing in Telegram marketing. "
            "Generate three short, engaging, and professional message templates based on the user's prompt. "
            "The messages should be in Uzbek. Each message should be distinct in tone and approach (e.g., one formal, one friendly, one direct). "
            "Return the response as a simple list of strings."
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            n=3,
            temperature=0.7,
        )

        suggestions = [choice.message.content.strip() for choice in response.choices]

        return jsonify({"suggestions": suggestions}), 200
    except Exception as e:
        return jsonify({"error": f"Error communicating with OpenAI: {str(e)}"}), 500


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
