import pandas as pd
import duckdb

def load_sales_data(uploaded_file, return_df=False):
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Upload CSV or Excel.")

    df = df.rename(columns={
        "Order ID": "order_id",
        "Date": "order_date",
        "Category": "category",
        "SKU": "sku",
        "Size": "size",
        "Qty": "qty",
        "Amount": "revenue",
        "ship-state": "state",
        "ship-city": "city",
        "ship-country": "country",
        "Status": "status"
    })

    df["order_date"] = pd.to_datetime(df.get("order_date"), errors="coerce")
    df["revenue"] = pd.to_numeric(df.get("revenue"), errors="coerce")
    df["qty"] = pd.to_numeric(df.get("qty"), errors="coerce")

    con = duckdb.connect(database=":memory:")
    con.execute("CREATE TABLE sales AS SELECT * FROM df")

    if return_df:
        return con, df
    return con
