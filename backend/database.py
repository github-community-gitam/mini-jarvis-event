import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL

def get_db_connection():
    """
    Returns a new PostgreSQL database connection.
    """
    if not DATABASE_URL:
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=5)
        conn.autocommit = True
        return conn
    except Exception as e:
        print("[Database Connection Error]: connection unavailable")
        return None
