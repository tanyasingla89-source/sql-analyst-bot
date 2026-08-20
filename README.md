# 📊 NL-to-SQL Analyst Bot

A natural-language-to-SQL analytics assistant — ask business questions in plain English, get validated SQL, live query results, and auto-generated charts.

**🔗 Live demo:** [sql-analyst-bot-c6htlaudwozdgnbccyzyv5.streamlit.app](https://sql-analyst-bot-c6htlaudwozdgnbccyzyv5.streamlit.app)

## What it does

Ask a question like *"What are the top 5 products by revenue?"* and the app:
1. Sends your question + the database schema to Gemini, which generates a SQL query
2. Validates the query (blocks any write operations, enforces read-only access, auto-limits result size)
3. Executes it against a live PostgreSQL database
4. Displays the results as a table and an auto-generated chart

## Try asking

- "What are the top 5 products by total revenue?"
- "How many orders did each customer place?"
- "Which category has the most products?"
- "List customers who have never placed an order"

## Tech stack

- **LLM:** Google Gemini API
- **Database:** PostgreSQL (hosted on Neon), Northwind sample dataset
- **SQL validation:** sqlglot
- **Backend/UI:** Streamlit
- **Visualization:** Plotly
- **Deployment:** Streamlit Community Cloud

## Safety guardrails

- Database connection uses a **read-only role** (SELECT only — no write grants at the DB level)
- Every generated query is parsed and validated before execution — write keywords (INSERT, UPDATE, DELETE, DROP, ALTER) are blocked
- Only SELECT statements are allowed to execute
- Row limits are auto-enforced (default cap of 100 rows)
- Query execution timeout (5s) prevents long-running queries

## Running locally

\`\`\`bash
git clone https://github.com/tanyasingla89-source/sql-analyst-bot.git
cd sql-analyst-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

Create a \`.env\` file with:
\`\`\`
DATABASE_URL=your_postgresql_connection_string
GEMINI_API_KEY=your_gemini_api_key
\`\`\`

Run the app:
\`\`\`bash
streamlit run app.py
\`\`\`

## Files

| File | Purpose |
|---|---|
| \`app.py\` | Streamlit UI — ties the full pipeline together |
| \`schema.py\` | Fetches the database schema dynamically for the LLM prompt |
| \`llm.py\` | Prompt design + SQL generation via Gemini API |
| \`validator.py\` | SQL safety validation using sqlglot |
| \`db.py\` | Executes validated queries against PostgreSQL |
| \`charts.py\` | Auto-chart generation logic based on result shape |
