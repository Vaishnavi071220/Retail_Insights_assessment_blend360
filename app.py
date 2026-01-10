import streamlit as st
from data_loader import load_sales_data
from agents import QueryResolutionAgent, DataExtractionAgent, ValidationAgent
from llm_client import call_llm
from prompts import SUMMARY_PROMPT

st.set_page_config(page_title="Retail Insights Assistant", layout="wide")

st.title("Retail Insights Assistant")
st.caption(
    "Upload retail or business datasets to generate executive summaries "
    "and ask questions in natural language."
)

# Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "con" not in st.session_state:
    st.session_state.con = None

if "df" not in st.session_state:
    st.session_state.df = None

if "dataset_type" not in st.session_state:
    st.session_state.dataset_type = None

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False


# File Upload
uploaded_file = st.file_uploader(
    "Upload Dataset (CSV or Excel)",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file:
    try:
        con, df, dataset_type = load_sales_data(uploaded_file, return_df=True)

        st.session_state.con = con
        st.session_state.df = df
        st.session_state.dataset_type = dataset_type
        st.session_state.data_loaded = True

        st.success("Data loaded successfully.")

        with st.expander("Preview dataset"):
            st.write(df.head(20))
            st.write("Columns detected:")
            st.write(list(df.columns))

        if dataset_type != "sales":
            st.info(
                "This dataset does not appear to be a transaction-level sales dataset. "
                "Summaries may be limited, but conversational queries will still work."
            )

    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

if not st.session_state.data_loaded:
    st.info("Upload a dataset to begin.")
    st.stop()



mode = st.radio(
    "Choose Mode",
    ["Summarization", "Conversational Q&A"],
    horizontal=True
)



# Summarization Mode
if mode == "Summarization":

    st.subheader("Executive Summary Generator")

    if st.button("Generate Summary", type="primary"):

        con = st.session_state.con
        df = st.session_state.df
        cols = set(df.columns)

        summary_blocks = []

        # Category summary (if available)
        if "category" in cols and "revenue" in cols:
            top_categories = con.execute("""
                SELECT category, SUM(revenue) AS total_revenue
                FROM sales
                WHERE revenue IS NOT NULL
                GROUP BY category
                ORDER BY total_revenue DESC
                LIMIT 10
            """).fetchdf()

            st.write("Top Categories")
            st.dataframe(top_categories)

            summary_blocks.append(
                "Top Categories:\n" +
                top_categories.to_string(index=False)
            )

        # State summary (if available)
        if "state" in cols and "revenue" in cols:
            top_states = con.execute("""
                SELECT state, SUM(revenue) AS total_revenue
                FROM sales
                WHERE revenue IS NOT NULL AND state IS NOT NULL
                GROUP BY state
                ORDER BY total_revenue DESC
                LIMIT 10
            """).fetchdf()

            st.write("Top States")
            st.dataframe(top_states)

            summary_blocks.append(
                "Top States:\n" +
                top_states.to_string(index=False)
            )
        # Status summary (if available)
        if "status" in cols:
            status_split = con.execute("""
                SELECT status, COUNT(*) AS orders,
                       SUM(revenue) AS total_revenue
                FROM sales
                GROUP BY status
                ORDER BY orders DESC
            """).fetchdf()

            st.write("Order Status Split")
            st.dataframe(status_split)

            summary_blocks.append(
                "Order Status Split:\n" +
                status_split.to_string(index=False)
            )

        if not summary_blocks:
            st.warning(
                "The dataset does not contain sufficient fields for a sales summary."
            )
            st.stop()

        combined_summary = "\n\n".join(summary_blocks)

        llm_input = SUMMARY_PROMPT + "\n\n" + combined_summary
        summary = call_llm(llm_input)

        st.subheader("Business Summary (LLM Generated)")
        st.success(summary)

# Conversational Q&A Mode
else:
    st.subheader("Ask Questions About Your Data")

    con = st.session_state.con

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_question = st.chat_input(
        "Ask a question, for example: "
        "'Which category generates the highest revenue?'"
    )

    if user_question:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_question}
        )

        with st.chat_message("user"):
            st.markdown(user_question)

        qr_agent = QueryResolutionAgent()
        data_agent = DataExtractionAgent()
        val_agent = ValidationAgent()

        schema_df = con.execute(
            "PRAGMA table_info('sales')"
        ).fetchdf()
        schema_info = schema_df[["name", "type"]].to_string(index=False)

        memory_context = "\n".join(
            [m["content"] for m in st.session_state.chat_history[-5:]]
        )

        with st.chat_message("assistant"):
            st.markdown("Thinking...")

            try:
                sql = qr_agent.resolve(
                    user_question,
                    schema_info,
                    memory_context
                )

                if any(
                    kw in sql.lower()
                    for kw in ["drop", "delete", "update", "insert", "alter"]
                ):
                    msg = "Unsafe SQL detected. Query blocked."
                    st.error(msg)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": msg}
                    )
                    st.stop()

                try:
                    df_result = data_agent.extract(sql, con)
                except Exception as e:
                    st.warning(
                        "Initial SQL failed. Attempting self-correction."
                    )
                    sql = qr_agent.refine(
                        user_question,
                        schema_info,
                        str(e),
                        failed_sql=sql
                    )
                    df_result = data_agent.extract(sql, con)

                st.markdown("Generated SQL")
                st.code(sql, language="sql")

                validated = val_agent.validate(df_result)

                if isinstance(validated, str):
                    st.warning(validated)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": validated}
                    )
                else:
                    st.dataframe(validated)

                    interpretation_prompt = f"""
Convert the following table into a concise business answer.

Question:
{user_question}

Result:
{validated.head(20).to_string(index=False)}
"""
                    explanation = call_llm(interpretation_prompt)

                    st.subheader("Insight")
                    st.success(explanation)

                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": explanation}
                    )

            except Exception as e:
                msg = f"Error occurred while answering: {e}"
                st.error(msg)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": msg}
                )
