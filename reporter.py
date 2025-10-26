# reporter.py
import logging
import io
import pandas as pd
from datetime import datetime
from decimal import Decimal
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# این فایل‌ها باید در همین پوشه باشند
import config
import db_utils

# تنظیمات لاگ‌گیری
logging.basicConfig(level=config.BOT["LOG_LEVEL"], format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# متن دکمه
REPORT_BUTTON_TEXT = "📊 دریافت گزارش مالی"

# دکوراتور برای محدود کردن دسترسی فقط به ادمین
def restricted(func):
    """دسترسی به دستور را فقط به ادمین تعریف شده در کانفیگ محدود می‌کند."""
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != config.TELEGRAM["ADMIN_CHAT_ID"]:
            logger.warning(f"دسترسی غیرمجاز به ربات گزارش‌گیر از ID: {user_id}")
            update.message.reply_text("شما مجاز به استفاده از این ربات نیستید.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def calculate_profit(row):
    """
    سود دقیق را بر اساس قیمت‌های سفارش‌گذاری محاسبه می‌کند.
    """
    try:
        # هزینه خرید به تومان
        # (مقدار خالص دریافتی + کارمزد ارز) * قیمت ورود
        gross_buy_qty = Decimal(row['buy_executed_quantity']) + Decimal(row['buy_fee'])
        cost_tmn = gross_buy_qty * Decimal(row['entry_price'])
        
        # درآمد فروش به تومان
        # (مقدار فروخته شده * قیمت خروج)
        revenue_tmn = Decimal(row['sell_executed_quantity']) * Decimal(row['exit_price'])
        
        # کارمزد فروش (که از قبل به تومان است)
        sell_fee_tmn = Decimal(row['sell_fee'])
        
        # سود خالص
        profit = revenue_tmn - cost_tmn - sell_fee_tmn
        
        return profit, cost_tmn, revenue_tmn
        
    except Exception as e:
        logger.error(f"خطا در محاسبه سود برای ردیف {row.get('id')}: {e}")
        return None, None, None


def fetch_report_data():
    """
    داده‌های حسابرسی را از دیتابیس استخراج و پردازش می‌کند.
    """
    query = "SELECT * FROM trade_signals"
    all_trades = db_utils.query_db(query, fetch='all')
    
    if not all_trades:
        return None
        
    df = pd.DataFrame(all_trades)
    
    # --- محاسبات اصلی ---
    
    # 1. سود/زیان تحقق یافته
    completed_trades = df[df['status'] == 'SELL_ORDER_FILLED'].copy()
    
    if not completed_trades.empty:
        profit_data = completed_trades.apply(calculate_profit, axis=1, result_type='expand')
        profit_data.columns = ['profit_tmn', 'cost_tmn', 'revenue_tmn']
        completed_trades = pd.concat([completed_trades, profit_data], axis=1)
        total_realized_profit = completed_trades['profit_tmn'].sum()
    else:
        total_realized_profit = 0

    # 2. آمار کلی
    total_trades = len(df)
    successful_trades = len(completed_trades)
    canceled_trades = len(df[df['status'] == 'CANCELED_TIMEOUT'])
    error_trades = len(df[df['status'] == 'ERROR'])
    
    # 3. پوزیشن‌های باز (سود تحقق نیافته)
    open_positions_df = df[df['status'].isin(['BUY_ORDER_FILLED', 'SELL_ORDER_PLACED'])].copy()
    
    if not open_positions_df.empty:
        # (مقدار خالص + کارمزد ارز) * قیمت ورود
        open_positions_df['cost_tmn'] = (
            pd.to_numeric(open_positions_df['buy_executed_quantity']) + 
            pd.to_numeric(open_positions_df['buy_fee'])
        ) * pd.to_numeric(open_positions_df['entry_price'])
        total_invested_in_open = open_positions_df['cost_tmn'].sum()
    else:
        total_invested_in_open = 0

    # --- ساخت دیکشنری خلاصه ---
    summary = {
        "total_realized_profit_tmn": total_realized_profit,
        "total_trades_initiated": total_trades,
        "successful_trades_completed": successful_trades,
        "canceled_by_timeout": canceled_trades,
        "trades_with_error": error_trades,
        "current_open_positions": len(open_positions_df),
        "total_invested_in_open_positions": total_invested_in_open
    }
    
    return summary, completed_trades, open_positions_df

def create_excel_report(report_data):
    """
    گزارش را در قالب یک فایل اکسل در حافظه (in-memory) ایجاد می‌کند.
    """
    summary, completed_trades, open_positions = report_data
    
    output_buffer = io.BytesIO()
    
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        # شیت اول: خلاصه آمار
        df_summary = pd.DataFrame(list(summary.items()), columns=['Metric', 'Value'])
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # شیت دوم: معاملات تکمیل شده (سود/زیان)
        if not completed_trades.empty:
            cols_to_show_completed = [
                'id', 'asset_name', 'created_at', 'status', 
                'cost_tmn', 'revenue_tmn', 'sell_fee', 'profit_tmn',
                'entry_price', 'exit_price', 'buy_executed_quantity'
            ]
            completed_trades[cols_to_show_completed].to_excel(writer, sheet_name='Completed Trades', index=False)
        
        # شیت سوم: پوزیشن‌های باز
        if not open_positions.empty:
            cols_to_show_open = [
                'id', 'asset_name', 'created_at', 'status', 
                'cost_tmn', 'buy_executed_quantity'
            ]
            open_positions[cols_to_show_open].to_excel(writer, sheet_name='Open Positions', index=False)
            
    output_buffer.seek(0)
    return output_buffer

@restricted
def start(update: Update, context: CallbackContext):
    """تابع /start. پیام خوشامد و دکمه گزارش را ارسال می‌کند."""
    
    # ساخت دکمه
    keyboard = [
        [KeyboardButton(REPORT_BUTTON_TEXT)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    update.message.reply_text(
        "سلام ادمین! برای دریافت گزارش مالی روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup
    )

@restricted
def send_report(update: Update, context: CallbackContext):
    """
    هندلر دکمه گزارش. گزارش را تولید و ارسال می‌کند.
    """
    user_name = update.effective_user.first_name
    logger.info(f"درخواست گزارش از کاربر {user_name} (Admin) دریافت شد...")
    update.message.reply_text("در حال تهیه گزارش مالی... لطفاً چند لحظه صبر کنید.")

    try:
        report_data = fetch_report_data()
        
        if not report_data:
            update.message.reply_text("هیچ داده‌ای برای گزارش یافت نشد.")
            return
            
        excel_file_buffer = create_excel_report(report_data)
        
        filename = f"Financial_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
        
        # ارسال فایل اکسل
        context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=excel_file_buffer,
            filename=filename,
            caption="گزارش عملکرد مالی ربات."
        )
        logger.info(f"گزارش با موفقیت برای {user_name} ارسال شد.")

    except Exception as e:
        logger.error(f"خطا در ایجاد یا ارسال گزارش: {e}")
        update.message.reply_text(f"خطا در پردازش گزارش: {e}")

def main_reporter_loop():
    """
    حلقه اصلی ماژول گزارش‌گیری (اجرای ربات تلگرام).
    """
    if not config.TELEGRAM.get("BOT_TOKEN"):
        logger.critical("توکن ربات تلگرام در کانفیگ تنظیم نشده است. ماژول گزارش‌گیری غیرفعال شد.")
        return
    if not config.TELEGRAM.get("ADMIN_CHAT_ID"):
        logger.critical("ADMIN_CHAT_ID در کانفیگ تنظیم نشده است. ماژول گزارش‌گیری غیرفعال شد.")
        return

    updater = Updater(config.TELEGRAM["BOT_TOKEN"], use_context=True)
    dispatcher = updater.dispatcher

    # 1. هندلر دستور /start (برای نمایش دکمه‌ها)
    dispatcher.add_handler(CommandHandler("start", start))
    
    # 2. هندلر دکمه گزارش (فیلتر بر اساس متن دکمه)
    dispatcher.add_handler(MessageHandler(
        Filters.text & Filters.regex(f"^{REPORT_BUTTON_TEXT}$"), 
        send_report
    ))

    logger.info("ماژول گزارش‌گیری (Reporter) شروع به کار کرد و منتظر دستورات تلگرام است...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    # این خط باعث می‌شود فایل مستقیما قابل اجرا باشد
    main_reporter_loop()