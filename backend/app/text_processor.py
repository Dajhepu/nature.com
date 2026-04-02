# backend/app/text_processor.py
import re
from collections import Counter
from nltk.stem import SnowballStemmer
from nltk.tokenize import word_tokenize

# O'zbek tili uchun stop-so'zlar ro'yxati
# Manba: https://github.com/ilyosrabbimov/uzbek-stop-words
UZBEK_STOP_WORDS = {
    "aftidan", "agar", "albatta", "allaqachon", "ammo", "aslida", "asosan", "asosiy", "atrofida", "avvalgi",
    "axborot", "ayin", "aynan", "ayni", "ayniqsa", "ba'zi", "balki", "barcha", "barchasi", "baribir", "ba’zi",
    "beradi", "beraman", "berdi", "bergan", "berilgan", "berish", "besh", "beshinchi", "biladi", "bilaman",
    "bilan", "bir", "birga", "biri", "birinchi", "biroq", "biroz", "bitta", "biz", "bizniki", "bizning",
    "bo'lgan", "bo'lish", "bo'lmoq", "bog‘liq", "bor", "borish", "boshlamoq", "boshlanadi", "boshlaydi",
    "boshqa", "boxabar", "bo‘l", "bo‘ladi", "bo‘lardi", "bo‘ldi", "bo‘lgan", "bo‘lib", "bo‘ling", "bo‘lish",
    "bo‘lishi", "bo‘lishni", "bo‘lmadi", "bo‘lmagan", "bo‘lmaydi", "bo‘lmoq", "bo‘lsa", "bo‘yicha", "bo‘ylab",
    "bu", "bular", "bundan", "bunday", "butun", "chetga", "chiqib", "chiqqan", "chunki", "dahshatli", "dan",
    "darhol", "davom", "davomida", "deb", "degan", "deya", "deyarli", "deydi", "deyiladi", "doim", "doir",
    "doirasida", "e'lon", "edi", "ega", "ekan", "emas", "endi", "eng", "esa", "etadi", "etdi", "etgan",
    "etib", "etiladi", "etildi", "etilgan", "etilishicha", "etish", "e’lon", "faqat", "foto", "gacha",
    "g‘alaba", "ham", "hamda", "hamma", "hammasi", "haqda", "haqida", "haqidagi", "haqiqiy", "har", "harakat",
    "hatto", "hech", "hisoblanadi", "hokazo", "holda", "hozir", "hozirda", "huzuridagi", "ichida", "ichiga",
    "ichkarida", "ikkalasi", "ikki", "ikkinchi", "iliq", "ishlab", "ishonaman", "istasangiz", "ixtiro",
    "joriy", "joy", "joyda", "juda", "kabi", "keladi", "keldi", "kelgan", "kelib", "keling", "keng", "kerak",
    "ketdi", "ketgan", "keyin", "keyingi", "kg", "kichik", "kim", "kimdir", "kimga", "km", "ko'proq", "ko‘p",
    "ko‘plab", "ko‘proq", "ko‘ra", "ko‘rib", "ko‘rsatilgan", "ko‘rsatish", "lekin", "lozim", "ma'lum",
    "ma'lumot", "mana", "marta", "masalan", "mavjud", "mayda", "mazkur", "ma’lum", "ma’lumot", "men",
    "meni", "mening", "ming", "moddasi", "mos", "muhim", "mumkin", "muvofiq", "nafar", "narsa", "natijada",
    "natijasida", "necha", "nega", "nima", "o'chirilgan", "o'sha", "o'zi", "o'zim", "o'zimiz", "o'zingiz",
    "o'zlari", "oladi", "oldi", "oldin", "oldindan", "oldingi", "olgan", "olib", "olingan", "olish",
    "oqibatida", "orasida", "orqada", "orqaga", "orqali", "ortiq", "ostida", "ozgina", "o‘quv", "o‘rin",
    "o‘rniga", "o‘rtasida", "o‘sha", "o‘tdi", "o‘tgan", "o‘tkazish", "o‘z", "o‘zgarib", "o‘zi", "o‘zim",
    "o‘zimiz", "o‘zingiz", "o‘zini", "o‘zining", "o‘zlari", "pastda", "pastga", "paydo", "paytda", "qachon",
    "qadar", "qanday", "qaratilgan", "qarshi", "qayerda", "qaysi", "qayta", "qiladi", "qilaman", "qilaylik",
    "qildi", "qildim", "qilgan", "qilib", "qilindi", "qilingan", "qilish", "qilmadim", "qilmaydi",
    "qilmayman", "qilmoq", "qiluvchi", "qilyapti", "qismi", "qisqa", "qisqacha", "qo‘shilgan", "quyida",
    "quyidagi", "ravishda", "sabab", "sabablar", "sababli", "sakkiz", "sakson", "salom", "sana", "saqlamoq",
    "saqlanadi", "saqlash", "saqlaydi", "shaxsiy", "shu", "shunchaki", "shunday", "shunga", "shuningdek",
    "sifatida", "siz", "sizniki", "sizning", "sodir", "so‘ng", "so‘nggi", "so‘rash", "ta", "ta'qib",
    "ta'sir", "tahminan", "taklif", "taqdim", "tashqari", "tashqarida", "ta’minlash", "tez", "tomonidan",
    "topilgan", "to‘g‘ri", "to‘g‘risida", "to‘g‘risidagi", "to‘rtta", "tufayli", "tugatish", "turadi",
    "turli", "tuzatish", "u", "uch", "uchun", "ular", "ularni", "ularning", "unda", "unga", "uni", "uning",
    "ushbu", "ustida", "uzoq", "va", "vaqt", "vaqtda", "vaqtida", "xabar", "xil", "xuddi", "xususan",
    "ya'ni", "yakka", "yana", "yanada", "yangi", "yaqin", "yashirin", "yaxshi", "ya’ni", "yerda", "yetarli",
    "yetib", "yirik", "yo'q", "yoki", "yonida", "yoqilgan", "yordam", "yo‘l", "yo‘q", "yuqorida",
    "yuqoriga", "yuvildi", "yuz", "yuzasidan", "zarur", "zo‘rg‘a"
}

def clean_text(text):
    """
    Tozalash: Tinish belgilari, smayliklar, havolalar va keraksiz simvollarni olib tashlaydi.
    Normallashtirish: Barcha so'zlarni kichik harflarga o'tkazadi.
    """
    text = text.lower()
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # Remove user @mentions
    text = re.sub(r'\@\w+', '', text)
    # Remove hashtags
    text = re.sub(r'\#\w+', '', text)
    # Remove emojis (this is a basic regex, might not catch all)
    text = re.sub(r'[^\w\s]', '', text)
    # Remove numbers
    text = re.sub(r'\d+', '', text)
    # Remove extra whitespace
    text = " ".join(text.split())
    return text

def tokenize_and_filter(text):
    """
    Tokenizatsiya qiladi, stop-so'zlarni filtrlash va stemming.
    """
    cleaned_text = clean_text(text)
    words = word_tokenize(cleaned_text)
    stemmer = SnowballStemmer("russian")

    # Filter out stop words and short words (less than 3 characters)
    filtered_and_stemmed_words = [
        stemmer.stem(word) for word in words
        if word not in UZBEK_STOP_WORDS and len(word) > 2
    ]

    return filtered_and_stemmed_words

def get_word_frequencies(messages):
    """
    Xabarlar ro'yxatidan so'zlar chastotasini hisoblaydi.
    """
    all_words = []
    for message_content in messages:
        all_words.extend(tokenize_and_filter(message_content))

    return Counter(all_words)
