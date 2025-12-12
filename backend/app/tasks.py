from . import rq, db
from .models import Message, MessageTemplate
from .telegram_service import send_telegram_message

@rq.job
def send_message_job(message_id):
    """
    A background job to send a single message.
    """
    message = db.session.get(Message, message_id)
    if not message:
        return f"Message with ID {message_id} not found."

    template = message.campaign.message_template
    lead = message.lead

    try:
        send_telegram_message(
            chat_id=lead.telegram_user_id,
            text=template.content
        )
        message.status = 'sent'
        db.session.commit()
        return f"Message to {lead.full_name} sent successfully."
    except Exception as e:
        message.status = 'failed'
        db.session.commit()
        return f"Failed to send message to {lead.full_name}: {e}"
