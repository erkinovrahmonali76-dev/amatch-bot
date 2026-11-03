
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, KeyboardButton,
    ReplyKeyboardMarkup, InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import (
    ADMIN_ID,
    PREMIUM_WEEK_PRICE,
    PREMIUM_MONTH_PRICE
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
                KeyboardButton(text="💎 PREMIUM")
            ],
            [KeyboardButton(text="🚫 Bloklanganlar")]
        ],
        resize_keyboard=True
    )


def profile_buttons(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❤️",
                callback_data=f"like:{uid}"
            ),
            InlineKeyboardButton(
                text="👎🏻",
                callback_data=f"skip:{uid}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Bloklash",
                callback_data=f"block:{uid}"
            ),
            InlineKeyboardButton(
                text="⚠️ Shikoyat",
                callback_data=f"report:{uid}"
            )
        ]
    ])


def user_active(uid):
    u = db.get_user(uid)
    return bool(u and u["approved"] and u["is_active"])


def show_profile(p):
    return (
        f"<b>{p['name'] or 'Foydalanuvchi'}</b>\n"
        f"📍 {p['city'] or 'Ko‘rsatilmagan'}\n\n"
        f"{p['bio'] or 'Bio kiritilmagan'}"
    )


async def send_next_profile(m: Message):
    if not user_active(m.from_user.id):
        await m.answer("Avval profilingizni yarating.")
        return

    p = db.next_profile(m.from_user.id)

    if not p:
        await m.answer(
            "Hozircha boshqa mos profil topilmadi. "
            "Keyinroq yana urinib ko‘ring."
        )
        return

    await m.answer_photo(
        p["photo_id"],
        caption=show_profile(p),
        reply_markup=profile_buttons(p["user_id"])
    )


@router.message(F.text == "/start")
async def start(m: Message, state: FSMContext):
    db.init_db()
    await state.clear()

    u = db.get_user(m.from_user.id)

    if u and u["approved"]:
        await m.answer(
            "⭐ A_Match ga xush kelibsiz!",
            reply_markup=menu()
        )
        return

    await state.set_state(Reg.age)
    await m.answer(
        "⭐ A_Match ga xush kelibsiz!\n\n"
        "Yoshingizni kiriting (15 yoshdan boshlab)."
    )


@router.message(Reg.age)
async def age(m: Message, state: FSMContext):
    try:
        n = int(m.text)
    except (ValueError, TypeError):
        await m.answer("Yoshingizni raqam bilan kiriting.")
        return

    if n < 15 or n > 100:
        await m.answer("15 dan 100 gacha bo‘lgan yoshni kiriting.")
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
        await m.answer("Ismingizni yozing.")
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
        "O‘zingiz haqingizda yozing yoki o‘tkazib yuboring:",
        reply_markup=kb
    )


@router.message(Reg.bio)
async def bio(m: Message, state: FSMContext):
    text = (
        "" if m.text == "⏭ O‘tkazib yuborish"
        else (m.text or "")[:300]
    )

    await state.update_data(bio=text)
    await state.set_state(Reg.photo)
    await m.answer("🤳 Profil rasmingizni yuboring.")


@router.message(Reg.photo, F.photo)
async def photo(m: Message, state: FSMContext):
    d = await state.get_data()

    db.save_user(
        m.from_user.id,
        **d,
        photo_id=m.photo[-1].file_id,
        username=m.from_user.username,
        approved=1,
        created_at=db.now()
    )

    await state.clear()
    await m.answer(
        "✅ Profil ma’lumotlari saqlandi!\n"
        "🎉 A_Match dan foydalanishingiz mumkin.",
        reply_markup=menu()
    )


@router.message(Reg.photo)
async def wrong_photo(m: Message):
    await m.answer("Iltimos, profil rasmini yuboring.")


@router.message(F.text == "🔎 Qidirish")
async def search(m: Message):
    await send_next_profile(m)


@router.callback_query(F.data.startswith("like:"))
async def like(c: CallbackQuery):
    if not user_active(c.from_user.id):
        await c.answer("Avval profil yarating.", show_alert=True)
        return

    target = int(c.data.split(":")[1])

    if target == c.from_user.id:
        await c.answer("O‘zingizga layk bosolmaysiz.")
        return

    p = db.get_user(target)

    if not p or not p["approved"] or not p["is_active"]:
        await c.answer("Bu profil mavjud emas.")
        return

    # Voyaga yetmaganlar va kattalar o‘rtasida
    # layk aloqasi yaratilmaydi.
    me = db.get_user(c.from_user.id)

    if (me["age"] < 18) != (p["age"] < 18):
        await c.answer(
            "Bu profil sizning yosh guruhingizga mos emas.",
            show_alert=True
        )
        return

    mutual = db.add_like(c.from_user.id, target)

    if mutual:
        await c.answer("O‘zaro layk! ❤️")
        await c.message.answer(
            "❤️ Sizlarda o‘zaro qiziqish bor! "
            "Shaxsiy chat avtomatik ochilmaydi."
        )
    else:
        await c.answer("Layk yuborildi ❤️")

    await c.message.delete()


@router.callback_query(F.data.startswith("skip:"))
async def skip(c: CallbackQuery):
    target = int(c.data.split(":")[1])

    if target == c.from_user.id:
        await c.answer("Bu amalni bajarib bo‘lmaydi.")
        return

    db.add_skip(c.from_user.id, target)

    await c.answer("Keyingi profil 👎🏻")
    await c.message.delete()


@router.message(F.text == "💗 Menga kim layk bosdi")
async def likes(m: Message):
    if not user_active(m.from_user.id):
        await m.answer("Avval profilingizni yarating.")
        return

    rows = db.received_likes(m.from_user.id)

    if not rows:
        await m.answer("Hozircha sizga layk bosishmagan.")
        return

    for p in rows[:20]:
        await m.answer(
            f"❤️ {p['name']}\n"
            f"📍 {p['city'] or 'Ko‘rsatilmagan'}"
        )


@router.callback_query(F.data.startswith("block:"))
async def block(c: CallbackQuery):
    target = int(c.data.split(":")[1])

    if target == c.from_user.id:
        await c.answer("O‘zingizni bloklay olmaysiz.")
        return

    db.block_user(c.from_user.id, target)

    await c.answer("Foydalanuvchi bloklandi.", show_alert=True)

    try:
        await c.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("report:"))
async def report(c: CallbackQuery):
    target = int(c.data.split(":")[1])

    if target == c.from_user.id:
        await c.answer("O‘zingiz haqida shikoyat yuborib bo‘lmaydi.")
        return

    report_id = db.report_user(
        c.from_user.id,
        target,
        "Profil bo‘yicha shikoyat"
    )

    if report_id and ADMIN_ID:
        try:
            await c.bot.send_message(
                ADMIN_ID,
                f"⚠️ Yangi shikoyat\n"
                f"ID: {report_id}\n"
                f"Yuboruvchi: {c.from_user.id}\n"
                f"Profil: {target}"
            )
        except Exception:
            pass

    await c.answer(
        "Shikoyatingiz yuborildi. Rahmat!",
        show_alert=True
    )


@router.message(F.text == "⚙️ Anketa sozlamalari")
async def settings(m: Message):
    if not user_active(m.from_user.id):
        await m.answer("Avval profilingizni yarating.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Ismni o‘zgartirish",
            callback_data="edit:name"
        )],
        [InlineKeyboardButton(
            text="Bio o‘zgartirish",
            callback_data="edit:bio"
        )],
        [InlineKeyboardButton(
            text="Rasmni o‘zgartirish",
            callback_data="edit:photo"
        )]
    ])

    await m.answer(
        "⚙️ Qaysi ma’lumotni o‘zgartirmoqchisiz?",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("edit:"))
async def edit_start(c: CallbackQuery, state: FSMContext):
    field = c.data.split(":")[1]

    if not user_active(c.from_user.id):
        await c.answer("Avval profil yarating.", show_alert=True)
        return

    if field == "name":
        await state.set_state(EditProfile.name)
        await c.message.answer("Yangi ismingizni kiriting:")

    elif field == "bio":
        await state.set_state(EditProfile.bio)
        await c.message.answer(
            "Yangi bio yozing yoki /cancel yuboring:"
        )

    elif field == "photo":
        await state.set_state(EditProfile.photo)
        await c.message.answer("Yangi rasm yuboring.")

    await c.answer()


@router.message(EditProfile.name)
async def edit_name(m: Message, state: FSMContext):
    if not m.text:
        await m.answer("Ismni matn ko‘rinishida yuboring.")
        return

    db.save_user(m.from_user.id, name=m.text[:40])
    await state.clear()
    await m.answer("✅ Ism yangilandi.", reply_markup=menu())


@router.message(EditProfile.bio)
async def edit_bio(m: Message, state: FSMContext):
    if m.text == "/cancel":
        await state.clear()
        await m.answer("Bekor qilindi.", reply_markup=menu())
        return

    db.save_user(m.from_user.id, bio=(m.text or "")[:300])
    await state.clear()
    await m.answer("✅ Bio yangilandi.", reply_markup=menu())


@router.message(EditProfile.photo, F.photo)
async def edit_photo(m: Message, state: FSMContext):
    db.save_user(
        m.from_user.id,
        photo_id=m.photo[-1].file_id
    )

    await state.clear()
    await m.answer("✅ Rasm yangilandi.", reply_markup=menu())


@router.message(EditProfile.photo)
async def edit_photo_wrong(m: Message):
    await m.answer("Iltimos, rasm yuboring.")


@router.message(F.text == "💎 PREMIUM")
async def premium(m: Message):
    await m.answer(
        "💎 PREMIUM\n\n"
        f"1 hafta — {PREMIUM_WEEK_PRICE:,} so‘m\n"
        f"1 oy — {PREMIUM_MONTH_PRICE:,} so‘m\n\n"
        "To‘lov va obuna imkoniyatlari hozircha "
        "faqat admin orqali boshqariladi."
    )


@router.message(F.text == "/stats")
async def stats(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    await m.answer(
        f"👥 Jami profillar: {db.count_users()}"
    )


@router.message(F.text == "/cancel")
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Bekor qilindi.",
        reply_markup=menu()
    )
