from flask import Blueprint, request, jsonify, render_template
from .models import Offer, User
from .extensions import db
import decimal

offers = Blueprint('offers', __name__)

# --- HTML Routes ---
@offers.route('/create_offer', methods=['GET'])
def create_offer_page():
    """Renders the page for creating a new offer."""
    return render_template('create_offer.html')

@offers.route('/offer/<offer_id>', methods=['GET'])
def view_offer_certificate(offer_id):
    """Displays the generated offer certificate to the user."""
    offer = Offer.query.get(offer_id)
    if not offer:
        return "Offer not found", 404
    return render_template('offer_certificate.html', offer=offer)

# --- API Route ---
@offers.route('/api/offers/create', methods=['POST'])
def create_offer():
    """Creates a new discount offer."""
    data = request.get_json()

    consumer_id = data.get('consumer_id')
    original_price_str = data.get('original_price')
    discount_percent_str = data.get('discount_percent')

    if not all([consumer_id, original_price_str, discount_percent_str]):
        return jsonify({'error': 'Missing required fields.'}), 400

    user = User.query.get(consumer_id)
    if not user:
        return jsonify({'error': 'Invalid consumer ID.'}), 400

    try:
        original_price = decimal.Decimal(original_price_str)
        discount_percent = int(discount_percent_str)
    except (ValueError, decimal.InvalidOperation):
        return jsonify({'error': 'Invalid price or discount format.'}), 400

    if not (0 < discount_percent <= 90):
         return jsonify({'error': 'Discount must be between 1 and 90.'}), 400

    final_price = original_price * (1 - decimal.Decimal(discount_percent / 100))

    new_offer = Offer(
        consumer_id=consumer_id,
        original_price=original_price,
        discount_percent=discount_percent,
        final_price=final_price.quantize(decimal.Decimal('0.01'))
    )

    db.session.add(new_offer)
    db.session.commit()

    return jsonify({
        'message': 'Offer created successfully.',
        'offer_id': new_offer.id
    }), 201
