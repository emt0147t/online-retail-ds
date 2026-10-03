"""
Milestone 2 quality investigation for the canonical Online Retail II database.

This script is READ-ONLY. It does not modify data/retail.db.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "retail.db"


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def header(number: int, title: str) -> None:
    print()
    print("=" * 90)
    print(f"{number}. {title}")
    print("=" * 90)


def investigate_duplicate_multiplicity(conn: sqlite3.Connection) -> None:
    header(1, "EXACT DUPLICATE MULTIPLICITY")
    groups = pd.read_sql_query(
        """
        SELECT invoice, stock_code, description, quantity, invoice_date,
               unit_price, customer_id, country, COUNT(*) AS multiplicity
        FROM transactions
        GROUP BY invoice, stock_code, description, quantity, invoice_date,
                 unit_price, customer_id, country
        HAVING COUNT(*) > 1
        ORDER BY multiplicity DESC, invoice
        """,
        conn,
    )
    if groups.empty:
        print("No exact duplicate groups found.")
        return

    groups["rows_beyond_first"] = groups["multiplicity"] - 1
    print(f"Duplicate groups: {len(groups):,}")
    print(f"Rows participating in duplicate groups: {groups['multiplicity'].sum():,}")
    print(f"Rows beyond first occurrence: {groups['rows_beyond_first'].sum():,}")
    print(f"Maximum multiplicity: {groups['multiplicity'].max():,}")

    print("\nMultiplicity distribution:")
    distribution = (
        groups["multiplicity"].value_counts()
        .sort_index()
        .rename_axis("multiplicity")
        .reset_index(name="duplicate_groups")
    )
    distribution["rows_in_groups"] = (
        distribution["multiplicity"] * distribution["duplicate_groups"]
    )
    print(distribution.to_string(index=False))

    print("\nTop 10 duplicate groups:")
    print(
        groups[
            ["invoice", "stock_code", "quantity", "unit_price",
             "customer_id", "multiplicity"]
        ].head(10).to_string(index=False)
    )


def investigate_duplicates_by_invoice(conn: sqlite3.Connection) -> None:
    header(2, "DUPLICATE GROUPS BY INVOICE")
    invoice_stats = pd.read_sql_query(
        """
        SELECT invoice, COUNT(*) AS transaction_rows,
               COUNT(*) - COUNT(
                   DISTINCT stock_code || '|' ||
                   COALESCE(description, '<NULL>') || '|' ||
                   quantity || '|' || invoice_date || '|' ||
                   unit_price || '|' ||
                   COALESCE(customer_id, '<NULL>') || '|' || country
               ) AS rows_beyond_exact_unique
        FROM transactions
        GROUP BY invoice
        HAVING rows_beyond_exact_unique > 0
        ORDER BY rows_beyond_exact_unique DESC, transaction_rows DESC
        """,
        conn,
    )
    if invoice_stats.empty:
        print("No invoices contain exact duplicate transaction combinations.")
        return

    print(f"Invoices containing duplicate combinations: {len(invoice_stats):,}")
    print(
        "Rows beyond exact-unique combinations: "
        f"{invoice_stats['rows_beyond_exact_unique'].sum():,}"
    )
    print("\nTop 10 affected invoices:")
    print(invoice_stats.head(10).to_string(index=False))


def investigate_nonpositive_price_by_stockcode(conn: sqlite3.Connection) -> None:
    header(3, "NON-POSITIVE PRICE BY STOCKCODE")
    result = pd.read_sql_query(
        """
        SELECT stock_code,
               COUNT(*) AS rows_nonpositive_price,
               SUM(CASE WHEN unit_price < 0 THEN 1 ELSE 0 END) AS negative_price_rows,
               SUM(CASE WHEN unit_price = 0 THEN 1 ELSE 0 END) AS zero_price_rows,
               SUM(CASE WHEN is_cancellation = 1 THEN 1 ELSE 0 END) AS cancellation_rows,
               COUNT(DISTINCT COALESCE(customer_id, -1)) AS distinct_customer_ids,
               GROUP_CONCAT(DISTINCT description) AS descriptions
        FROM transactions
        WHERE unit_price <= 0
        GROUP BY stock_code
        ORDER BY rows_nonpositive_price DESC, stock_code
        """,
        conn,
    )
    if result.empty:
        print("No rows with unit_price <= 0.")
        return

    print(f"StockCodes with unit_price <= 0: {len(result):,}")
    print(f"Rows with unit_price <= 0: {result['rows_nonpositive_price'].sum():,}")
    print(f"Negative-price rows: {result['negative_price_rows'].sum():,}")
    print(f"Zero-price rows: {result['zero_price_rows'].sum():,}")
    print("\nTop 20 StockCodes:")
    print(result.head(20).to_string(index=False, max_colwidth=80))


def investigate_price_vs_cancellation(conn: sqlite3.Connection) -> None:
    header(4, "NON-POSITIVE PRICE VS CANCELLATION")
    result = pd.read_sql_query(
        """
        SELECT
            CASE WHEN unit_price < 0 THEN 'price < 0'
                 WHEN unit_price = 0 THEN 'price = 0'
                 ELSE 'price > 0' END AS price_class,
            CASE WHEN is_cancellation = 1 THEN 'cancellation'
                 ELSE 'non-cancellation' END AS cancellation_class,
            COUNT(*) AS rows,
            SUM(quantity * unit_price) AS total_line_amount
        FROM transactions
        WHERE unit_price <= 0
        GROUP BY price_class, cancellation_class
        ORDER BY price_class, cancellation_class
        """,
        conn,
    )
    if result.empty:
        print("No rows with unit_price <= 0.")
        return
    print(result.to_string(index=False))

    combo = pd.read_sql_query(
        """
        SELECT
            SUM(CASE WHEN unit_price = 0 AND is_cancellation = 1 THEN 1 ELSE 0 END)
                AS zero_price_cancellations,
            SUM(CASE WHEN unit_price = 0 AND is_cancellation = 0 THEN 1 ELSE 0 END)
                AS zero_price_non_cancellations,
            SUM(CASE WHEN unit_price < 0 AND is_cancellation = 1 THEN 1 ELSE 0 END)
                AS negative_price_cancellations,
            SUM(CASE WHEN unit_price < 0 AND is_cancellation = 0 THEN 1 ELSE 0 END)
                AS negative_price_non_cancellations
        FROM transactions
        """,
        conn,
    )
    print("\nDirect count:")
    print(combo.to_string(index=False))


def investigate_missing_description_recoverability(conn: sqlite3.Connection) -> None:
    header(5, "MISSING DESCRIPTION RECOVERABILITY BY STOCKCODE")
    stockcode = pd.read_sql_query(
        """
        SELECT stock_code, COUNT(*) AS total_rows,
               SUM(CASE WHEN description IS NULL OR TRIM(description) = ''
                        THEN 1 ELSE 0 END) AS missing_description_rows,
               COUNT(DISTINCT CASE
                   WHEN description IS NOT NULL AND TRIM(description) <> ''
                   THEN description END) AS nonnull_description_count
        FROM transactions
        GROUP BY stock_code
        HAVING missing_description_rows > 0
        ORDER BY missing_description_rows DESC, stock_code
        """,
        conn,
    )
    if stockcode.empty:
        print("No missing descriptions found.")
        return

    stockcode["recoverable_from_unique_description"] = (
        (stockcode["missing_description_rows"] > 0)
        & (stockcode["nonnull_description_count"] == 1)
    )
    print(f"StockCodes with missing-description rows: {len(stockcode):,}")
    print(
        "Recoverable StockCodes (one non-null description): "
        f"{stockcode['recoverable_from_unique_description'].sum():,}"
    )
    print(
        "Not safely recoverable: "
        f"{(~stockcode['recoverable_from_unique_description']).sum():,}"
    )
    print(
        "Total missing-description rows: "
        f"{stockcode['missing_description_rows'].sum():,}"
    )
    print("\nTop 20 StockCodes:")
    print(stockcode.head(20).to_string(index=False))


def investigate_customer_country_conflicts(conn: sqlite3.Connection) -> None:
    header(6, "CUSTOMER-COUNTRY CONSISTENCY")
    conflicts = pd.read_sql_query(
        """
        SELECT customer_id, COUNT(DISTINCT country) AS distinct_countries,
               GROUP_CONCAT(DISTINCT country) AS countries,
               COUNT(*) AS transaction_rows
        FROM transactions
        WHERE customer_id IS NOT NULL
          AND country IS NOT NULL
          AND TRIM(country) <> ''
        GROUP BY customer_id
        HAVING COUNT(DISTINCT country) > 1
        ORDER BY transaction_rows DESC, customer_id
        """,
        conn,
    )
    if conflicts.empty:
        print("No customers have multiple countries.")
        return
    print(f"Customers with multiple countries: {len(conflicts):,}")
    print(conflicts.to_string(index=False))


def investigate_negative_quantity_without_cancellation(
    conn: sqlite3.Connection,
) -> None:
    header(7, "NEGATIVE QUANTITY WITHOUT CANCELLATION")
    summary = pd.read_sql_query(
        """
        SELECT
            CASE WHEN is_cancellation = 1 THEN 'cancellation'
                 ELSE 'non-cancellation' END AS cancellation_class,
            COUNT(*) AS rows,
            SUM(quantity) AS total_quantity,
            SUM(quantity * unit_price) AS total_line_amount
        FROM transactions
        WHERE quantity < 0
        GROUP BY cancellation_class
        ORDER BY cancellation_class
        """,
        conn,
    )
    print(summary.to_string(index=False))

    examples = pd.read_sql_query(
        """
        SELECT invoice, stock_code, description, quantity, unit_price,
               customer_id, country, invoice_date
        FROM transactions
        WHERE quantity < 0 AND is_cancellation = 0
        ORDER BY invoice_date, invoice, stock_code
        LIMIT 30
        """,
        conn,
    )
    print("\nExamples (up to 30) of negative-quantity non-cancellation rows:")
    if examples.empty:
        print("None found.")
    else:
        print(examples.to_string(index=False, max_colwidth=80))


def main() -> None:
    print("=" * 90)
    print("MILESTONE 2 - QUALITY INVESTIGATION")
    print("=" * 90)
    print(f"Database: {DB_PATH}")
    print("READ-ONLY: no data will be modified.")

    with get_connection() as conn:
        investigate_duplicate_multiplicity(conn)
        investigate_duplicates_by_invoice(conn)
        investigate_nonpositive_price_by_stockcode(conn)
        investigate_price_vs_cancellation(conn)
        investigate_missing_description_recoverability(conn)
        investigate_customer_country_conflicts(conn)
        investigate_negative_quantity_without_cancellation(conn)

    print("\n" + "=" * 90)
    print("INVESTIGATION COMPLETE")
    print("=" * 90)
    print("No data was modified by this script.")


if __name__ == "__main__":
    main()
