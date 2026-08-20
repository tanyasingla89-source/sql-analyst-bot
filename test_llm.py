from schema import get_schema_text
from llm import generate_sql

schema_text = get_schema_text()

questions = [
    "How many orders did each customer place?",
    "Which category has the most products?",
    "List customers who have never placed an order",
    "What's our best strategy for next quarter?",
]

for q in questions:
    print(f"\nQ: {q}")
    print(generate_sql(q, schema_text))
    print("-" * 50)
