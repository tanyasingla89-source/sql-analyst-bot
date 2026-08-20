import sqlglot
from sqlglot import exp

FORBIDDEN = {"insert", "update", "delete", "drop", "alter", "truncate", "grant", "create"}

def validate_sql(sql: str):
    if sql.strip().startswith("-- CANNOT_ANSWER"):
        return False, sql

    lowered = sql.lower()
    for word in FORBIDDEN:
        if word in lowered:
            return False, f"Blocked: contains forbidden keyword '{word}'"

    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except Exception as e:
        return False, f"SQL parse error: {e}"

    if not isinstance(parsed, exp.Select):
        return False, "Only SELECT statements are allowed"

    if not parsed.args.get("limit"):
        sql = sql.rstrip(";") + " LIMIT 100;"

    return True, sql
