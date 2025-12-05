### **WooCommerce uchun "Upsell & Cross-sell" Plagini Yaratish Bo'yicha Texnik Vazifa**

**Hujjat sanasi:** 25.05.2024
**Loyiha nomi:** Smart Upsell for WooCommerce

**1. Umumiy Ma'lumot**

*   **Platforma:** WordPress + WooCommerce.
*   **Asosiy maqsad:** Mijoz mahsulotni savatchaga qo'shganda (Upsell) yoki "Checkout" sahifasiga o'tganda (Cross-sell) unga qo'shimcha mahsulotlarni strategik taklif qilish orqali o'rtacha chek miqdorini va do'kon daromadini oshirish.
*   **Maqsadli bozor:** Xalqaro bozor (birinchi navbatda AQSh), shuning uchun interfeys ingliz tilida va sozlamalar moslashuvchan bo'lishi kerak.
*   **Sifat darajasi:** CodeCanyon platformasida sotuvga qo'yish talablariga to'liq javob beradigan, professional va optimallashtirilgan yechim.

**2. Asosiy Funksionallik (Frontend – Mijoz Tomoni)**

**2.1. Upsell Pop-up ("Savatchaga qo'shganda")**
*   **Ishga tushish sharti:** Mijoz "Add to cart" tugmasini bosgandan so'ng darhol, sahifani to'smasdan (modal/pop-up) paydo bo'ladi.
*   **Tarkibi:**
    *   Sarlavha (masalan, "Don't miss this exclusive offer!" yoki "Customers also bought").
    *   Taklif etilayotgan mahsulotning aniq va sifatli rasmi.
    *   Mahsulot nomi.
    *   Mahsulot narxi (eski narx va chegirmali narx, agar chegirma qo'llanilgan bo'lsa).
    *   Chegirma haqida yozuv (masalan, "+10% cheaper if added now").
    *   "Add to Cart" (yoki shunga o'xshash) tugmasi.
    *   Pop-upni yopish uchun "X" belgisi yoki "No, thanks" linki.
*   **Mantiq:**
    *   "Add to Cart" tugmasi bosilganda, mahsulot savatchaga **AJAX orqali (sahifani qayta yuklamasdan)** qo'shilishi va pop-up yopilishi kerak.
    *   Mijoz pop-upni yopganda, u o'z ishini davom ettiradi.

**2.2. Cross-sell Bloki ("Checkout" Sahifasida)**
*   **Joylashuvi:** "Checkout" sahifasining yuqori qismida yoki to'lov ma'lumotlaridan oldin maxsus blokda ko'rsatiladi.
*   **Tarkibi:**
    *   Sarlavha (masalan, "You might also like...").
    *   1-3 tagacha tavsiya etilgan mahsulotlar ro'yxati (rasm, nom, narx).
    *   Har bir mahsulot yonida "Add to Order" tugmasi.
*   **Mantiq:**
    *   "Add to Order" tugmasi bosilganda, mahsulot **sahifani yangilamasdan (AJAX)** buyurtmaga qo'shilishi va umumiy summa avtomatik tarzda yangilanishi kerak.

**3. Administrator Paneli (Backend – Admin Tomoni)**

**3.1. Asosiy Sozlamalar**
*   Pluginni yoqish/o'chirish uchun global checkbox.
*   Upsell va Cross-sell funksiyalarini alohida-alohida yoqish/o'chirish imkoniyati.

**3.2. "Tavsiyalar Qoidalari" Yaratish (Offer Rules)**
Admin panelda yangi menyu ("Smart Upsells") yaratilishi kerak. U yerda admin cheksiz "qoidalar" yaratishi mumkin bo'ladi:
*   **Qoida yaratish interfeysi:**
    1.  **Trigger (Asosiy mahsulot):** Qaysi mahsulot savatchaga qo'shilganda tavsiya chiqishini tanlash:
        *   Aniq bir mahsulot (qidiruv orqali tanlanadi).
        *   Biror bir kategoriyadagi istalgan mahsulot.
        *   Barcha mahsulotlar uchun yagona qoida.
    2.  **Tavsiya turi:** Ushbu qoida uchun "Upsell (Pop-up)" yoki "Cross-sell (Checkout)" turini tanlash.
    3.  **Tavsiya mahsulotlari:** Qaysi mahsulot(lar) tavsiya qilinishini tanlash (qidiruv funksiyasi bilan, 1 dan 3 tagacha tanlash imkoniyati).
    4.  **Chegirma sozlamalari (Faqat Upsell uchun):**
        *   Chegirma yo'q.
        *   Foizli chegirma (%).
        *   Aniq summa ($).
        *   **Muhim:** Chegirma faqat Upsell orqali qo'shilganda amal qilishi kerak, to'g'ridan-to'g'ri sotib olganda emas.

**3.3. Dizaynni Moslashtirish (Customizer)**
*   **Pop-up dizayni:**
    *   Sarlavha matnini o'zgartirish.
    *   "Add to Cart" tugmasi matnini o'zgartirish.
    *   Fon rangi, matn rangi, tugma rangi va tugma matni rangini tanlash (color picker orqali).
*   **Cross-sell bloki dizayni:**
    *   Sarlavha matnini o'zgartirish.
    *   Elementlarning ranglarini (matn, tugma) moslashtirish imkoniyati.

**3.4. Statistik Panel (Dashboard)**
*   Admin panelda alohida "Analytics" sahifasi yoki Dashboard vidjeti.
*   **Ko'rsatkichlar:**
    *   **Impressions (Ko'rsatuvlar):** Tavsiyalar (pop-up/blok) necha marta mijozlarga ko'rsatilgani.
    *   **Clicks (Qo'shishlar):** Tavsiya qilingan mahsulotlardan nechtasi savatchaga/buyurtmaga qo'shilgani.
    *   **Conversion Rate (Konversiya):** Qo'shishlar sonining ko'rsatuvlar soniga nisbati (%).
    *   **Revenue (Qo'shimcha Daromad):** Ushbu plugin orqali qancha qo'shimcha sotuv qilingani (summa hisobida).
*   **Filtr:** Statistikani ma'lum bir sana oralig'i (hafta, oy, yil) bo'yicha filtrlash imkoniyati.

**4. Texnik Talablar**

*   **Kodlash Standartlari:** Kod **WordPress Coding Standards (PHP, JS, CSS)** talablariga to'liq mos bo'lishi kerak. Kommentlar bilan yaxshi hujjatlashtirilishi lozim.
*   **Tezkorlik (Performance):** Plugin saytning yuklanish tezligiga minimal ta'sir qilishi kerak. AJAX so'rovlari optimallashtirilgan, keraksiz skriptlar faqat kerakli sahifalarda yuklanishi shart (masalan, admin panel JS'lari faqat admin panelda).
*   **Moslashuvchanlik (Compatibility):** WooCommerce'ning so'nggi versiyalari va kamida 2-3 ta oldingi versiyasi bilan to'liq ishlashi ta'minlanishi kerak. Turli WordPress mavzulari (themes) bilan muammosiz ishlashi lozim.
*   **Mobil Adaptatsiya (Responsiveness):** Pop-up va checkout bloki barcha qurilmalarda (desktop, planshet, mobil) to'g'ri va chiroyli ko'rinishi shart.
*   **Xavfsizlik:** Barcha kiruvchi va chiquvchi ma'lumotlar tozalanishi (sanitized/escaped), nonces'lardan foydalanilishi va WordPress xavfsizlik standartlariga rioya qilinishi kerak.
*   **Tarjima (Localization):** Plugin barcha matnlari tarjima uchun tayyor bo'lishi kerak (.pot fayli yaratilishi lozim).

**5. Loyiha Yakuniy Natijasi (Deliverables)**

1.  O'rnatish uchun tayyor bo'lgan `.zip` formatidagi plugin fayli.
2.  To'liq va kommentlangan dasturiy kod (source code).
3.  Admin uchun plaginni sozlash va ishlatish bo'yicha qisqa qo'llanma (dokumentatsiya).
