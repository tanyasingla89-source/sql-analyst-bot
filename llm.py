import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

SYSTEM_PROMPT = """You are a SQL generator. Given a database schema and a natural
language question, output ONLY a valid, read-only PostgreSQL SELECT query.

Rules:
- Only use tables/columns listed in the schema below.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, or any write operation.
- Always use explicit table aliases.
- If the question is ambiguous or cannot be answered from this schema,
  output exactly: -- CANNOT_ANSWER: <short reason>
- Output ONLY the SQL query. No explanation, no markdown fences, no commentary.

Schema:
{schema}

Question: {question}
"""

def generate_sql(question: str, schema_text: str) -> str:
    prompt = SYSTEM_PROMPT.format(schema=schema_text, question=question)
    response = model.generate_content(prompt)
    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

if __name__ == "__main__":
    from schema import get_schema_text
    schema_text = get_schema_text()
    test_question = "What are the top 5 products by total revenue?"
    print(generate_sql(test_question, schema_text))
