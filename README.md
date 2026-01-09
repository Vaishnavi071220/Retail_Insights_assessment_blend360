# Retail_Insights_assessment_blend360

# Retail Insights Assistant (Multi-Agent RAG)

## 🛠️ Setup & Execution
1. Install dependencies: `pip install -r requirements.txt`
2. Add your Groq API Key to a `.env` file: `GROQ_API_KEY=your_key_here`
3. Run the application: `streamlit run app.py`

## 🤖 Multi-Agent Design
- **Query Resolution Agent:** Analyzes the DuckDB schema and conversation history to generate precise SQL.
- **Data Extraction Agent:** Executes the SQL and manages the data connection.
- **Validation Agent:** Acts as a quality gate, ensuring data exists before interpretation.
- **Self-Correction Loop:** If the SQL fails, the agents automatically attempt a refinement step.

## 📝 Key Assumptions
- The uploaded dataset follows a standard retail format (headers like Order ID, Date, Amount).
- A standardized schema is created in DuckDB for consistent querying.

## 🚀 Scalability (100GB+ Strategy)
[cite_start]To scale this system for 100GB+ datasets as per requirements [cite: 33-35]:
1. [cite_start]**Cloud Migration:** Replace local DuckDB with **Google BigQuery** or **Snowflake**[cite: 41].
2. **Metadata Layer:** Instead of full schema injection, use a vector-indexed metadata store to find relevant tables/columns.
3. [cite_start]**Partitioning:** Utilize partitioned **Parquet** files in cloud storage (S3/GCS) to minimize data scanning[cite: 43].
