from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID
import database as db
from face_check import contains_face

router=Router()

class Reg(StatesGroup):
    age=State(); city=State(); name=State(); gender=State(); bio=State(); photo=State()

def menu():
    return ReplyKeyboardMarkup(keyboard=[
      [KeyboardButton(text="🔎 Qidirish"),KeyboardButton(text="⚙️ Anketa sozlamalari")],
      [KeyboardButton(text="💗 Menga kim layk bosdi"),KeyboardButton(text="💜 VIP CHAT")],
      [KeyboardButton(text="💎 PREMIUM")]
    ], resize_keyboard=True)

@router.message(F.text=="/start")
async def start(m:Message,state:FSMContext):
    db.init_db()
    u=db.get_user(m.from_user.id)
    if u and u["approved"]:
        await m.answer("⭐ Xush kelibsiz! Menyudan kerakli bo‘limni tanlang.",reply_markup=menu()); return
    await state.set_state(Reg.age)
    await m.answer("🔞 Bu xizmat faqat 18 yoshdan kattalar uchun. Yoshingizni kiriting:")

@router.message(Reg.age)
async def age(m:Message,state:FSMContext):
    try: n=int(m.text)
    except: await m.answer("Yoshingizni raqam bilan kiriting."); return
    if n<18:
        await state.clear()
        await m.answer("Kechirasiz, ushbu xizmat 18+ foydalanuvchilar uchungina. Ro‘yxatdan o‘tish davom ettirilmaydi.")
        return
    if n>100: await m.answer("Yoshni tekshirib qayta kiriting."); return
    await state.update_data(age=n); await state.set_state(Reg.city)
    await m.answer("📍 Qaysi shahardansiz? Faqat shahar nomini yozing. Aniq manzil yubormang.")

@router.message(Reg.city)
async def city(m:Message,state:FSMContext):
    await state.update_data(city=m.text[:50]); await state.set_state(Reg.name)
    await m.answer("Ismingizni kiriting:")

@router.message(Reg.name)
async def name(m:Message,state:FSMContext):
    await state.update_data(name=m.text[:40]); await state.set_state(Reg.gender)
    kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Erkak"),KeyboardButton(text="Ayol")]],resize_keyboard=True)
    await m.answer("Jinsingizni tanlang:",reply_markup=kb)

@router.message(Reg.gender)
async def gender(m:Message,state:FSMContext):
    if m.text not in ("Erkak","Ayol"):
        await m.answer("Erkak yoki Ayol tugmasini tanlang."); return
    await state.update_data(gender=m.text); await state.set_state(Reg.bio)
    await m.answer("O‘zingiz haqingizda qisqacha yozing:")

@router.message(Reg.bio)
async def bio(m:Message,state:FSMContext):
    await state.update_data(bio=m.text[:300]); await state.set_state(Reg.photo)
    await m.answer("🤳 Yuzingiz aniq ko‘rinadigan o‘zingizning rasmingizni yuboring. Guruh rasmlari qabul qilinmaydi.")

@router.message(Reg.photo, F.photo)
async def photo(m:Message,state:FSMContext):
    file=await m.bot.get_file(m.photo[-1].file_id)
    data=await m.bot.download_file(file.file_path)
    raw=data.read()
    if not contains_face(raw):
        await m.answer("❌ Rasmda yuz aniqlanmadi. Yuz aniq ko‘rinadigan boshqa rasm yuboring."); return
    d=await state.get_data()
    db.save_user(m.from_user.id, **d, photo_id=m.photo[-1].file_id,
      username=m.from_user.username, approved=1, created_at="")
    await state.clear()
    await m.answer("✅ Profil yaratildi! Endi tanishuvni boshlashingiz mumkin.",reply_markup=menu())

@router.message(Reg.photo)
async def wrong_photo(m:Message):
    await m.answer("Iltimos, rasm yuboring. Video yoki matn qabul qilinmaydi.")

@router.message(F.text=="🔎 Qidirish")
async def search(m:Message):
    u=db.get_user(m.from_user.id)
    if not u or not u["approved"]: await m.answer("Avval /start orqali anketa yarating."); return
    p=db.next_profile(m.from_user.id,u["gender"])
    if not p: await m.answer("Hozircha yangi profil topilmadi. Keyinroq urinib ko‘ring."); return
    kb=InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(text="❤️",callback_data=f"like:{p['user_id']}"),
      InlineKeyboardButton(text="👎",callback_data=f"skip:{p['user_id']}")
    ]])
    caption=f"<b>{p['name']}</b>, {p['age']} yosh\n📍 {p['city']}\n\n{p['bio']}"
    await m.answer_photo(p["photo_id"],caption=caption,reply_markup=kb)

@router.callback_query(F.data.startswith("like:"))
async def like(c:CallbackQuery):
    target=int(c.data.split(":")[1])
    mutual=db.add_like(c.from_user.id,target)
    if mutual:
        a=db.get_user(c.from_user.id); b=db.get_user(target)
        await c.message.answer("💞 Sizlarda o‘zaro Match! Kontakt so‘rovi yuborish uchun Premium bo‘limidan foydalaning.")
        try: await c.bot.send_message(target,f"💞 {a['name']} sizga ham layk bosdi. Sizlarda Match bor!")
        except: pass
    else: await c.answer("Layk yuborildi ❤️")
    await c.message.delete()

@router.callback_query(F.data.startswith("skip:"))
async def skip(c:CallbackQuery):
    await c.answer("O‘tkazib yuborildi")
    await c.message.delete()

@router.message(F.text=="💗 Menga kim layk bosdi")
async def likes(m:Message):
    if not db.is_premium(m.from_user.id):
        await m.answer("🔒 Bu bo‘lim Premium foydalanuvchilar uchun. 💎 PREMIUM bo‘limini oching."); return
    rows=db.received_likes(m.from_user.id)
    if not rows: await m.answer("Hozircha sizga layk bosishmagan."); return
    for p in rows[:20]:
        await m.answer(f"❤️ {p['name']}, {p['age']} yosh — {p['city']}")

@router.message(F.text=="💎 PREMIUM")
async def premium(m:Message):
    await m.answer("💎 <b>PREMIUM OBUNA</b>\n\n✨ 1 hafta — 25 000 so‘m\n✨ 1 oy — 50 000 so‘m\n\nPremium: sizga layk bosganlarni ko‘rish va Matchdan keyin kontakt so‘rovi yuborish.\n\nTo‘lov uchun bot egasi bilan bog‘laning. To‘lov tasdiqlanmaguncha obuna yoqilmaydi.",
      reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 hafta — 25 000 so‘m",callback_data="buy:7")],
        [InlineKeyboardButton(text="1 oy — 50 000 so‘m",callback_data="buy:30")]
      ]))

@router.callback_query(F.data.startswith("buy:"))
async def buy(c:CallbackQuery):
    days=int(c.data.split(":")[1])
    price="25 000" if days==7 else "50 000"
    await c.message.answer(f"💎 {days} kunlik Premium: {price} so‘m.\nTo‘lovni faqat tasdiqlangan xavfsiz to‘lov usuli orqali amalga oshiring. Hozircha admin bilan bog‘laning: /support")
    await c.answer()

@router.message(F.text=="/support")
async def support(m:Message):
    await m.answer("To‘lov bo‘yicha admin bilan bog‘lanish: bot egasi ADMIN_ID orqali sozlanadi.")

@router.message(F.text=="⚙️ Anketa sozlamalari")
async def settings(m:Message):
    await m.answer("Anketani o‘chirish yoki yangilash uchun admin bilan bog‘laning. Keyingi versiyada tahrirlash menyusi qo‘shiladi.")

@router.message(F.text=="💜 VIP CHAT")
async def vip(m:Message):
    await m.answer("💜 VIP CHAT — hozircha guruh havolasi admin tomonidan sozlanadi.")

@router.message(F.text=="/stats")
async def stats(m:Message):
    if m.from_user.id!=ADMIN_ID: return
    await m.answer(f"👥 Tasdiqlangan profillar: {db.count_users()}")
