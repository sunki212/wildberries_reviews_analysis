import psycopg2
from config.config import DB_CONFIG

def get_db_connection():
    """Установка соединения с БД"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        return conn
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        raise

