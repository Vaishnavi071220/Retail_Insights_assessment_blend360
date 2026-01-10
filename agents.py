from llm_client import call_llm
from prompts import SQL_PROMPT
import re
import pandas as pd


def clean_sql(sql: str) -> str:
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```", "", sql).strip()
    sql = sql.strip("`").strip()

    # Keep only first SQL statement
    if ";" in sql:
        sql = sql.split(";")[0].strip() + ";"

    return sql


class QueryResolutionAgent:
    def resolve(self, user_query, schema_info, memory_context=""):
        prompt = SQL_PROMPT.format(
            schema_info=schema_info,
            memory_context=memory_context,
            user_question=user_query
        )
        raw_sql = call_llm(prompt)
        return clean_sql(raw_sql)

    def refine(self, original_query, schema_info, error_msg, failed_sql):
        prompt = f"""
You are fixing a DuckDB SQL query.

Table name: sales

FAILED SQL:
{failed_sql}

ERROR MESSAGE:
{error_msg}

User question:
{original_query}

Use ONLY the following schema:
{schema_info}

Return ONLY the corrected SQL query.
"""
        raw_sql = call_llm(prompt)
        return clean_sql(raw_sql)


class DataExtractionAgent:
    def extract(self, sql, con):
        return con.execute(sql).fetchdf()


class ValidationAgent:
    def validate(self, df):
        if df is None:
            return "Validation Error: No data returned"

        if not isinstance(df, pd.DataFrame):
            return f"Validation Error: Expected DataFrame, got {type(df)}"

        if df.empty:
            return "Validation Warning: Query returned no rows"

        if df.isnull().all().all():
            return "Validation Warning: All values in result are null"

        if len(df) > 10000:
            return df.head(1000)

        return df
