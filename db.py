import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def run_query(sql: str, timeout_seconds: int = 5):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {timeout_seconds * 1000};")
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return columns, rows
