from pathlib import Path
import sqlite3

import pandas as pd


# =========================================================
# Paths
# =========================================================

RAW_FILE = Path("data/raw/online_retail_II.xlsx")
SCHEMA_FILE = Path("sql/schema.sql")
DB_FILE = Path("data/retail.db")


SHEET_1 = "Year 2009-2010"
SHEET_2 = "Year 2010-2011"


# =========================================================
# Normalization
# =========================================================

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize data types and string representations.

    This function does not perform analytical cleaning.
    It only makes the representation consistent.
    """

    df = df.copy()

    # String columns
    for column in [
        "Invoice",
        "StockCode",
        "Description",
        "Country",
    ]:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Numeric columns
    df["Quantity"] = pd.to_numeric(
        df["Quantity"],
        errors="coerce",
    ).astype("Int64")

    df["Price"] = pd.to_numeric(
        df["Price"],
        errors="coerce",
    )

    df["Customer ID"] = pd.to_numeric(
        df["Customer ID"],
        errors="coerce",
    ).astype("Int64")

    # Datetime
    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce",
    )

    # Cancellation signal
    df["is_cancellation"] = (
        df["Invoice"]
        .str.upper()
        .str.startswith("C")
        .fillna(False)
        .astype(int)
    )

    return df


# =========================================================
# Read sheets
# =========================================================

def read_sheet(
    file_path: Path,
    sheet_name: str,
) -> pd.DataFrame:

    print(f"Reading: {sheet_name}")

    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
    )

    return normalize_dataframe(df)


# =========================================================
# Build canonical dataset
# =========================================================

def build_canonical_dataset() -> pd.DataFrame:

    df1 = read_sheet(
        RAW_FILE,
        SHEET_1,
    )

    df2 = read_sheet(
        RAW_FILE,
        SHEET_2,
    )

    print("\n" + "=" * 80)
    print("CROSS-SHEET REPLICATION REMOVAL")
    print("=" * 80)

    # We already verified that:
    #
    # - there are 1,088 common invoices
    # - there are 22,523 rows belonging to those invoices
    #   in each sheet
    # - every exact transaction combination has identical
    #   multiplicity in both sheets
    #
    # Therefore Sheet 2's rows belonging to common invoices
    # are replicated rows.

    invoices_1 = set(
        df1["Invoice"]
        .dropna()
        .unique()
    )

    invoices_2 = set(
        df2["Invoice"]
        .dropna()
        .unique()
    )

    common_invoices = invoices_1.intersection(
        invoices_2
    )

    print(
        f"Common invoices: "
        f"{len(common_invoices):,}"
    )

    sheet2_before = len(df2)

    df2 = df2[
        ~df2["Invoice"].isin(common_invoices)
    ].copy()

    removed = sheet2_before - len(df2)

    print(
        f"Removed replicated Sheet-2 rows: "
        f"{removed:,}"
    )

    canonical = pd.concat(
        [df1, df2],
        ignore_index=True,
    )

    expected_rows = 1_067_371 - 22_523

    print(
        f"Canonical rows: "
        f"{len(canonical):,}"
    )

    print(
        f"Expected rows: "
        f"{expected_rows:,}"
    )

    if len(canonical) != expected_rows:
        raise RuntimeError(
            "Canonical row count does not match "
            "the audited expectation."
        )

    return canonical


# =========================================================
# Build entity tables
# =========================================================

def build_customers(
    canonical: pd.DataFrame,
) -> pd.DataFrame:

    customers = (
        canonical[["Customer ID"]]
        .dropna(subset=["Customer ID"])
        .drop_duplicates()
        .rename(
            columns={
                "Customer ID": "customer_id",
            }
        )
    )

    return customers


def build_products(
    canonical: pd.DataFrame,
) -> pd.DataFrame:

    products = (
        canonical[["StockCode"]]
        .dropna(subset=["StockCode"])
        .drop_duplicates()
        .rename(
            columns={
                "StockCode": "stock_code",
            }
        )
    )

    return products


def build_transactions(
    canonical: pd.DataFrame,
) -> pd.DataFrame:

    transactions = canonical[
        [
            "Invoice",
            "StockCode",
            "Customer ID",
            "Description",
            "Quantity",
            "InvoiceDate",
            "Price",
            "Country",
            "is_cancellation",
        ]
    ].copy()

    transactions = transactions.rename(
        columns={
            "Invoice": "invoice",
            "StockCode": "stock_code",
            "Customer ID": "customer_id",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "Price": "unit_price",
            "Country": "country",
        }
    )

    return transactions


# =========================================================
# Database
# =========================================================

def create_database(
    canonical: pd.DataFrame,
) -> None:

    DB_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove existing database so that the ETL is reproducible.
    if DB_FILE.exists():
        print(
            f"\nRemoving existing database: "
            f"{DB_FILE}"
        )
        DB_FILE.unlink()

    connection = sqlite3.connect(
        DB_FILE
    )

    try:

        # -----------------------------------------------------
        # Enable FK enforcement
        # -----------------------------------------------------

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        # -----------------------------------------------------
        # Create schema
        # -----------------------------------------------------

        schema_sql = SCHEMA_FILE.read_text(
            encoding="utf-8"
        )

        connection.executescript(
            schema_sql
        )

        # -----------------------------------------------------
        # Build tables
        # -----------------------------------------------------

        customers = build_customers(
            canonical
        )

        products = build_products(
            canonical
        )

        transactions = build_transactions(
            canonical
        )

        print("\n" + "=" * 80)
        print("LOADING TABLES")
        print("=" * 80)

        # -----------------------------------------------------
        # Customers
        # -----------------------------------------------------

        customers.to_sql(
            "customers",
            connection,
            if_exists="append",
            index=False,
        )

        print(
            f"customers: "
            f"{len(customers):,}"
        )

        # -----------------------------------------------------
        # Products
        # -----------------------------------------------------

        products.to_sql(
            "products",
            connection,
            if_exists="append",
            index=False,
        )

        print(
            f"products: "
            f"{len(products):,}"
        )

        # -----------------------------------------------------
        # Transactions
        # -----------------------------------------------------

        transactions.to_sql(
            "transactions",
            connection,
            if_exists="append",
            index=False,
            chunksize=10_000,
        )

        print(
            f"transactions: "
            f"{len(transactions):,}"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# =========================================================
# Main
# =========================================================

def main() -> None:

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: {RAW_FILE}"
        )

    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(
            f"Schema file not found: {SCHEMA_FILE}"
        )

    print("=" * 80)
    print("ONLINE RETAIL II → SQLITE")
    print("=" * 80)

    canonical = build_canonical_dataset()

    create_database(canonical)

    print("\n" + "=" * 80)
    print("ETL COMPLETE")
    print("=" * 80)

    print(
        f"Database created at: "
        f"{DB_FILE}"
    )


if __name__ == "__main__":
    main()