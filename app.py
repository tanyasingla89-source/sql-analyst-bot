import streamlit as st
from agent import run_agent

st.set_page_config(page_title="NL-to-SQL Analyst Bot", layout="wide")
st.title("📊 NL-to-SQL Analyst Bot")
st.caption("Ask a business question in plain English — the agent picks tools, runs SQL, and explains the result.")

question = st.text_input("Ask a question about the data:",
                          placeholder="e.g. What are the top 5 products by revenue?")

if st.button("Run") and question:
    with st.spinner("Agent is working..."):
        try:
            out = run_agent(question)
        except Exception as e:
            st.error(f"Agent failed: {e}")
            st.stop()

    with st.expander(f"Agent steps ({len(out['steps'])})"):
        for i, s in enumerate(out["steps"], 1):
            st.markdown(f"**{i}. `{s['tool']}`**")
            st.json(s["args"])
            st.caption(s["result"])

    st.subheader("Answer")
    st.write(out["answer"])

    if out["sql"]:
        st.subheader("Generated SQL")
        st.code(out["sql"], language="sql")
    if out["df"] is not None:
        st.subheader("Results")
        st.dataframe(out["df"])
    if out["fig"] is not None:
        st.subheader("Visualization")
        st.plotly_chart(out["fig"], use_container_width=True)
