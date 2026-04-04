from flask import request, jsonify, send_from_directory
from . import db
from .models import User, Business, Lead, Campaign, Message, MessageTemplate, MonitoredGroup, WordFrequency, Trend
from .telegram_service import send_telegram_message_async
from .pyrogram_client import pyrogram_manager
from .telegram_scraper import get_group_members, get_group_messages
from .text_processor import get_word_frequencies
from .trend_analyzer import analyze_trends_for_business
import asyncio
from flask import current_app as app
import os
import traceback
from groq import Groq
from datetime import date, datetime
from sqlalchemy import func

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
                "status": lead.status,
            }
            for lead in business.leads
        ]
        return jsonify(leads), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/leads/<int:lead_id>/status', methods=['PUT'])
def update_lead_status(lead_id):
    user = _get_current_user()
    lead = Lead.query.get_or_404(lead_id)
    # Ensure the lead belongs to one of the user's businesses
    if lead.business.owner.id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'error': 'Missing status in request body'}), 400

    # Basic validation for status field
    allowed_statuses = ['New', 'Contacted', 'Interested', 'Converted', 'Not Interested']
    if data['status'] not in allowed_statuses:
        return jsonify({'error': f'Invalid status. Must be one of {allowed_statuses}'}), 400

    lead.status = data['status']
    db.session.commit()

    return jsonify({
        "id": lead.id,
        "full_name": lead.full_name,
        "username": lead.username,
        "activity_score": lead.activity_score,
        "source": lead.source,
        "status": lead.status
    })

@app.route('/api/business/<int:business_id>/analytics', methods=['GET'])
def get_business_analytics(business_id):
    user = _get_current_user()
    business = Business.query.get_or_404(business_id)
    if business.owner.id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Total leads
    total_leads = Lead.query.filter_by(business_id=business_id).count()

    # Lead status distribution
    lead_status_distribution = db.session.query(Lead.status, func.count(Lead.status)).filter_by(business_id=business_id).group_by(Lead.status).all()
    lead_status_distribution = dict(lead_status_distribution)

    # Leads by source
    leads_by_source = db.session.query(Lead.source, func.count(Lead.source)).filter_by(business_id=business_id).group_by(Lead.source).all()
    leads_by_source = dict(leads_by_source)

    # Total messages sent
    total_messages_sent = Message.query.join(Lead).filter(Lead.business_id == business_id, Message.status == 'sent').count()

    analytics_data = {
        'total_leads': total_leads,
        'lead_status_distribution': lead_status_distribution,
        'leads_by_source': leads_by_source,
        'total_messages_sent': total_messages_sent
    }

    return jsonify(analytics_data)


@app.route('/api/campaigns/start', methods=['POST'])
def start_campaign():
    """Start a messaging campaign with efficient, batch-based message sending."""
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

    # Create campaign and message records first
    new_campaign = Campaign(name=name, business_id=business.id, message_template_id=template.id)
    db.session.add(new_campaign)
    db.session.flush()

    messages_to_send = []
    for lead_id in lead_ids:
        lead = db.session.get(Lead, lead_id)
        if lead and lead.business_id == business.id:
            msg = Message(campaign_id=new_campaign.id, lead_id=lead.id, status='pending')
            db.session.add(msg)
            messages_to_send.append({'lead': lead, 'message_record': msg})

    db.session.commit() # Commit records before sending

    # --- Async Batch Sending ---
    async def _send_campaign_async():
        client = pyrogram_manager.get_client()
        results = {'sent': 0, 'failed': 0}
        for item in messages_to_send:
            lead = item['lead']
            # Now we pass the already-started client to the async function
            was_sent = await send_telegram_message_async(client, lead.telegram_user_id, template.content)
            if was_sent:
                results['sent'] += 1
                item['message_record'].status = 'sent'
            else:
                results['failed'] += 1
                item['message_record'].status = 'failed'
        return results

    try:
        # Using a helper to run the async code from a sync context
        results = asyncio.run(_send_campaign_async())
        db.session.commit()  # Commit status updates
        return jsonify({
            "message": f"Campaign '{name}' completed. Sent: {results['sent']}, Failed: {results['failed']}.",
            "campaign_id": new_campaign.id
        }), 201
    except Exception as e:
        app.logger.error(f"A critical error occurred during campaign sending: {e}", exc_info=True)
        # Rollback any potential lingering DB changes
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred during the campaign."}), 500


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

import json

@app.route('/api/ai/generate_template', methods=['POST'])
def generate_ai_template():
    """Generate message templates using Groq"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("WARNING: GROQ_API_KEY not set. Returning mock data.")
            return jsonify({
                "suggestions": [
                    "Mock suggestion 1: Check your GROQ_API_KEY.",
                    "Mock suggestion 2: The AI service is currently offline.",
                    "Mock suggestion 3: Have a great day!"
                ]
            }), 200

        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a marketing expert specializing in Telegram outreach. "
                        "Based on the user's prompt, generate 3 distinct, short, and engaging message templates. "
                        "Each template must be a maximum of 2 sentences. "
                        "Your response MUST be a valid JSON object with a single key 'suggestions' "
                        "which contains a list of the 3 string templates. For example: "
                        "{\"suggestions\": [\"Template 1\", \"Template 2\", \"Template 3\"]}"
                    )
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
        )
        response_content = chat_completion.choices[0].message.content
        suggestions = json.loads(response_content)
        return jsonify(suggestions)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate AI suggestions: {str(e)}"}), 500


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

@app.route('/api/monitored_groups/<int:group_id>', methods=['DELETE'])
def delete_monitored_group(group_id):
    """Kuzatilayotgan guruhni o'chiradi"""
    user = _get_current_user()
    group = MonitoredGroup.query.get_or_404(group_id)

    # Foydalanuvchi ushbu guruhga egalik qiluvchi biznesning egasi ekanligini tekshirish
    if group.business.owner.id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(group)
    db.session.commit()

    return jsonify({'message': 'Group removed successfully'}), 200

@app.route('/api/business/<int:business_id>/trends', methods=['DELETE'])
def clear_analysis_data(business_id):
    """Biznes uchun barcha trend tahlili ma'lumotlarini o'chiradi"""
    user = _get_current_user()
    business = Business.query.get_or_404(business_id)

    if business.owner.id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Bu biznesga tegishli barcha Trend va WordFrequency yozuvlarini o'chirish
    Trend.query.filter_by(business_id=business_id).delete()
    WordFrequency.query.filter_by(business_id=business_id).delete()

    db.session.commit()

    return jsonify({'message': 'Trend analysis data cleared successfully'}), 200

@app.route('/api/business/<int:business_id>/trends', methods=['GET'])
def get_trends(business_id):
    """Eng so'nggi trendlarni oladi"""
    today = date.today()
    trends = Trend.query.filter_by(business_id=business_id, date=today).order_by(Trend.trend_score.desc()).all()

    return jsonify([
        {
            "word": t.word,
            "trend_score": round(t.trend_score, 2),
            "sentiment": t.sentiment,
            "summary": t.summary
        }
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
        analyze_trends_for_business(business_id, all_messages, today)

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
