
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import (
    ADMIN_ID, PREMIUM_WEEK_DAYS, PREMIUM_MONTH_DAYS,
    PREMIUM_WEEK_PRICE, PREMIUM_MONTH_PRICE
)
import database as db

router = Router()


class Reg(StatesGroup):
    age = State()
    city = State()
    name = State()
    gender = State()
    bio = State()
    photo = State()


class EditProfile(StatesGroup):
    name = State()
    bio = State()
    photo = State()


class Payment(StatesGroup):
    receipt = State()


def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔎 Qidirish"),
                KeyboardButton(text="⚙️ Anketa sozlamalari")
            ],
            [
                KeyboardButton(text="💗 Menga kim layk bosdi"),
                KeyboardButton(text="💜 VIP CHAT")
            ],
            [KeyboardButton(text="💎 PREMIUM")]
        ],
        resize_keyboard=True
    )


def adult_verified(uid):
    u = db.get_user(uid)
    return bool(u and u["approved"] and u["adult_verified"] and u["is_active"])


def main_access(m):
    if not adult_verified(m.from_user.id):
        return False
    return True


@router.message(F.text == "/start")
async def start(m: Message, state: FSMContext):
    db.init_db()
    await state.clear()

    u = db.get_user(m.from_user.id)

    if u and u["approved"]:
        if not u["adult_verified"]:
            await m.answer(
                "🔒 Profilingiz uchun ishonchli 18+ yosh tekshiruvi hali yakunlanmagan."
            )
            return

        await m.answer(
            "⭐ A_Match ga xush kelibsiz!",
            reply_markup=menu()
        )
        return

    await state.set_state(Reg.age)
    await m.answer(
        "🔞 A_Match faqat 18+ foydalanuvchilar uchun.\n"
        "Yoshingizni kiriting. Yoshni yozishning o‘zi tasdiqlash hisoblanmaydi."
    )


@router.message(Reg.age)
async def age(m: Message, state: FSMContext):
    try:
        n = int(m.text)
    except (ValueError, TypeError):
        await m.answer("Yoshingizni raqam bilan kiriting.")
        return

    if n < 18:
        await state.clear()
        await m.answer("Bu xizmat faqat 18 yoshdan kattalar uchun.")
        return

    if n > 100:
        await m.answer("Yoshni tekshirib qayta kiriting.")
        return

    await state.update_data(age=n)
    await state.set_state(Reg.city)
    await m.answer("📍 Shaharingizni yozing. Aniq manzil yubormang.")


@router.message(Reg.city)
async def city(m: Message, state: FSMContext):
    if not m.text:
        await m.answer("Shahar nomini matn ko‘rinishida yuboring.")
        return

    await state.update_data(city=m.text[:50])
    await state.set_state(Reg.name)
    await m.answer("Ismingizni kiriting:")


@router.message(Reg.name)
async def name(m: Message, state: FSMContext):
    if not m.text:
        await m.answer("Ismingizni matn ko‘rinishida yuboring.")
        return

    await state.update_data(name=m.text[:40])
    await state.set_state(Reg.gender)

    kb = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="Erkak"),
            KeyboardButton(text="Ayol")
        ]],
        resize_keyboard=True
    )
    await m.answer("Jinsingizni tanlang:", reply_markup=kb)


@router.message(Reg.gender)
async def gender(m: Message, state: FSMContext):
    if m.text not in ("Erkak", "Ayol"):
        await m.answer("Erkak yoki Ayol tugmasini tanlang.")
        return

    await state.update_data(gender=m.text)
    await state.set_state(Reg.bio)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O‘tkazib yuborish")]
        ],
        resize_keyboard=True
    )
    await m.answer(
        "O‘zingiz haqingizda qisqacha yozing yoki o‘tkazib yuboring:",
        reply_markup=kb
    )


@router.message(Reg.bio)
async def bio(m: Message, state: FSMContext):
    text = "" if m.text == "⏭ O‘tkazib yuborish" else (m.text or "")[:300]

    await state.update_data(bio=text)
    await state.set_state(Reg.photo)
    await m.answer("🤳 Profil rasmingizni yuboring.")


@router.message(Reg.photo, F.photo)
async def photo(m: Message, state: FSMContext):
    from face_check import contains_face

    file = await m.bot.get_file(m.photo[-1].file_id)
    data = await m.bot.download_file(file.file_path)
    raw = data.read()

    if not contains_face(raw):
        await m.answer("❌ Rasmda yuz aniqlanmadi. Boshqa rasm yuboring.")
        return

    d = await state.get_data()

    db.save_user(
        m.from_user.id,
        **d,
        photo_id=m.photo[-1].file_id,
        username=m.from_user.username,
        approved=1,
        created_at=""
    )

    await state.clear()
    await m.answer(
        "✅ Profil ma’lumotlari saqlandi.\n"
        "🔒 Tanishuv funksiyalari yosh ishonchli tasdiqlangandan keyin ochiladi."
    )


@router.message(Reg.photo)
async def wrong_photo(m: Message):
    await m.answer("Iltimos, rasm yuboring.")


@router.message(F.text == "🔎 Qidirish")
async def search(m: Message):
    if not main_access(m):
        await m.answer("🔒 Avval profilingiz uchun 18+ tekshiruv yakunlanishi kerak.")
        return

    u = db.get_user(m.from_user.id)
    p = db.next_profile(m.from_user.id, u["gender"])

    if not p:
        await m.answer("Hozircha yangi tasdiqlangan profil topilmadi.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="❤️ Layk",
            callback_data=f"like:{p['user_id']}"
        ),
        InlineKeyboardButton(
            text="👎 O‘tkazish",
            callback_data=f"skip:{p['user_id']}"
        )
    ]])

    caption = (
        f"<b>{p['name']}</b>, {p['age']} yosh\n"
        f"📍 {p['city']}\n\n{p['bio'] or 'Bio kiritilmagan'}"
    )

    await m.answer_photo(
        p["photo_id"],
        caption=caption,
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("like:"))
async def like(c: CallbackQuery):
    if not adult_verified(c.from_user.id):
        await c.answer("18+ tekshiruv talab qilinadi.", show_alert=True)
        return

    target = int(c.data.split(":")[1])

    if not adult_verified(target):
        await c.answer("Bu profil hozir mavjud emas.")
        return

    mutual = db.add_like(c.from_user.id, target)

    if mutual:
        await c.message.answer(
            "💞 Sizlarda o‘zaro Match!\n"
            "Endi suhbat boshlash uchun taklif yuborishingiz mumkin."
        )
        try:
            await c.bot.send_message(
                target,
                "💞 Sizlarda o‘zaro Match bor! Suhbat boshlashingiz mumkin."
            )
        except Exception:
            pass
    else:
        await c.answer("Layk yuborildi ❤️")

    await c.message.delete()


@router.callback_query(F.data.startswith("skip:"))
async def skip(c: CallbackQuery):
    target = int(c.data.split(":")[1])
    db.add_skip(c.from_user.id, target)
    await c.answer("O‘tkazib yuborildi")
    await c.message.delete()


@router.message(F.text == "💗 Menga kim layk bosdi")
async def likes(m: Message):
    if not main_access(m):
        await m.answer("🔒 Avval 18+ tekshiruv yakunlanishi kerak.")
        return

    rows = db.received_likes(m.from_user.id)

    if not rows:
        await m.answer("Hozircha sizga layk bosishmagan.")
        return

    for p in rows[:20]:
        await m.answer(
            f"❤️ {p['name']}, {p['age']} yosh — {p['city']}"
        )


@router.message(F.text == "💎 PREMIUM")
async def premium(m: Message):
    if not main_access(m):
        await m.answer("🔒 Avval 18+ tekshiruv yakunlanishi kerak.")
        return

    await m.answer(
        "💎 <b>PRO OBUNA</b>\n\n"
        f"✨ 1 hafta — {PREMIUM_WEEK_PRICE:,} so‘m\n"
        f"✨ 1 oy — {PREMIUM_MONTH_PRICE:,} so‘m\n\n"
        "Pro imkoniyatlari:\n"
        "• 5 tagacha qo‘shimcha chat taklifi\n"
        "• Profilingizga qo‘shimcha imkoniyatlar\n\n"
        "To‘lov admin tomonidan tekshiriladi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="1 hafta",
                callback_data="buy:7"
            )],
            [InlineKeyboardButton(
                text="1 oy",
                callback_data="buy:30"
            )]
        ])
    )


@router.callback_query(F.data.startswith("buy:"))
async def buy(c: CallbackQuery, state: FSMContext):
    if not adult_verified(c.from_user.id):
        await c.answer("18+ tekshiruv talab qilinadi.", show_alert=True)
        return

    days = int(c.data.split(":")[1])

    if days == 7:
        amount = PREMIUM_WEEK_PRICE
    elif days == 30:
        amount = PREMIUM_MONTH_PRICE
    else:
        await c.answer("Noto‘g‘ri tarif.", show_alert=True)
        return

    await state.update_data(plan_days=days, amount=amount)
    await state.set_state(Payment.receipt)

    await c.message.answer(
        f"💎 Tanlangan tarif: {days} kun\n"
        f"To‘lov miqdori: {amount:,} so‘m\n\n"
        "To‘lovni faqat bot egasi ko‘rsatgan rasmiy to‘lov usuli orqali qiling. "
        "So‘ng chek rasmini yuboring.\n"
        "Chek admin tomonidan mustaqil tekshiriladi."
    )
    await c.answer()


@router.message(Payment.receipt, F.photo)
async def payment_receipt(m: Message, state: FSMContext):
    d = await state.get_data()

    payment_id = db.create_payment(
        m.from_user.id,
        d["plan_days"],
        d["amount"],
        m.photo[-1].file_id
    )

    await state.clear()

    await m.answer(
        "🧾 Chekingiz admin tekshiruviga yuborildi. "
        "Tekshiruv tugagach sizga xabar beriladi."
    )

    if ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Tasdiqlash",
                callback_data=f"payok:{payment_id}"
            ),
            InlineKeyboardButton(
                text="❌ Rad etish",
                callback_data=f"payno:{payment_id}"
            )
        ]])

        try:
            await m.bot.send_photo(
                ADMIN_ID,
                m.photo[-1].file_id,
                caption=(
                    f"💳 Yangi to‘lov so‘rovi\n"
                    f"ID: {payment_id}\n"
                    f"Foydalanuvchi: {m.from_user.id}\n"
                    f"Tarif: {d['plan_days']} kun\n"
                    f"Summa: {d['amount']:,} so‘m\n\n"
                    "Tasdiqlashdan oldin bank ilovasida to‘lovni tekshiring."
                ),
                reply_markup=kb
            )
        except Exception:
            pass


@router.message(Payment.receipt)
async def wrong_receipt(m: Message):
    await m.answer("Iltimos, to‘lov chekini rasm ko‘rinishida yuboring.")


@router.callback_query(F.data.startswith("payok:"))
async def payment_approve(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        await c.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    payment_id = int(c.data.split(":")[1])
    row = db.get_payment(payment_id)

    if not row or row["status"] != "pending":
        await c.answer("Bu to‘lov allaqachon ko‘rib chiqilgan.")
        return

    if not db.review_payment(payment_id, c.from_user.id, True):
        await c.answer("To‘lovni tasdiqlab bo‘lmadi.")
        return

    await c.bot.send_message(
        row["user_id"],
        "✅ To‘lovingiz admin tomonidan tasdiqlandi. Pro obunangiz faollashtirildi!"
    )

    await c.message.edit_caption(
        caption=f"✅ To‘lov #{payment_id} admin tomonidan tasdiqlandi."
    )
    await c.answer("Pro faollashtirildi.")


@router.callback_query(F.data.startswith("payno:"))
async def payment_reject(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        await c.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    payment_id = int(c.data.split(":")[1])
    row = db.get_payment(payment_id)

    if not row or row["status"] != "pending":
        await c.answer("Bu to‘lov allaqachon ko‘rib chiqilgan.")
        return

    if not db.review_payment(payment_id, c.from_user.id, False):
        await c.answer("So‘rovni rad etib bo‘lmadi.")
        return

    await c.bot.send_message(
        row["user_id"],
        "❌ To‘lov tasdiqlanmadi. Iltimos, admin bilan bog‘laning."
    )

    await c.message.edit_caption(
        caption=f"❌ To‘lov #{payment_id} rad etildi."
    )
    await c.answer("To‘lov rad etildi.")


@router.message(F.text == "⚙️ Anketa sozlamalari")
async def settings(m: Message):
    if not main_access(m):
        await m.answer("🔒 Avval 18+ tekshiruv yakunlanishi kerak.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ismni o‘zgartirish", callback_data="edit:name")],
        [InlineKeyboardButton(text="Bio o‘zgartirish", callback_data="edit:bio")],
        [InlineKeyboardButton(text="Rasmni o‘zgartirish", callback_data="edit:photo")],
        [InlineKeyboardButton(text="Profilni o‘chirish", callback_data="profile:delete")]
    ])

    await m.answer("⚙️ Qaysi ma’lumotni o‘zgartirmoqchisiz?", reply_markup=kb)


@router.callback_query(F.data.startswith("edit:"))
async def edit_start(c: CallbackQuery, state: FSMContext):
    if not adult_verified(c.from_user.id):
        await c.answer("18+ tekshiruv talab qilinadi.", show_alert=True)
        return

    field = c.data.split(":")[1]

    if field == "name":
        await state.set_state(EditProfile.name)
        await c.message.answer("Yangi ismingizni kiriting:")
    elif field == "bio":
        await state.set_state(EditProfile.bio)
        await c.message.answer(
            "Yangi bio yozing yoki o‘zgartirmaslik uchun /cancel yuboring:"
        )
    elif field == "photo":
        await state.set_state(EditProfile.photo)
        await c.message.answer("Yangi profilingiz rasmini yuboring.")

    await c.answer()


@router.message(EditProfile.name)
async def edit_name(m: Message, state: FSMContext):
    if not m.text:
        await m.answer("Ismni matn ko‘rinishida yuboring.")
        return

    db.save_user(m.from_user.id, name=m.text[:40])
    await state.clear()
    await m.answer("✅ Ismingiz yangilandi.", reply_markup=menu())


@router.message(EditProfile.bio)
async def edit_bio(m: Message, state: FSMContext):
    if m.text == "/cancel":
        await state.clear()
        await m.answer("O‘zgarish bekor qilindi.", reply_markup=menu())
        return

    db.save_user(m.from_user.id, bio=(m.text or "")[:300])
    await state.clear()
    await m.answer("✅ Bio yangilandi.", reply_markup=menu())


@router.message(EditProfile.photo, F.photo)
async def edit_photo(m: Message, state: FSMContext):
    from face_check import contains_face

    file = await m.bot.get_file(m.photo[-1].file_id)
    data = await m.bot.download_file(file.file_path)

    if not contains_face(data.read()):
        await m.answer("❌ Rasmda yuz aniqlanmadi. Boshqa rasm yuboring.")
        return

    db.save_user(m.from_user.id, photo_id=m.photo[-1].file_id)
    await state.clear()
    await m.answer("✅ Rasm yangilandi.", reply_markup=menu())


@router.message(EditProfile.photo)
async def edit_photo_wrong(m: Message):
    await m.answer("Iltimos, rasm yuboring.")


@router.callback_query(F.data == "profile:delete")
async def delete_profile(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        await c.answer(
            "Profilni o‘chirish hozircha admin orqali amalga oshiriladi.",
            show_alert=True
        )
        return

    await c.answer("Admin tasdig‘i talab qilinadi.", show_alert=True)


@router.message(F.text == "💜 VIP CHAT")
async def vip(m: Message):
    if not main_access(m):
        await m.answer("🔒 Avval 18+ tekshiruv yakunlanishi kerak.")
        return

    await m.answer(
        "💜 VIP CHAT\n"
        "Qo‘shimcha chat takliflari faqat Pro foydalanuvchilarga beriladi. "
        "Qabul qiluvchi rozilik bergandan keyingina suhbat ochiladi."
    )


@router.message(F.text == "/stats")
async def stats(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    await m.answer(
        f"👥 Tasdiqlangan 18+ profillar: {db.count_users()}"
    )


@router.message(F.text == "/cancel")
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.", reply_markup=menu())
