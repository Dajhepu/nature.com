from flask import Flask, render_template, request, redirect, url_for
import uuid

app = Flask(__name__)

# A simple in-memory "database" to store offers
offers = {}

@app.route('/')
def index():
    """Renders the main page where users can create an offer."""
    return render_template('index.html')

@app.route('/create_offer', methods=['POST'])
def create_offer():
    """Handles the form submission to create a new risk-free offer."""
    original_price = request.form.get('original_price')
    discount_percentage = request.form.get('discount_percentage')

    # Basic validation
    if not original_price or not discount_percentage:
        return "Error: Missing price or discount percentage.", 400

    try:
        price = float(original_price)
        discount = int(discount_percentage)
    except ValueError:
        return "Error: Invalid input.", 400

    new_price = price * (1 - discount / 100)

    # Create a unique ID for the offer
    offer_id = str(uuid.uuid4())[:8]

    # Store the offer details
    offers[offer_id] = {
        'original_price': price,
        'discount_percentage': discount,
        'new_price': new_price,
        'claimed': False
    }

    # Redirect to the offer page
    return redirect(url_for('view_offer', offer_id=offer_id))

@app.route('/offer/<offer_id>')
def view_offer(offer_id):
    """Displays the generated offer to the customer."""
    offer_details = offers.get(offer_id)
    if not offer_details:
        return "Offer not found.", 404

    return render_template('offer_page.html', offer=offer_details, offer_id=offer_id)

@app.route('/claim/<offer_id>')
def claim_offer(offer_id):
    """Simulates the business owner claiming the offer."""
    offer_details = offers.get(offer_id)
    if not offer_details:
        return "Offer not found.", 404

    # Here you would typically integrate with a payment provider like Stripe
    # For now, we'll just simulate the subscription/payment process.
    offers[offer_id]['claimed'] = True

    return render_template('claim_page.html', offer_id=offer_id)

if __name__ == '__main__':
    app.run(debug=True)
