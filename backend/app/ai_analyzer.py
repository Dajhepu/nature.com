# backend/app/ai_analyzer.py
from groq import Groq
from flask import current_app as app

def analyze_text_with_ai(word, related_messages):
    """
    Groq yordamida matnlar guruhini tahlil qilib, sentiment va xulosa oladi.
    """
    groq_api_key = app.config.get('GROQ_API_KEY')
    if not groq_api_key:
        print("Warning: GROQ_API_KEY is not set. Skipping AI analysis.")
        return {"sentiment": "neutral", "summary": "AI analysis is not configured."}

    client = Groq(api_key=groq_api_key)

    # Xabarlarni bitta matnga birlashtirish
    context = ". ".join(related_messages)

    # Promptni shakllantirish
    system_prompt = (
        "You are an expert text analyst. The user will provide a keyword and a set of related text messages in Uzbek. "
        "Your task is to perform two things:\n"
        "1. Sentiment Analysis: Determine the overall sentiment of the messages related to the keyword. Respond with only one word: 'positive', 'negative', or 'neutral'.\n"
        "2. Summarization: Provide a concise, one-sentence summary in Uzbek that explains why the keyword is trending.\n"
        "Format your response as follows: SENTIMENT|SUMMARY"
    )

    user_prompt = f"Keyword: \"{word}\"\n\nMessages:\n\"\"\"\n{context[:3000]}\n\"\"\"" # Matn hajmini cheklash

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant",
        )

        response_content = chat_completion.choices[0].message.content

        # Javobni parsing qilish
        parts = response_content.split('|', 1)
        if len(parts) == 2:
            sentiment = parts[0].strip().lower()
            summary = parts[1].strip()
            # Sentimentni tekshirish
            if sentiment not in ['positive', 'negative', 'neutral']:
                sentiment = 'neutral'
            return {"sentiment": sentiment, "summary": summary}
        else:
            return {"sentiment": "neutral", "summary": "Could not parse AI response."}

    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return {"sentiment": "neutral", "summary": "Error during AI analysis."}
