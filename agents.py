from llm_client import call_llm
from prompts import SQL_PROMPT
import re

def clean_sql(sql: str) -> str:
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```", "", sql).strip()
    sql = sql.strip("`").strip()

    # Keep only first SQL statement if multiple
    if sql.count(";") > 1:
        sql = sql.split(";")[0].strip() + ";"

    return sql

class QueryResolutionAgent:
    def resolve(self, user_query, schema_info, memory_context=""):
        prompt = f"""
{SQL_PROMPT}

SCHEMA:
{schema_info}

Conversation Context (optional):
{memory_context}

USER QUESTION:
{user_query}

Return ONLY SQL.
"""
        raw_sql = call_llm(prompt)
        return clean_sql(raw_sql)

    def refine(self, original_query, schema_info, error_msg, failed_sql):
        prompt = f"""
The SQL query failed.

FAILED SQL:
{failed_sql}

ERROR:
{error_msg}

Fix the SQL for the user question:
{original_query}

Use ONLY this schema:
{schema_info}

Return ONLY corrected SQL.
"""
        raw_sql = call_llm(prompt)
        return clean_sql(raw_sql)

class DataExtractionAgent:
    def extract(self, sql, con):
        return con.execute(sql).fetchdf()

class ValidationAgent:
    def validate(self, df):
        if df is None or df.empty:
            return "Validation Error: No data found for this request."
        return df
