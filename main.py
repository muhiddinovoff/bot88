import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# --- Sozlamalar ---
BOT_TOKEN = "7521073611:AAHadp9OahqN9bcGQHCkq6YdEklR8IH51KQ"
ADMIN_ID = 5913958185  # O‘zingizning Telegram ID’ingiz
USERS_FILE = "users.json"
ASK_NAME = 1

# --- Log sozlash ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- JSON foydalanuvchi fayl bilan ishlash ---
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


# --- /start komandasi ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Xush kelibsiz!\n\nIsmingizni kiriting:")
    return ASK_NAME


# --- Ismni qabul qilish ---
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    name = update.message.text.strip()

    users = load_users()
    users[user_id] = name
    save_users(users)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 Test yaratish", url="https://newsite1277.infy.uk/creator.html")],
        [InlineKeyboardButton("📝 Test ishlash", url="https://newsite1277.infy.uk/taker.html")],
        [InlineKeyboardButton("📞 Adminga bog‘lanish", url="https://t.me/raschtestbot_admin")]
    ])

    await update.message.reply_text(
        "✅ Rahmat, {0}!\nQuyidagilardan birini tanlang:".format(name),
        reply_markup=keyboard
    )
    return ConversationHandler.END


# --- /admin komandasi ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda admin ruxsati yo‘q.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Foydalanuvchilar soni", callback_data="count_users")],
        [InlineKeyboardButton("📢 Hamma foydalanuvchiga xabar yuborish", callback_data="broadcast")]
    ])

    await update.message.reply_text("⚙️ Admin panel:", reply_markup=keyboard)


# --- Callback tugmalarni ishlovchi ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "count_users":
        users = load_users()
        await query.edit_message_text(f"👥 Foydalanuvchilar soni: {len(users)} ta")

    elif query.data == "broadcast":
        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text("✉️ Yuboriladigan xabar matnini kiriting:")


# --- Admin matn yuborish ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_broadcast") and update.message.from_user.id == ADMIN_ID:
        users = load_users()
        text = update.message.text
        success = 0

        for user_id in users:
            try:
                await context.bot.send_message(chat_id=int(user_id), text=text)
                success += 1
            except Exception as e:
                logger.warning(f"Xatolik: {e}")

        await update.message.reply_text(f"✅ {success} foydalanuvchiga yuborildi.")
        context.user_data["awaiting_broadcast"] = False
    else:
        await update.message.reply_text("❗Iltimos, /start buyrug‘idan boshlang.")


# --- Asosiy botni ishga tushirish ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)]},
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🤖 Bot ishga tushdi...")
    app.run_polling()