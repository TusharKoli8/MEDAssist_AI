import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
 
load_dotenv()
 
DATABASE_URL = os.getenv("DATABASE_URL")
 
 
def get_connection():
    """Create a new database connection. Caller is responsible for closing it."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
 
 
def run_query(query: str, params: tuple = None) -> list[dict]:
    """Run a read-only query and return results as a list of dicts."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        results = cur.fetchall()
        cur.close()
        return [dict(row) for row in results]
    finally:
        conn.close()
 