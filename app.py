import streamlit as st
from data_loader import load_sales_data
from agents import QueryResolutionAgent, DataExtractionAgent, ValidationAgent
from llm_client import call_llm
from prompts import SUMMARY_PROMPT

st.set_page_config(page_title="Retail Insights Assistant", layout="wide")

st.title(" Retail Insights Assistant (Groq + Multi-Agent)")
st.caption("Upload retail sales data → get executive summaries + ask business questions in natural language.")

# -----------------------------
# Session state
# -----------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "con" not in st.session_state:
    st.session_state.con = None

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False


# -----------------------------
# File Upload
# -----------------------------
uploaded_file = st.file_uploader(" Upload Sales Dataset (CSV or Excel)", type=["csv", "xlsx", "xls"])

if uploaded_file:
    try:
        con, df = load_sales_data(uploaded_file, return_df=True)
        st.session_state.con = con
        st.session_state.data_loaded = True

        st.success(" Data loaded successfully!")

        with st.expander(" Preview dataset"):
            st.write(df.head(20))
            st.write("Columns detected:", list(df.columns))

    except Exception as e:
        st.error(f" Error loading file: {e}")
        st.stop()

if not st.session_state.data_loaded:
    st.info("Upload a dataset to begin.")
    st.stop()

# -----------------------------
# Mode Selection
# -----------------------------
mode = st.radio("Choose Mode", [" Summarization", " Conversational Q&A"], horizontal=True)


# ==========================================================
#  Summarization Mode
# ==========================================================
if mode == " Summarization":

    st.subheader(" Executive Summary Generator")

    if st.button("Generate Summary", type="primary"):
        con = st.session_state.con

        top_categories = con.execute("""
            SELECT category, SUM(revenue) AS total_revenue
            FROM sales
            WHERE revenue IS NOT NULL
            GROUP BY category
            ORDER BY total_revenue DESC
            LIMIT 10
        """).fetchdf()

        top_states = con.execute("""
            SELECT state, SUM(revenue) AS total_revenue
            FROM sales
            WHERE revenue IS NOT NULL AND state IS NOT NULL
            GROUP BY state
            ORDER BY total_revenue DESC
            LIMIT 10
        """).fetchdf()

        status_split = con.execute("""
            SELECT status, COUNT(*) AS orders, SUM(revenue) AS total_revenue
            FROM sales
            GROUP BY status
            ORDER BY orders DESC
        """).fetchdf()

        st.write("###  Top Categories")
        st.dataframe(top_categories)

        st.write("###  Top States")
        st.dataframe(top_states)

        st.write("###  Status Split")
        st.dataframe(status_split)

        combined = f"""
Top Categories:\n{top_categories.to_string(index=False)}\n
Top States:\n{top_states.to_string(index=False)}\n
Order Status Split:\n{status_split.to_string(index=False)}
"""
        summary = call_llm(SUMMARY_PROMPT + "\n\n" + combined)

        st.write("##  Business Summary (LLM Generated)")
        st.success(summary)


# ==========================================================
#  Conversational Q&A Mode
# ==========================================================
else:
    st.subheader(" Ask Questions About Your Sales Data")

    con = st.session_state.con

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_question = st.chat_input("Ask e.g. 'Which category has highest revenue in Maharashtra?'")

    if user_question:
        # Store user question
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        qr_agent = QueryResolutionAgent()
        data_agent = DataExtractionAgent()
        val_agent = ValidationAgent()

        #  Dynamic schema extraction
        schema_df = con.execute("PRAGMA table_info('sales')").fetchdf()
        schema_info = schema_df[["name", "type"]].to_string(index=False)

        #  Memory context (last 5 user+assistant messages)
        memory_context = "\n".join([m["content"] for m in st.session_state.chat_history[-5:]])

        with st.chat_message("assistant"):
            st.markdown(" Thinking...")

            try:
                # 1) First attempt SQL
                sql = qr_agent.resolve(user_question, schema_info, memory_context)

                # safety guard
                unsafe = any(x in sql.lower() for x in ["drop", "delete", "update", "insert", "alter"])
                if unsafe:
                    msg = " Unsafe SQL detected. Query blocked."
                    st.error(msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": msg})
                    st.stop()

                try:
                    df_result = data_agent.extract(sql, con)

                except Exception as e:
                    # 2) Self-correction retry
                    st.warning("Initial SQL failed. Attempting self-correction...")
                    sql = qr_agent.refine(user_question, schema_info, str(e), failed_sql=sql)
                    df_result = data_agent.extract(sql, con)

                st.markdown("###  Generated SQL")
                st.code(sql, language="sql")

                validated = val_agent.validate(df_result)

                st.markdown("###  Result")
                if isinstance(validated, str):
                    st.warning(validated)
                    st.session_state.chat_history.append({"role": "assistant", "content": validated})
                else:
                    st.dataframe(validated)

                    # LLM explanation (business-friendly)
                    interpretation_prompt = f"""
Convert the following table into a short business-friendly answer:

Question: {user_question}
Result table:
{validated.head(20).to_string(index=False)}
"""
                    explanation = call_llm(interpretation_prompt)

                    st.markdown("###  Insight")
                    st.success(explanation)

                    st.session_state.chat_history.append({"role": "assistant", "content": explanation})

            except Exception as e:
                msg = f" Error occurred while answering: {e}"
                st.error(msg)
                st.session_state.chat_history.append({"role": "assistant", "content": msg})
