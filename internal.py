import requests
import json
import time
import sys

# --- تنظیمات شما ---
API_URL = "http://103.75.198.172:5005/Internal/arbitrage"
BOT_TOKEN = "7435237309:AAEAXXkce1VU8Wk-NqxX1v6VKnSMaydbErs"

# CHAT_ID به‌روزرسانی شد
CHAT_ID = "-1002684336789" 

# !!! هشدار: این شناسه به احتمال زیاد اشتباه است و باعث خطای 'message thread not found' می‌شود
# !!! لطفاً شناسه تاپیک صحیح را پیدا کرده و جایگزین کنید
TOPIC_ID = "228782" 

# --- پروکسی (در صورت نیاز در سرور ایران) ---
PROXIES = {
    # 'https': 'socks5h://127.0.0.1:1080'
}
# --------------------

def fetch_arbitrage_data():
    """از API شما داده‌ها را دریافت می‌کند."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as errh:
        print(f"خطای HTTP از API آربیتراژ: {errh}")
    except requests.exceptions.RequestException as err:
        print(f"خطا در اتصال به API آربیتراژ: {err}")
    except json.JSONDecodeError:
        print("خطا در پارس کردن JSON. خروجی API معتبر نیست.")
    return None

def format_message(data):
    """
    داده‌های JSON را به پیام متنی انگلیسی مطابق فرمت درخواستی تبدیل می‌کند.
    """
    if not data or 'opportunities' not in data or not data['opportunities']:
        return None  # اگر فرصتی نبود، None برگردان

    message_parts = ["🔔 **Arbitrage Opportunities Found**\n"]
    
    for opp in data['opportunities']:
        asset = opp.get('asset_name', 'N/A')
        pair = opp.get('pair', 'N/A')
        entry_price = opp.get('entry_price', 'N/A')
        exit_price = opp.get('exit_price', 'N/A')
        strategy = opp.get('strategy_name', 'N/A')
        exchange = opp.get('exchange_name', 'N/A') 
        profit = opp.get('expected_profit_percentage', 0)
        
        try:
            profit_formatted = f"{float(profit):.2f}%"
        except (ValueError, TypeError):
            profit_formatted = f"{profit}%"

        part = (
            f"**{asset}**\n\n"
            f"  Pair: {pair}\n"
            f"  Entry Price ({exchange}): {entry_price}\n"
            f"  Exit Price ({exchange}): {exit_price}\n"
            f"  Expected Profit: **{profit_formatted}**\n"
            f"  Strategy: {strategy}"
        )
        message_parts.append(part)
    
    return "\n\n---\n\n".join(message_parts)

def send_to_telegram(message):
    """پیام را به تلگرام ارسال می‌کند."""
    
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'message_thread_id': TOPIC_ID,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(telegram_url, json=payload, proxies=PROXIES, timeout=20)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            print(">>> پیام آربیتراژ با موفقیت به تلگرام ارسال شد. <<<")
        else:
            # خطای 'message thread not found' اینجا نمایش داده می‌شود
            print(f"!!! خطا در ارسال به تلگرام: {response_data.get('description', 'خطای ناشناخته')} !!!")
    
    except requests.exceptions.ProxyError as e:
        print(f"!!! خطا در اتصال به پروکسی: {e} !!!")
    except requests.exceptions.RequestException as e:
        print(f"!!! خطا در اتصال به API تلگرام: {e} !!!")

def main():
    """تابع اصلی برای اجرای اسکریپت در یک حلقه تکرار."""
    print("اسکریپت آربیتراژ اجرا شد. (برای توقف Ctrl+C را بزنید)")
    print(f"هر 30 ثانیه API در آدرس {API_URL} چک می‌شود...")
    print("-" * 30)
    
    while True:
        try:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{current_time}] در حال دریافت داده‌ها...")
            
            data = fetch_arbitrage_data()
            
            if data:
                message = format_message(data)
                
                if message:
                    print(f"[{current_time}] فرصت یافت شد! در حال ارسال به تلگرام...")
                    send_to_telegram(message)
                else:
                    print(f"[{current_time}] فرصتی یافت نشد. در حال انتظار...")
            else:
                print(f"[{current_time}] دریافت داده‌ها از API ناموفق بود. در حال انتظار...")

            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\nدریافت سیگنال توقف (Ctrl+C). اسکریپت متوقف شد.")
            sys.exit(0)
        except Exception as e:
            print(f"!!! خطای پیش‌بینی نشده در حلقه اصلی: {e} !!!")
            print("30 ثانیه صبر می‌کند و دوباره تلاش می‌کند...")
            time.sleep(30)

if __name__ == "__main__":
    main()
