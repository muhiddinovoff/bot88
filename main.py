import logging
import json
import os
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------------- Config ----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "7521073611:AAHadp9OahqN9bcGQHCkq6YdEklR8IH51KQ")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5913958185"))  # Set your Telegram numeric ID here
USERS_FILE = os.getenv("USERS_FILE", "users.json")

# Conversation state
ASK_NAME = 1

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------- Storage helpers ----------------------
def _ensure_users_file() -> None:
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_users() -> Dict[str, str]:
    _ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            # Keys must be strings
            return {str(k): str(v) for k, v in data.items()}
    except Exception as e:
        logger.error("Failed to load users.json: %s", e)
        return {}


def save_users(users: Dict[str, str]) -> None:
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Failed to save users.json: %s", e)


def get_name_by_id(user_id: int) -> Optional[str]:
    users = load_users()
    return users.get(str(user_id))


def set_name_for_id(user_id: int, name: str) -> None:
    users = load_users()
    users[str(user_id)] = name.strip()
    save_users(users)


# ---------------------- UI builders ----------------------
def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
    ]
    return InlineKeyboardMarkup(kb)


def users_list_kb() -> InlineKeyboardMarkup:
    users = load_users()
    buttons = []
    # Inline button matni ko'p Telegram mijozlarida ko'k rangda ko'rinadi (mijoz mavzusiga bog'liq).
    for uid, name in users.items():
        text = f"{name}"
        buttons.append([InlineKeyboardButton(text, callback_data=f"user_{uid}")])
    if not buttons:
        buttons = [[InlineKeyboardButton("Hozircha foydalanuvchi yo'q", callback_data="noop")]]
    buttons.append([InlineKeyboardButton("⬅️ Ortga", callback_data="admin_back")])
    return InlineKeyboardMarkup(buttons)


# ---------------------- Handlers ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start bosilganda: ID ni oladi, agar tanish bo'lsa ism bilan salomlaydi,
    aks holda ism so'raydi va saqlaydi."""
    user = update.effective_user
    if user is None:
        return ConversationHandler.END

    uid = user.id
    name = get_name_by_id(uid)

    if name:
        await update.message.reply_text(f"Salom, {name}! Qaytib kelganingizdan xursandmiz 😊")
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "🤖 Xush kelibsiz!\n\nIsmingizni yozing (masalan: \"Mirkomil\")."
        )
        return ASK_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi ism yuborganida saqlash."""
    user = update.effective_user
    if user is None:
        return ConversationHandler.END

    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text("Ismingizni to'g'ri kiriting, iltimos.")
        return ASK_NAME

    set_name_for_id(user.id, name)
    await update.message.reply_text(f"Rahmat, {name}! Ma'lumot saqlandi ✅")
    return ConversationHandler.END


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun bosh menyu."""
    uid = update.effective_user.id if update.effective_user else 0
    if ADMIN_ID and uid != ADMIN_ID:
        await update.message.reply_text("⛔ Bu bo'lim faqat admin uchun.")
        return

    await update.message.reply_text("🛠 Admin panel", reply_markup=admin_menu_kb())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline tugmalar uchun umumiy handler."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    # Admin filtri
    uid = query.from_user.id if query.from_user else 0
    if ADMIN_ID and uid != ADMIN_ID:
        await query.edit_message_text("⛔ Bu bo'lim faqat admin uchun.")
        return

    data = query.data or ""

    if data == "admin_users":
        users = load_users()
        count = len(users)
        header = f"👥 Foydalanuvchilar: {count} ta\n\nQuyidan foydalanuvchini tanlang:"
        await query.edit_message_text(header, reply_markup=users_list_kb())
        return

    if data == "admin_back":
        await query.edit_message_text("🛠 Admin panel", reply_markup=admin_menu_kb())
        return

    if data.startswith("user_"):
        target_id = data.split("_", 1)[1]
        users = load_users()
        name = users.get(target_id, "Noma'lum")
        text = (
            f"👤 Foydalanuvchi profili\n"
            f"• Ism: {name}\n"
            f"• Telegram ID: `{target_id}`\n\n"
            f"⬅️ Ortga qaytish uchun pastdagi tugmadan foydalaning."
        )
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⬅️ Foydalanuvchilar ro'yxati", callback_data="admin_users")],
                [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_back")],
            ]
        )
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        return

    # No-op
    if data == "noop":
        return


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oddiy xabarlar uchun: tanish foydalanuvchiga ismi bilan murojaat qiladi."""
    user = update.effective_user
    if not user or not update.message:
        return

    name = get_name_by_id(user.id)
    if name:
        await update.message.reply_text(f"{name}, xabaringiz qabul qilindi!")
    else:
        await update.message.reply_text("Ismingizni saqlash uchun /start ni bosing. 🙂")


def main():
    _ensure_users_file()

    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        logger.error("BOT_TOKEN o'rnatilmagan. Iltimos, kodda yoki muhitda BOT_TOKEN ni belgilang.")
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)]},
        fallbacks=[],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
