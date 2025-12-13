# backend/app/trend_analyzer.py
from . import db
from .models import WordFrequency, Trend
from .ai_analyzer import analyze_text_with_ai
from datetime import date, timedelta

def calculate_trend_score(word, current_frequency, past_frequency):
    """
    Oddiy trend skorini hisoblash funksiyasi.
    Agar oldingi chastota 0 bo'lsa, o'sish cheksiz bo'ladi, shuning uchun biz uni
    hozirgi chastotaga tenglashtiramiz (katta skor).
    """
    if past_frequency == 0:
        return float(current_frequency)  # Prevent division by zero

    # Foiz o'sishini hisoblash
    percentage_increase = ((current_frequency - past_frequency) / past_frequency) * 100

    # Og'irliklar: o'sishga ko'proq, mutlaq qiymatga kamroq e'tibor beramiz
    score = (percentage_increase * 0.7) + (current_frequency * 0.3)

    return score

def analyze_trends_for_business(business_id, all_messages, analysis_date=None):
    """
    Belgilangan biznes uchun so'z chastotalarini tahlil qiladi, AI yordamida boyitadi va trendlarni aniqlaydi.
    """
    if analysis_date is None:
        analysis_date = date.today()

    yesterday = analysis_date - timedelta(days=1)

    # Bugungi va kechagi so'z chastotalarini olish
    today_frequencies = {
        wf.word: wf.frequency
        for wf in WordFrequency.query.filter_by(business_id=business_id, date=analysis_date).all()
    }

    yesterday_frequencies = {
        wf.word: wf.frequency
        for wf in WordFrequency.query.filter_by(business_id=business_id, date=yesterday).all()
    }

    print(f"📈 Analyzing trends for {analysis_date}...")
    print(f"   Found {len(today_frequencies)} unique words for today.")
    print(f"   Found {len(yesterday_frequencies)} unique words for yesterday.")

    # Mavjud trendlarni tozalash
    Trend.query.filter_by(business_id=business_id, date=analysis_date).delete()

    # Trend skorlarini hisoblash
    trends = []
    for word, today_freq in today_frequencies.items():
        yesterday_freq = yesterday_frequencies.get(word, 0)

        # Trend faqat sezilarli o'sish bo'lganda hisoblanadi
        if today_freq > yesterday_freq and today_freq > 5: # Minimal chastota chegarasi
            score = calculate_trend_score(word, today_freq, yesterday_freq)

            if score > 10: # Minimal skor chegarasi
                # AI tahlili uchun shu so'z qatnashgan xabarlarni topish
                related_messages = [msg for msg in all_messages if word in msg.lower()]

                ai_result = {"sentiment": "neutral", "summary": ""}
                if related_messages:
                    ai_result = analyze_text_with_ai(word, related_messages)

                new_trend = Trend(
                    word=word,
                    trend_score=score,
                    date=analysis_date,
                    business_id=business_id,
                    sentiment=ai_result.get('sentiment'),
                    summary=ai_result.get('summary')
                )
                trends.append(new_trend)

    if trends:
        # Trendlarni skor bo'yicha saralash
        trends.sort(key=lambda t: t.trend_score, reverse=True)

        # Eng yaxshi 10 yoki undan kam trendni saqlash
        top_trends = trends[:10]
        db.session.add_all(top_trends)
        db.session.commit()
        print(f"   ✅ Saved {len(top_trends)} new trends to the database after AI analysis.")
    else:
        print("   ℹ️ No significant trends were identified.")

    return trends[:10]
