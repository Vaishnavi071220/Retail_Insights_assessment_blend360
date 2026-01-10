import pandas as pd
import duckdb

# Normalize column names
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace(":", "_")
    )
    return df

# Deduplicate columns
def deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen = {}
    new_cols = []

    for col in df.columns:
        if col not in seen:
            seen[col] = 0
            new_cols.append(col)
        else:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")

    df.columns = new_cols
    return df

# Detect dataset type
def detect_dataset_type(df: pd.DataFrame) -> str:
    cols = set(df.columns)

    sales_signals = {
        "order_id", "order_date", "date",
        "category", "style", "sku",
        "qty", "pcs",
        "amount", "revenue", "gross_amt",
        "state", "ship_state"
    }

    if len(cols.intersection(sales_signals)) >= 2:
        return "sales"

    return "generic"

# Convert numeric columns safely
def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    numeric_candidates = [
        # sales numeric columns
        "qty", "revenue", "amount", "gross_amt",

        # expense numeric columns (amount-like)
        "received_amount", "recived_amount", "expense_amount",

        # pricing and margin datasets
        "tp", "tp_1", "tp_2",
        "mrp_old",
        "final_mrp", "final_mrp_old",

        # marketplace MRPs
        "ajio_mrp",
        "amazon_mrp", "amazon_fba_mrp",
        "flipkart_mrp",
        "limeroad_mrp",
        "myntra_mrp",
        "paytm_mrp",
        "snapdeal_mrp"
    ]

    for col in numeric_candidates:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("₹", "", regex=False)
                .str.replace("/-", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

# Main loader
def load_sales_data(uploaded_file, return_df=False):
    filename = uploaded_file.name.lower()

    # ---- Load file
    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Upload CSV or Excel.")

    # Normalize headers
    df = normalize_columns(df)

    # Detect dataset type BEFORE renaming
    dataset_type = detect_dataset_type(df)

    # Normalize sales datasets
    if dataset_type == "sales":
        column_map = {
            "order_id": "order_id",
            "orderid": "order_id",

            "date": "order_date",
            "order_date": "order_date",

            "category": "category",
            "style": "category",
            "product": "category",

            "qty": "qty",
            "quantity": "qty",
            "pcs": "qty",

            "amount": "revenue",
            "revenue": "revenue",
            "gross_amt": "revenue",

            "state": "state",
            "ship_state": "state",
            "city": "city",
            "ship_city": "city",
            "country": "country",
            "ship_country": "country",

            "status": "status"
        }

        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

    # ---- Expense dataset special handling
    # Expense IIGF looks like:
    # index, recived_amount, unnamed_1, expance, unnamed_3
    # where expance = expense name (text)
    # and unnamed_3 = numeric amount
    if "expance" in df.columns and "unnamed_3" in df.columns and "expense_amount" not in df.columns:
        df = df.rename(columns={"unnamed_3": "expense_amount"})

    # ---- Drop unnamed junk columns (AFTER expense mapping)
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

    # ---- Deduplicate columns
    df = deduplicate_columns(df)

    # ---- Convert numeric columns
    df = convert_numeric_columns(df)

    # ---- Date conversion
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # ---- Load into DuckDB
    con = duckdb.connect(database=":memory:")
    con.execute("CREATE TABLE sales AS SELECT * FROM df")

    if return_df:
        return con, df, dataset_type

    return con
