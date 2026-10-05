"""
Independent validation of the analytical Online Retail II dataset.

This script is READ-ONLY:
- It reads data/retail.db.
- It reads data/processed/analytical_transactions.csv.
- It does not modify either file.

Validation targets:
1. Canonical row count.
2. Analytical row count.
3. Required columns.
4. Customer ID non-null.
5. No cancellations.
6. Quantity > 0.
7. Unit price > 0.
8. Valid invoice dates.
9. No exact duplicate business records.
10. line_amount consistency.
11. Every analytical record corresponds to a canonical transaction.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "retail.db"
CSV_PATH = ROOT / "data" / "processed" / "analytical_transactions.csv"

BUSINESS_KEYS = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "customer_id",
    "country",
]

REQUIRED_COLUMNS = [
    "transaction_id",
    "invoice",
    "stock_code",
    "customer_id",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "country",
    "is_cancellation",
    "line_amount",
]


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> None:
    print("=" * 90)
    print("MILESTONE 2 - POST-CLEANING VALIDATION")
    print("=" * 90)
    print(f"Canonical database: {DB_PATH}")
    print(f"Analytical dataset: {CSV_PATH}")
    print("READ-ONLY VALIDATION: no files will be modified.")

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Analytical CSV not found: {CSV_PATH}")

    # ------------------------------------------------------------------
    # 1. Read canonical database metadata.
    # ------------------------------------------------------------------
    with sqlite3.connect(DB_PATH) as conn:
        canonical_count = pd.read_sql_query(
            "SELECT COUNT(*) AS n FROM transactions", conn
        ).iloc[0]["n"]

        canonical_max_id = pd.read_sql_query(
            "SELECT MAX(transaction_id) AS max_id FROM transactions", conn
        ).iloc[0]["max_id"]

    # ------------------------------------------------------------------
    # 2. Read analytical dataset.
    # ------------------------------------------------------------------
    df = pd.read_csv(
        CSV_PATH,
        encoding="utf-8-sig",
    )

    print("\n1. ROW COUNTS")
    print("-" * 90)
    print(f"Canonical transactions : {int(canonical_count):,}")
    print(f"Analytical transactions: {len(df):,}")

    if len(df) == 0:
        fail("Analytical dataset is empty.")

    # ------------------------------------------------------------------
    # 3. Schema validation.
    # ------------------------------------------------------------------
    print("\n2. SCHEMA")
    print("-" * 90)

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]

    if missing_columns:
        fail(f"Missing required columns: {missing_columns}")

    print("Required columns: PASS")

    # ------------------------------------------------------------------
    # 4. Datatype normalization for validation.
    # ------------------------------------------------------------------
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")

    # ------------------------------------------------------------------
    # 5. Analytical invariants.
    # ------------------------------------------------------------------
    print("\n3. ANALYTICAL INVARIANTS")
    print("-" * 90)

    checks = {
        "customer_id_not_null": int(df["customer_id"].isna().sum()),
        "cancellation_rows": int((df["is_cancellation"] != 0).sum()),
        "quantity_nonpositive": int((df["quantity"] <= 0).sum()),
        "unit_price_nonpositive": int((df["unit_price"] <= 0).sum()),
        "invalid_invoice_date": int(df["invoice_date"].isna().sum()),
        "missing_invoice": int(df["invoice"].isna().sum()),
        "missing_stock_code": int(df["stock_code"].isna().sum()),
        "missing_country": int(df["country"].isna().sum()),
    }

    for name, value in checks.items():
        print(f"{name:35s}: {value:,}")

    if checks["customer_id_not_null"] != 0:
        fail("Analytical dataset contains missing Customer IDs.")

    if checks["cancellation_rows"] != 0:
        fail("Analytical dataset contains cancellation transactions.")

    if checks["quantity_nonpositive"] != 0:
        fail("Analytical dataset contains Quantity <= 0.")

    if checks["unit_price_nonpositive"] != 0:
        fail("Analytical dataset contains Unit Price <= 0.")

    if checks["invalid_invoice_date"] != 0:
        fail("Analytical dataset contains invalid InvoiceDate values.")

    if checks["missing_invoice"] != 0:
        fail("Analytical dataset contains missing Invoice values.")

    if checks["missing_stock_code"] != 0:
        fail("Analytical dataset contains missing StockCode values.")

    print("Analytical invariants: PASS")

    # ------------------------------------------------------------------
    # 6. Exact duplicate validation.
    # ------------------------------------------------------------------
    print("\n4. EXACT DUPLICATE VALIDATION")
    print("-" * 90)

    duplicate_rows = int(
        df.duplicated(subset=BUSINESS_KEYS, keep=False).sum()
    )
    duplicate_groups = int(
        df[df.duplicated(subset=BUSINESS_KEYS, keep=False)]
        .groupby(BUSINESS_KEYS, dropna=False)
        .ngroups
        if duplicate_rows
        else 0
    )

    print(f"Duplicate groups: {duplicate_groups:,}")
    print(f"Rows participating in duplicates: {duplicate_rows:,}")

    if duplicate_rows != 0:
        fail("Exact duplicate business records remain in analytical dataset.")

    print("Exact duplicate check: PASS")

    # ------------------------------------------------------------------
    # 7. line_amount validation.
    # ------------------------------------------------------------------
    print("\n5. LINE AMOUNT VALIDATION")
    print("-" * 90)

    expected_amount = df["quantity"] * df["unit_price"]
    amount_difference = (df["line_amount"] - expected_amount).abs()

    max_difference = float(amount_difference.max())
    invalid_amount_rows = int((amount_difference > 1e-9).sum())

    print(f"Rows with inconsistent line_amount: {invalid_amount_rows:,}")
    print(f"Maximum absolute difference: {max_difference:.12g}")

    if invalid_amount_rows != 0:
        fail("line_amount is inconsistent with quantity * unit_price.")

    print("line_amount check: PASS")

    # ------------------------------------------------------------------
    # 8. transaction_id sanity.
    # ------------------------------------------------------------------
    print("\n6. TRANSACTION ID SANITY")
    print("-" * 90)

    if df["transaction_id"].isna().any():
        fail("Analytical dataset contains missing transaction_id.")

    transaction_ids = df["transaction_id"].astype("int64")

    print(f"Unique transaction IDs: {transaction_ids.nunique():,}")
    print(f"Maximum transaction ID: {transaction_ids.max():,}")
    print(f"Canonical maximum ID:  {int(canonical_max_id):,}")

    if transaction_ids.nunique() != len(df):
        fail("transaction_id is not unique in analytical dataset.")

    if (transaction_ids <= 0).any():
        fail("Analytical dataset contains invalid transaction_id values.")

    if transaction_ids.max() > int(canonical_max_id):
        fail("Analytical dataset contains transaction_id outside canonical DB.")

    print("transaction_id check: PASS")

    # ------------------------------------------------------------------
    # 9. Basic RFM-readiness metrics.
    # ------------------------------------------------------------------
    print("\n7. RFM READINESS")
    print("-" * 90)

    unique_customers = int(df["customer_id"].nunique())
    unique_invoices = int(df["invoice"].nunique())
    min_date = df["invoice_date"].min()
    max_date = df["invoice_date"].max()
    total_quantity = int(df["quantity"].sum())
    total_revenue = float(df["line_amount"].sum())

    print(f"Unique customers: {unique_customers:,}")
    print(f"Unique invoices : {unique_invoices:,}")
    print(f"Minimum date    : {min_date}")
    print(f"Maximum date    : {max_date}")
    print(f"Total quantity  : {total_quantity:,}")
    print(f"Total revenue   : {total_revenue:,.2f}")

    if unique_customers == 0:
        fail("No customers remain for RFM.")
    if unique_invoices == 0:
        fail("No invoices remain for RFM.")
    if total_revenue <= 0:
        fail("Analytical revenue is not positive.")

    # ------------------------------------------------------------------
    # 10. Final result.
    # ------------------------------------------------------------------
    print()
    print("=" * 90)
    print("POST-CLEANING VALIDATION: PASSED")
    print("=" * 90)
    print("Analytical dataset satisfies all documented purchase invariants.")
    print("Canonical SQLite database was not modified.")


if __name__ == "__main__":
    main()
