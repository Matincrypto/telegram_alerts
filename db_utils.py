# db_utils.py
import mysql.connector
import logging
import config  # این فایل، کانفیگ همین پوشه را می‌خواند

# تنظیمات لاگ‌گیری
# ما از تنظیمات لاگ در reporter.py استفاده می‌کنیم، اما این خطوط
# برای اطمینان از تنظیم شدن لاگ در صورت اجرای مستقل بخش‌ها مفید هستند.
try:
    log_level = config.BOT["LOG_LEVEL"]
except AttributeError:
    log_level = logging.INFO

logging.basicConfig(level=log_level, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

def create_db_connection():
    """یک اتصال جدید به پایگاه داده ایجاد می‌کند."""
    try:
        connection = mysql.connector.connect(**config.DATABASE)
        return connection
    except mysql.connector.Error as e:
        logging.error(f"خطا در اتصال به پایگاه داده MySQL: {e}")
        return None

def query_db(query, params=None, fetch=None):
    """
    یک تابع عمومی برای اجرای کوئری روی پایگاه داده.
    :param query: رشته کوئری SQL
    :param params: پارامترهای جایگزین در کوئری (برای جلوگیری از SQL Injection)
    :param fetch: 'one' (برای یک ردیف)، 'all' (برای همه ردیف‌ها)، None (برای INSERT/UPDATE/DELETE)
    :return: نتیجه کوئری یا True/False
    """
    connection = create_db_connection()
    if not connection:
        return None
    
    try:
        # dictionary=True باعث می‌شود نتایج به صورت دیکشنری (dict) برگردند
        cursor = connection.cursor(dictionary=(fetch is not None))
        cursor.execute(query, params or ())
        
        if fetch == 'one':
            result = cursor.fetchone()
        elif fetch == 'all':
            result = cursor.fetchall()
        else:
            connection.commit() # اجرای دستورات INSERT, UPDATE, DELETE
            result = True
            
        return result
    except mysql.connector.Error as e:
        logging.error(f"خطای کوئری پایگاه داده: {e} | کوئری: {query} | پارامترها: {params}")
        return None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()