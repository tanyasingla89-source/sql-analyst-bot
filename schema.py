import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_schema_text():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)
    rows = cur.fetchall()
    conn.close()

    tables = {}
    for table, col, dtype in rows:
        tables.setdefault(table, []).append(f"{col} ({dtype})")

    schema_text = ""
    for table, cols in tables.items():
        schema_text += f"Table {table}: {', '.join(cols)}\n"
    return schema_text

if __name__ == "__main__":
    print(get_schema_text())
