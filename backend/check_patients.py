import os
import psycopg2
from dotenv import load_dotenv
 
load_dotenv()
 
DATABASE_URL = os.getenv("DATABASE_URL")
 
 
def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
 
    cur.execute("SELECT DISTINCT patient_id FROM lab_results LIMIT 5;")
    print("Sample patient_ids from lab_results:", cur.fetchall())
 
    cur.execute("SELECT DISTINCT patient_id FROM billing LIMIT 5;")
    print("Sample patient_ids from billing:", cur.fetchall())
 
    cur.execute("SELECT COUNT(*) FROM patients;")
    print("Patients table row count:", cur.fetchone()[0])
 
    cur.close()
    conn.close()
 
 
if __name__ == "__main__":
    main()
 
 