from schema import get_schema_text
from llm import generate_sql
from validator import validate_sql
from db import run_query

schema_text = get_schema_text()
question = "What are the top 5 products by total revenue?"

sql = generate_sql(question, schema_text)
print("Generated SQL:\n", sql)

is_valid, result = validate_sql(sql)
if not is_valid:
    print("Validation failed:", result)
else:
    columns, rows = run_query(result)
    print("\nColumns:", columns)
    print("Rows:")
    for row in rows:
        print(row)
