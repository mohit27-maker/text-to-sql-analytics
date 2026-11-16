import streamlit as st
from llm import generate_sql
from guard import check_sql
from db import run_query
from charts import make_chart

st.set_page_config(page_title="NL-to-SQL Agent", layout="wide")
st.title("Ask your data")
st.caption("Type a business question. The agent writes the SQL, runs it read-only, and charts the result.")

q = st.text_input("Your question", placeholder="Which plan has the highest churn rate?")

if st.button("Run") and q:
    sql = generate_sql(q)
    ok, result = check_sql(sql)
    if not ok:
        st.code(sql, language="sql")
        st.error(result)
        st.stop()

    df, error = None, None
    for attempt in range(2):                      # 1 retry on SQL error
        try:
            df = run_query(result)
            break
        except Exception as e:
            error = str(e).split("\n")[0]
            sql = generate_sql(q, error=error, bad_sql=result)
            ok, result = check_sql(sql)
            if not ok:
                st.error(result)
                st.stop()

    st.subheader("Generated SQL")
    st.code(result, language="sql")

    if df is None:
        st.error(f"Query failed: {error}")
    else:
        st.subheader("Result")
        st.dataframe(df, use_container_width=True)
        fig = make_chart(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)