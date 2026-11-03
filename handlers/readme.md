a Match Bot — xavfsiz MVP

Muhim

• Ushbu loyiha 18+ xizmat uchun mo‘ljallangan. 18 yoshdan kichik foydalanuvchilar ro‘yxatdan o‘ta olmaydi.
• Yosh maydoni o‘z-o‘zini bildiradi; haqiqiy yoshni tasdiqlash uchun qonuniy age-assurance provayderini integratsiya qiling.
• Yuz detektori faqat rasmda yuzga o‘xshash obyektni topadi. U shaxsni yoki yoshni tasdiqlamaydi.
• Aniq manzil, telefon yoki boshqa ortiqcha shaxsiy ma’lumotlarni so‘ramang.
• Kontakt so‘rovlari faqat o‘zaro Matchdan keyin va qabul qiluvchining roziligi bilan ishlashi kerak.
• Bank karta raqamini kodga yoki ommaviy repozitoriyga joylamang. To‘lov uchun rasmiy provayder (masalan, Telegram Payments yoki mahalliy litsenziyalangan provayder) va server-side webhook ishlating. To‘lovni skrinshot bilan avtomatik tasdiqlamang.

Ishga tushirish

1. BotFather orqali bot yarating va token oling.
2. .env.example faylini .env deb nusxalang va BOT_TOKEN hamda ADMIN_ID ni kiriting.
3. pip install -r requirements.txt
4. python main.py

GitHub

.env faylini GitHub’ga yuklamang. .gitignore qo‘shing:

.env
*.db
__pycache__/

Render

1. Loyihani GitHub’ga push qiling.
2. Render → New → Blueprint orqali render.yaml ni tanlang.
3. BOT_TOKEN va ADMIN_ID environment variable’larini kiriting.
4. Persistent disk yoqilganini tekshiring.

Hozirgi MVP chegaralari

Bu boshlang‘ich ishlaydigan skelet: anketa, yuz borligini tekshirish, profil qidirish, layk va Premium muddat tekshiruvi mavjud. Admin orqali to‘lovni tasdiqlash, to‘liq anketa tahriri, kontakt so‘rovini qabul/rad etish, shikoyat/bloklash, rate-limit va mustahkam yosh tekshiruvi keyingi bosqichda qo‘shilishi shart. Real foydalanuvchilarga ochishdan oldin test va xavfsizlik tekshiruvi zarur.
