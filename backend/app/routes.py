from flask import request, jsonify, send_from_directory
from . import db
from .models import User, Business, Lead, Campaign, Message, MessageTemplate, MonitoredGroup, WordFrequency, Trend
from .telegram_service import send_telegram_message
from .telegram_scraper import get_group_members, get_group_messages
from .tasks import send_message_job
from .text_processor import get_word_frequencies
from .trend_analyzer import analyze_trends_for_business
from flask import current_app as app
import os
import traceback
from groq import Groq
from datetime import date, datetime

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


# =============================================
# AI ROUTES
# =============================================

@app.route('/api/ai/generate_template', methods=['POST'])
def generate_ai_template():
    """Generate message templates using Groq"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        groq_api_key = app.config.get('GROQ_API_KEY')
        if not groq_api_key:
            return jsonify({"error": "The AI feature has not been configured by the administrator. (GROQ_API_KEY is not set)"}), 500

        client = Groq(api_key=groq_api_key)

        system_prompt = (
            "You are an expert copywriter specializing in Telegram marketing. "
            "Generate three short, engaging, and professional message templates based on the user's prompt. "
            "The messages should be in Uzbek. Each message should be distinct in tone and approach (e.g., one formal, one friendly, one direct). "
            "Return the response as a simple list of strings, separated by '---'."
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant", # A fast and capable model from Groq
        )

        response_content = chat_completion.choices[0].message.content

        # Split the response into three suggestions
        suggestions = [s.strip() for s in response_content.split('---')]

        return jsonify({"suggestions": suggestions}), 200
    except Exception as e:
        print("❌ An exception occurred in generate_ai_template:")
        traceback.print_exc() # Prints the full traceback to the log
        return jsonify({"error": f"An internal error occurred while communicating with the AI service: {str(e)}"}), 500


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
# TREND ANALYSIS ROUTES
# =============================================

@app.route('/api/business/<int:business_id>/monitored_groups', methods=['POST'])
def add_monitored_group(business_id):
    """Kuzatish uchun yangi guruh qo'shadi"""
    data = request.get_json()
    group_link = data.get('group_link')

    if not group_link:
        return jsonify({"error": "Group link is required"}), 400

    # Check if business exists
    business = Business.query.get_or_404(business_id)

    # Check if group link is already monitored for this business
    existing = MonitoredGroup.query.filter_by(business_id=business_id, group_link=group_link).first()
    if existing:
        return jsonify({"error": "This group is already being monitored."}), 409

    new_group = MonitoredGroup(
        group_link=group_link,
        business_id=business_id
    )
    db.session.add(new_group)
    db.session.commit()

    return jsonify({
        "message": "Group added for monitoring.",
        "group": {"id": new_group.id, "group_link": new_group.group_link}
    }), 201

@app.route('/api/business/<int:business_id>/monitored_groups', methods=['GET'])
def get_monitored_groups(business_id):
    """Biznes uchun barcha kuzatilayotgan guruhlarni oladi"""
    groups = MonitoredGroup.query.filter_by(business_id=business_id).all()
    return jsonify([{"id": g.id, "group_link": g.group_link} for g in groups]), 200

@app.route('/api/business/<int:business_id>/trends', methods=['GET'])
def get_trends(business_id):
    """Eng so'nggi trendlarni oladi"""
    today = date.today()
    trends = Trend.query.filter_by(business_id=business_id, date=today).order_by(Trend.trend_score.desc()).all()

    return jsonify([
        {"word": t.word, "trend_score": round(t.trend_score, 2)}
        for t in trends
    ]), 200

@app.route('/api/business/<int:business_id>/trigger_analysis', methods=['POST'])
def trigger_analysis(business_id):
    """Trend tahlilini qo'lda ishga tushiradi"""
    try:
        # 1. Guruhlarni topish
        groups = MonitoredGroup.query.filter_by(business_id=business_id).all()
        if not groups:
            return jsonify({"message": "No groups are being monitored for this business."}), 200

        all_messages = []
        # 2. Har bir guruhdan xabarlarni yig'ish
        for group in groups:
            result = get_group_messages(group.group_link, limit=200) # Oxirgi 200 ta xabar
            if "error" in result:
                # Agar biror guruhda xato bo'lsa, davom etamiz
                print(f"Warning: Could not scrape messages from {group.group_link}. Error: {result['error']}")
                continue

            # TODO: Xabarlarni GroupMessage jadvaliga saqlash mantiqi bu yerga qo'shilishi mumkin

            all_messages.extend([msg['content'] for msg in result.get("messages", [])])
            group.last_scraped_at = datetime.utcnow()

        if not all_messages:
            return jsonify({"message": "No new messages found to analyze."}), 200

        # 3. So'zlar chastotasini hisoblash
        frequencies = get_word_frequencies(all_messages)

        # 4. Chastotalarni ma'lumotlar bazasiga saqlash
        today = date.today()
        for word, freq in frequencies.items():
            wf = WordFrequency.query.filter_by(business_id=business_id, word=word, date=today).first()
            if wf:
                wf.frequency += freq
            else:
                wf = WordFrequency(
                    word=word,
                    frequency=freq,
                    date=today,
                    business_id=business_id
                )
                db.session.add(wf)

        db.session.commit()

        # 5. Trendlarni tahlil qilish
        analyze_trends_for_business(business_id, today)

        return jsonify({"message": f"Analysis complete. Processed {len(all_messages)} messages and identified new trends."}), 200

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

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
