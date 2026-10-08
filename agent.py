import os
import json
import time
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from google import genai
from google.genai import types

from schema import get_schema_text
from validator import validate_sql
from db import run_query

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.5-flash-lite"
MAX_STEPS = 6            # agent can call tools at most this many rounds
MAX_ROWS_TO_MODEL = 50   # only send this many rows back to the model

SYSTEM_PROMPT = """You are a data analyst assistant for a PostgreSQL database.

Rules:
1. If you have not seen the schema yet, call get_schema first.
2. To get data, call execute_sql with ONE read-only PostgreSQL SELECT query. Use only tables/columns from the schema and use table aliases.
3. For calculations on the last query result (describe, group-by, top-N, month-over-month change) call analyze_data. Do not do math in your head.
4. When a chart would help, call create_visualization using column names from the last query result.
5. If a tool returns an error, read the error, fix your call, and try again.
6. If the question cannot be answered from the schema, say so and do not call execute_sql.
7. Aggregate in SQL (SUM, COUNT, GROUP BY) so the result is a small table. Aim for 3 tool calls or fewer. For "why" questions, query the trend by period, report what the numbers show, then say the data cannot explain the cause.
8. Your final answer must be short and plain. Only state what the returned data shows. Never invent numbers. If the data does not explain WHY something happened, say that clearly.
"""


# ---------------- TOOLS ----------------
# every tool takes (state, **args). state holds the last query result and chart.

def get_schema(state):
    """Return table and column info from PostgreSQL."""
    return {"schema": get_schema_text()}


def execute_sql(state, query):
    """Run a read-only SELECT. Goes through the sqlglot validator first."""
    ok, result = validate_sql(query)          # blocks writes, adds LIMIT 100
    if not ok:
        return {"error": f"Query rejected: {result}"}
    columns, rows = run_query(result)         # read-only DB account + 5s timeout
    df = pd.DataFrame(rows, columns=columns)
    for c in df.columns:                      # Postgres SUM/AVG come back as Decimal -> make them numbers
        try:
            df[c] = pd.to_numeric(df[c])
        except (ValueError, TypeError):
            pass
    state["df"] = df
    state["sql"] = result
    return {
        "columns": columns,
        "row_count": len(df),
        "truncated": len(df) > MAX_ROWS_TO_MODEL,
        "rows": json.loads(df.head(MAX_ROWS_TO_MODEL).to_json(orient="records", date_format="iso", default_handler=str)),
    }


def analyze_data(state, operation, column=None, group_by=None, agg="sum", n=5):
    """Simple pandas analysis on the last query result."""
    df = state.get("df")
    if df is None:
        return {"error": "No data yet. Call execute_sql first."}

    for c in (column, group_by):
        if c is not None and c not in df.columns:
            return {"error": f"Column '{c}' not found. Available: {list(df.columns)}"}

    if operation == "describe":
        out = df.describe(include="all")
    elif operation == "group_aggregate":
        if column is None or group_by is None:
            return {"error": "group_aggregate needs 'column' and 'group_by'."}
        if agg not in ("sum", "mean", "count", "min", "max"):
            return {"error": "agg must be one of sum, mean, count, min, max."}
        out = df.groupby(group_by)[column].agg(agg).reset_index()
    elif operation == "top_n":
        if column is None:
            return {"error": "top_n needs 'column'."}
        out = df.nlargest(int(n), column)
    elif operation == "pct_change":
        if column is None:
            return {"error": "pct_change needs 'column'."}
        out = df.copy()
        out["pct_change"] = (out[column].pct_change() * 100).round(2)
    else:
        return {"error": "operation must be describe, group_aggregate, top_n or pct_change."}

    return {"result": json.loads(out.to_json(orient="records", date_format="iso", default_handler=str))}


def create_visualization(state, chart_type, x, y, title=""):
    """Build a Plotly chart from the last query result."""
    df = state.get("df")
    if df is None:
        return {"error": "No data yet. Call execute_sql first."}
    for c in (x, y):
        if c not in df.columns:
            return {"error": f"Column '{c}' not found. Available: {list(df.columns)}"}

    if chart_type == "bar":
        fig = px.bar(df, x=x, y=y, title=title)
    elif chart_type == "line":
        fig = px.line(df, x=x, y=y, title=title)
    elif chart_type == "pie":
        fig = px.pie(df, names=x, values=y, title=title)
    elif chart_type == "scatter":
        fig = px.scatter(df, x=x, y=y, title=title)
    else:
        return {"error": "chart_type must be bar, line, pie or scatter."}

    state["fig"] = fig
    return {"status": f"{chart_type} chart created"}


TOOL_FUNCS = {
    "get_schema": get_schema,
    "execute_sql": execute_sql,
    "analyze_data": analyze_data,
    "create_visualization": create_visualization,
}

# the description of each tool that Gemini sees
TOOLS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="get_schema",
        description="Get all table names, column names and data types from the PostgreSQL database. Call this before writing SQL.",
        parameters={"type": "OBJECT", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="execute_sql",
        description="Run ONE read-only PostgreSQL SELECT query and return the rows. Writes are rejected. Results are capped at 100 rows.",
        parameters={
            "type": "OBJECT",
            "properties": {"query": {"type": "STRING", "description": "A single PostgreSQL SELECT statement."}},
            "required": ["query"],
        },
    ),
    types.FunctionDeclaration(
        name="analyze_data",
        description="Run a simple pandas analysis on the result of the last execute_sql call.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "operation": {"type": "STRING", "enum": ["describe", "group_aggregate", "top_n", "pct_change"]},
                "column": {"type": "STRING", "description": "Numeric column to analyze."},
                "group_by": {"type": "STRING", "description": "Column to group by (group_aggregate only)."},
                "agg": {"type": "STRING", "enum": ["sum", "mean", "count", "min", "max"]},
                "n": {"type": "INTEGER", "description": "How many rows for top_n."},
            },
            "required": ["operation"],
        },
    ),
    types.FunctionDeclaration(
        name="create_visualization",
        description="Create a Plotly chart from the result of the last execute_sql call.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "chart_type": {"type": "STRING", "enum": ["bar", "line", "pie", "scatter"]},
                "x": {"type": "STRING", "description": "Column for the x axis (or labels for pie)."},
                "y": {"type": "STRING", "description": "Numeric column for the y axis (or values for pie)."},
                "title": {"type": "STRING"},
            },
            "required": ["chart_type", "x", "y"],
        },
    ),
])


# ---------------- AGENT LOOP ----------------

def call_gemini(contents, config):
    # free tier allows ~5 requests/min, so on a 429 error wait and try again
    for attempt in range(3):
        try:
            return client.models.generate_content(model=MODEL, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(30)
                continue
            raise

def run_agent(question):
    state = {"df": None, "fig": None, "sql": None}
    steps = []
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[TOOLS],
        # we run the loop ourselves, so turn off the SDK's automatic one
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    for _ in range(MAX_STEPS):
        response = call_gemini(contents, config)
        if not response.candidates or not response.candidates[0].content:
            answer = "The model returned no response. Please try rephrasing the question."
            break

        content = response.candidates[0].content
        calls = [p.function_call for p in (content.parts or []) if p.function_call]

        if not calls:                              # no tool requested -> final answer
            answer = response.text or "No answer returned."
            break

        contents.append(content)                   # keep the model's tool request in history
        result_parts = []
        for call in calls:
            args = dict(call.args or {})
            try:
                result = TOOL_FUNCS[call.name](state, **args)
            except Exception as e:                 # send the error back so the model can retry
                result = {"error": f"{type(e).__name__}: {e}"}
            steps.append({"tool": call.name, "args": args, "result": str(result)[:300]})
            result_parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=result_parts))
    else:
        # out of steps: ask once more with tools switched off so we still get a text answer
        contents.append(types.Content(role="user", parts=[types.Part(text="Stop calling tools. Answer now using only the data you already have.")]))
        final_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[TOOLS],
            tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode="NONE")),
        )
        try:
            answer = call_gemini(contents, final_config).text or f"Stopped after {MAX_STEPS} steps without a final answer."
        except Exception:
            answer = f"Stopped after {MAX_STEPS} steps without a final answer. Try a simpler question."

    return {"answer": answer, "steps": steps, "df": state["df"], "fig": state["fig"], "sql": state["sql"]}
