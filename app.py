import streamlit as st
import pandas as pd
from schema import get_schema_text
from llm import generate_sql
from validator import validate_sql
from db import run_query
from charts import auto_chart

st.set_page_config(page_title="NL-to-SQL Analyst Bot", layout="wide")
st.title("📊 NL-to-SQL Analyst Bot")
st.caption("Ask a business question in plain English — get SQL, data, and a chart.")

schema_text = get_schema_text()

question = st.text_input("Ask a question about the data:",
                          placeholder="e.g. What are the top 5 products by revenue?")

if st.button("Run") and question:
    with st.spinner("Generating SQL..."):
        sql = generate_sql(question, schema_text)

    is_valid, result = validate_sql(sql)

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    if not is_valid:
        st.error(result)
    else:
        try:
            columns, rows = run_query(result)
            df = pd.DataFrame(rows, columns=columns)
            st.subheader("Results")
            st.dataframe(df)

            chart = auto_chart(df)
            if chart:
                st.subheader("Visualization")
                st.plotly_chart(chart, use_container_width=True)
        except Exception as e:
            st.error(f"Query execution failed: {e}")
