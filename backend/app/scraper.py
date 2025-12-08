from textblob import TextBlob

def find_dissatisfied_customers(business_type, location):
    """
    Placeholder function to simulate finding dissatisfied customers.
    In a real application, this would involve scraping Google Maps,
    and would be a more complex process.
    """
    # Mock data simulating scraped reviews
    reviews = [
        {"author": "John Doe", "text": "The service was terrible. I would not recommend this place."},
        {"author": "Jane Smith", "text": "Amazing experience! The staff was friendly and the product was great."},
        {"author": "Peter Jones", "text": "It was okay, but I've had better. Not worth the price."},
        {"author": "Mary Williams", "text": "I'm so happy I found this business. I'll be a returning customer for sure!"},
        {"author": "David Brown", "text": "A complete waste of money. The quality was poor and the customer service was rude."}
    ]

    dissatisfied_customers = []
    for review in reviews:
        analysis = TextBlob(review["text"])
        # Polarity is a float between -1.0 (negative) and 1.0 (positive)
        if analysis.sentiment.polarity < 0:
            dissatisfied_customers.append({
                "source": "Google Maps",
                "customer_name": review["author"],
                "review_text": review["text"],
                "sentiment": "negative"
            })

    return dissatisfied_customers
