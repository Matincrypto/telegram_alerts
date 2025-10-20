import requests
import json

# --- تنظیمات شما ---
API_URL = "http://103.75.198.172:5005/Internal/arbitrage"
BOT_TOKEN = "7435237309:AAEAXXkce1VU8Wk-NqxX1v6VKnSMaydbErs"
CHAT_ID = "-1002964082215"
TOPIC_ID = "228782"  # در API تلگرام به این 'message_thread_id' می‌گویند
# --------------------

def fetch_arbitrage_data():
    """از API شما داده‌ها را دریافت می‌کند."""
    try:
        # یک مهلت زمانی (timeout) هم برای جلوگیری از قفل شدن اسکریپت در نظر می‌گیریم
        response = requests.get(API_URL, timeout=10)
        
        # اگر درخواست ناموفق بود (مثلاً خطای 500 یا 404)، خطا ایجاد می‌کند
        response.raise_for_status()
        
        # پاسخ را به صورت JSON برمی‌گرداند
        return response.json()
    except requests.exceptions.HTTPError as errh:
        print(f"خطای HTTP: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"خطای اتصال: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"خطای تایم‌اوت (پاسخ‌دهی API طول کشید): {errt}")
    except requests.exceptions.RequestException as err:
        print(f"خطا در درخواست: {err}")
    except json.JSONDecodeError:
        print("خطا در پارس کردن JSON. آیا خروجی API معتبر است؟")
    return None

def format_message(data):
    """داده‌های JSON را به یک پیام متنی ساده مطابق خواسته شما تبدیل می‌کند."""
    
    # ابتدا چک می‌کنیم که آیا داده‌ای وجود دارد و آیا لیستی از فرصت‌ها در آن هست یا نه
    if not data or 'opportunities' not in data or not data['opportunities']:
        # اگر فرصتی یافت نشد، می‌توانید پیامی مبنی بر عدم وجود فرصت ارسال کنید
        # یا اینکه اصلاً پیامی ارسال نکنید (در این صورت None برگردانید)
        return "در حال حاضر فرصت آربیتراژی یافت نشد."

    message_parts = ["🔔 فرصت‌های آربیتراژ یافت شده:\n"]
    
    for opp in data['opportunities']:
        # اطلاعات را با .get() می‌خوانیم تا اگر کلیدی وجود نداشت، برنامه خطا ندهد
        asset = opp.get('asset_name', '؟')
        entry = opp.get('entry_price', '؟')
        exit_price = opp.get('exit_price', '؟')
        strategy = opp.get('strategy_name', '؟')
        
        # ساخت پیام ساده مطابق درخواست شما
        # افزودن نام ارز (asset_name) به خوانایی پیام کمک می‌کند
        part = (
            f"ارز: {asset}\n"
            f"استراتژی: {strategy}\n"
            f"قیمت ورود: {entry}\n"
            f"قیمت خروج: {exit_price}"
        )
        message_parts.append(part)
    
    # پیام‌ها را با دو خط جدید از هم جدا می‌کنیم تا خواناتر باشند
    return "\n\n".join(message_parts)

def send_to_telegram(message):
    """پیام متنی نهایی را به تاپیک مشخص شده در تلگرام ارسال می‌کند."""
    
    # آدرس API تلگرام برای ارسال پیام
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # داده‌هایی که باید برای تلگرام ارسال شوند
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'message_thread_id': TOPIC_ID  # این پارامتر برای ارسال به تاپیک است
    }
    
    try:
        response = requests.post(telegram_url, json=payload, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            print("پیام با موفقیت به تلگرام ارسال شد.")
        else:
            # نمایش خطای احتمالی از سمت تلگرام
            print(f"خطا در ارسال به تلگرام: {response_data.get('description', 'خطای ناشناخته')}")
    except requests.exceptions.RequestException as e:
        print(f"خطا در اتصال به API تلگرام: {e}")

def main():
    """تابع اصلی برای اجرای اسکریپت."""
    print("در حال دریافت داده‌ها از API...")
    data = fetch_arbitrage_data()
    
    if data:
        print("داده‌ها دریافت شد، در حال فرمت‌بندی پیام...")
        message = format_message(data)
        
        if message:
            print(f"پیام آماده ارسال:\n{message}")
            print("\nدر حال ارسال پیام به تلگرام...")
            send_to_telegram(message)
        else:
            print("پیامی برای ارسال آماده نشد (احتمالاً فرصتی یافت نشده).")
    else:
        print("دریافت داده‌ها از API ناموفق بود. پیامی ارسال نشد.")

# اجرای تابع اصلی
if __name__ == "__main__":
    main()
