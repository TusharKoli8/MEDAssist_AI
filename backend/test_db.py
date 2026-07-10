import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public';
    """)
    tables = cur.fetchall()
    print("Connected successfully. Tables found:")
    for t in tables:
        print(" -", t[0])
    cur.close()
    conn.close()
except Exception as e:
    print("Connection failed:")
    print(e)
