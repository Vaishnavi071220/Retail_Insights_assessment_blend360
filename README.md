Retail Insights Assistant (GenAI + Multi-Agent System)

Overview
--------
The Retail Insights Assistant is a GenAI-powered analytics application designed to help business users analyze retail sales data through executive summaries and natural language questions.

The system combines a structured analytical data layer with a Groq-hosted LLM and a multi-agent architecture to deliver accurate, scalable, and decision-ready insights. This project was built as part of the Blend360 GenAI interview assessment.

Core Capabilities
-----------------
1. Summarization Mode
- Generates concise executive-level summaries from retail sales data
- Highlights top-performing categories, geographic performance, order status distribution, and key business insights
- Provides actionable recommendations based on observed trends

2. Conversational Q&A Mode
- Allows users to ask ad-hoc business questions in natural language
- Automatically translates questions into SQL queries
- Returns data-backed answers along with business-friendly explanations
- Maintains short-term conversational context for follow-up questions

Setup & Execution
-----------------
1. Install dependencies:
```bash
   pip install -r requirements.txt
```

3. Configure environment variables:
   Create a .env file in the project root and add:
   GROQ_API_KEY=your_key_here

4. Run the application:
  ```bash
 streamlit run app.py
```

5. Upload a CSV or Excel retail sales dataset (e.g., Amazon Sale Report)

Multi-Agent Architecture
------------------------
The system uses a three-agent architecture aligned with the assignment requirements.

Query Resolution Agent:
- Interprets user intent using a large language model
- Dynamically injects the DuckDB schema into prompts to prevent hallucinated columns
- Generates safe, schema-aware SQL queries

Data Extraction Agent:
- Executes SQL queries against DuckDB
- Ensures all heavy computation happens in the database layer

Validation Agent:
- Acts as a quality gate by validating query results
- Handles empty or insufficient data scenarios gracefully
- Prevents unsafe SQL operations

Self-Correction Loop:
- If SQL execution fails, the error is passed back to the LLM
- The agent refines and retries the query automatically
- Demonstrates true agentic interaction and system resilience

Scalability Strategy (100GB+ Design)
-----------------------------------
Although the prototype runs locally, it is designed to scale to large datasets.

Data Engineering & Storage:
- Raw data stored in a cloud data lake (S3, GCS, or Azure Data Lake)
- Curated data written as partitioned Parquet or Delta tables
- Batch ingestion handled via Spark, Databricks, or dbt

Query & Retrieval Efficiency:
- SQL pushdown to cloud data warehouses such as BigQuery or Snowflake
- Partitioning by date, geography, and category
- Use of pre-aggregated summary tables for frequent analytical queries

LLM Orchestration:
- LLM used only for intent understanding, SQL generation, and narrative summaries
- Prompt templates and caching applied to control latency and cost

Key Assumptions
---------------
- The dataset contains structured retail sales data with date, category, geography, and revenue fields
- Regional groupings (North, South, East, West) are not explicitly defined unless provided
- Year-over-year analysis depends on availability of multi-year data
- All insights are strictly grounded in retrieved data to avoid hallucination

Limitations & Future Enhancements
---------------------------------
- Add vector search for unstructured business documents
- Introduce configurable region mappings
- Persist long-term conversation memory
- Add monitoring for accuracy, latency, and cost
- Support real-time or streaming data ingestion

Why This Design Works
---------------------
- Clean separation between data processing and LLM reasoning
- Schema grounding and validation prevent hallucinations
- SQL-based retrieval scales efficiently to large datasets
- Produces executive-ready insights rather than raw metrics
