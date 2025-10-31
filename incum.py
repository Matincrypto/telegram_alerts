import random # برای انتخاب تصادفی
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# فعال کردن لاگ‌گیری (برای دیدن اطلاعات در کنسول)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- تنظیمات شما ---
# توکن ربات شما
BOT_TOKEN = "7620588620:AAG9J-XhMJUsEMZOD1mb4rjiU55uyfsmy9M"
# شناسه (ID) گروه شما
TARGET_CHAT_ID = -1002684336789

# --- لیست پیام‌های خوش‌آمدگویی تصادفی (به روز شده) ---
WELCOME_MESSAGES = [
    "💎 به تیم ما خوش اومدی! مسیر پیشرفت اینجاست، کنار هم می‌سازیمش. 🚀",
    "👋 سلام به عضو جدید! با حضور شما تیم ما کامل‌تر شد. آماده‌ایم برای فتح قله‌ها! ✨",
    "💡 یه ذهن خلاق دیگه به جمعمون اضافه شد! خوشحالیم که اینجایی، آینده روشن‌تر شد. 🌟",
    "🤩 به تیم خفن ما خوش اومدی! قراره اینجا بترکونیم. حضورت یه دنیا ارزشه! 💪",
    "همراهی شما برای ما یک شروع عالیه. بیا با هم اتفاقای بزرگ بسازیم! 💫",
    "به جمع حرفه‌ای‌ها خوش اومدی! اینجا هر روز برای بهتر شدن تلاش می‌کنیم. 📈",
    "سلام! حضورت انرژی‌بخش تیم ماست. مشتاقیم با هم رشد کنیم. 🌱",
    "درب‌های موفقیت به روت بازه! به تیم ما خوش اومدی، اینجا همه حامی همیم. 🤝",
    "یه ستاره جدید به تیم اضافه شد! خوشحالیم که اینجایی، بیا بدرخشیم. 🌠",
    "به خانواده جدیدت خوش اومدی! اینجا ایده‌های تو برامون مهمه. 💡"
]

# --- تابع خوش‌آمدگویی به عضو جدید ---
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if chat_id != TARGET_CHAT_ID:
        logger.info(f"آپدیت از چت {chat_id} نادیده گرفته شد، زیرا چت هدف {TARGET_CHAT_ID} نیست.")
        return

    if update.message and update.message.new_chat_members:
        for user in update.message.new_chat_members:
            if not user.is_bot:
                chosen_message = random.choice(WELCOME_MESSAGES)
                
                # --- اضافه کردن تگ کاربر ---
                # ساخت لینک تگ کاربر
                # اگر کاربر نام کاربری داشته باشد، می توان از @username استفاده کرد، اما tg://user?id=USER_ID مطمئن تر است
                user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
                if user.last_name:
                    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name} {user.last_name}</a>'
                # --- پایان اضافه کردن تگ کاربر ---
                
                # نام کاربر تگ شده در ابتدای پیام اضافه می‌شود
                welcome_text = f"{user_mention} {chosen_message}"

                try:
                    await context.bot.send_message(
                        chat_id=TARGET_CHAT_ID,
                        text=welcome_text,
                        parse_mode='HTML' # parse_mode باید HTML باشد تا تگ کار کند
                    )
                    logger.info(f"پیام خوش‌آمدگویی تصادفی به {user.first_name} ({user.id}) در چت {chat_id} ارسال شد.")
                except Exception as e:
                    logger.error(f"ارسال پیام خوش‌آمدگویی با خطا مواجه شد: {e}")
                    logger.error("اطمینان حاصل کنید ربات در گروه ادمین است و دسترسی ارسال پیام و مدیریت تاپیک‌ها را دارد.")
            else:
                logger.info(f"خوش‌آمدگویی به ربات {user.first_name} نادیده گرفته شد.")
    else:
        logger.debug("هیچ عضو جدیدی در این آپدیت شناسایی نشد.")

# --- تابع اصلی برای اجرای ربات ---
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    logger.info("ربات راه‌اندازی شد و در حال گوش دادن برای اعضای جدید است...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()