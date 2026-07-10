import os
import psycopg2
from dotenv import load_dotenv
 
load_dotenv()
 
DATABASE_URL = os.getenv("DATABASE_URL")
 
TABLES_OF_INTEREST = ["patients", "appointments", "lab_results", "billing", "admissions"]
 
 
def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
 
    for table in TABLES_OF_INTEREST:
        print(f"\n=== {table} ===")
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table,))
        columns = cur.fetchall()
        if not columns:
            print("  (table not found)")
            continue
        for col_name, col_type in columns:
            print(f"  {col_name}: {col_type}")
 
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        count = cur.fetchone()[0]
        print(f"  Row count: {count}")
 
    cur.close()
    conn.close()
 
 
if __name__ == "__main__":
    main()
 