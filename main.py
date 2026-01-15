import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.filters import Command

# --- SOZLAMALAR ---
BOT_TOKEN = "8413845155:AAHBLmNecBHW1DHyhMorqgDNLOojVTVgJxo"
GROUP_ID = -1001410191264  # Guruhning haqiqiy ID'si (manfiy son bo'ladi)
ADMIN_CONTACT = "@beknazarovuz"

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS verified_users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user_to_db(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO verified_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except: pass
    conn.close()

def remove_user_from_db(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM verified_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_user_verified(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM verified_users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

# --- RUXSATLAR ---
# Faqat o'qish mumkin, yozish mumkin emas
RESTRICTED = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_voice_notes=False,
    can_send_polls=False
)

# Hamma narsa mumkin
UNRESTRICTED = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_invite_users=True
)

router = Router()

# --- 1. GURUHGA KIRISH NAZORATI (Yangi qo'shilgan) ---
@router.message(F.new_chat_members)
async def on_user_join(message: Message):
    for user in message.new_chat_members:
        # User guruhga kirishi bilan uni bazadan o'chiramiz.
        # Bu uning "eski ruxsatlarini" bekor qiladi.
        remove_user_from_db(user.id)

    # Kirish xabarini o'chirish (ixtiyoriy)
    try:
        await message.delete()
    except: pass


# --- 2. GURUHDA XABARNI USHLASH ---
@router.message(F.chat.type.in_({"group", "supergroup"}))
async def group_handler(message: Message, bot: Bot):
    user = message.from_user
    chat_id = message.chat.id

    # Adminlarni o'tkazib yuboramiz
    member = await bot.get_chat_member(chat_id, user.id)
    if member.status in ['creator', 'administrator']:
        return

    # Agar user bazada bo'lsa, indamaymiz
    if is_user_verified(user.id):
        return

    # --- AGAR BAZADA YO'Q BO'LSA ---

    # 1. Xabarni o'chiramiz
    try:
        await message.delete()
    except: pass

    # 2. Userni cheklaymiz
    try:
        await bot.restrict_chat_member(chat_id, user.id, RESTRICTED)
    except: pass

    # 3. Link beramiz
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=verify_{user.id}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Avtorizatsiyadan o'tish", url=link)]
    ])

    msg = await message.answer(
        f"⛔️ **{user.full_name}**, guruhda yozish uchun tasdiqlashdan o'ting!",
        reply_markup=kb
    )

    # 15 soniyadan keyin ogohlantirishni o'chiramiz
    await asyncio.sleep(15)
    try:
        await msg.delete()
    except: pass


# --- 3. GURUHDA CHIQIB KETISH NAZORATI ---
@router.message(F.left_chat_member)
async def on_user_leave(message: Message):
    if message.left_chat_member:
        remove_user_from_db(message.left_chat_member.id)
    try:
        await message.delete()
    except: pass


# --- 4. START (Shaxsiy chatda) ---
@router.message(Command("start"), F.chat.type == "private")
async def start_handler(message: Message, bot: Bot):
    args = message.text.split()
    user_id = message.from_user.id

    if len(args) > 1 and "verify" in args[1]:
        # 1. Bazaga qo'shamiz
        add_user_to_db(user_id)

        # 2. Guruhda ruxsat beramiz
        try:
            await bot.restrict_chat_member(
                chat_id=GROUP_ID, # TEPADAGI ID TO'G'RI BO'LISHI SHART
                user_id=user_id,
                permissions=UNRESTRICTED
            )
            await message.answer("✅ **Tasdiqlandi!** Guruhda yozishingiz mumkin.")
        except Exception as e:
            await message.answer(f"⚠️ Xatolik: {e}\nGuruh ID sini tekshiring.")
    else:
        await message.answer("Botga xush kelibsiz! Guruhdan kiring.")


async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Webhookni tozalash
    await bot.delete_webhook(drop_pending_updates=True)

    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass