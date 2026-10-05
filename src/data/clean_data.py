"""
Create the analytical transaction dataset for Online Retail II.

This script:
1. Reads the canonical SQLite database.
2. Recovers missing descriptions only when StockCode has exactly one
   non-null description.
3. Builds a customer-purchase analytical dataset using the documented policy.
4. Removes exact duplicate business records deterministically from the
   analytical dataset so RFM metrics are not silently inflated.
5. Writes:
   - data/processed/analytical_transactions.csv
   - data/processed/cleaning_summary.csv

The canonical database is READ-ONLY and is never modified.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "retail.db"
OUTPUT_DIR = ROOT / "data" / "processed"

ANALYTICAL_OUTPUT = OUTPUT_DIR / "analytical_transactions.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "cleaning_summary.csv"

# Business columns used to detect exact duplicates.
DUPLICATE_KEYS = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "customer_id",
    "country",
]


def load_transactions() -> pd.DataFrame:
    """Load all canonical transactions from SQLite."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    query = """
        SELECT
            transaction_id,
            invoice,
            stock_code,
            customer_id,
            description,
            quantity,
            invoice_date,
            unit_price,
            country,
            is_cancellation
        FROM transactions
    """

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn)

    if df.empty:
        raise RuntimeError("Canonical transactions table is empty.")

    df["invoice_date"] = pd.to_datetime(
        df["invoice_date"],
        errors="coerce",
    )

    return df


def recover_descriptions(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Recover missing descriptions only when a StockCode has exactly one
    distinct non-null description in the canonical dataset.
    """
    df = df.copy()

    valid_descriptions = (
        df.loc[
            df["description"].notna()
            & df["description"].astype(str).str.strip().ne(""),
            ["stock_code", "description"],
        ]
        .drop_duplicates()
    )

    description_counts = (
        valid_descriptions.groupby("stock_code")["description"]
        .nunique()
        .rename("nonnull_description_count")
    )

    recoverable = description_counts[description_counts == 1].index

    lookup = (
        valid_descriptions[
            valid_descriptions["stock_code"].isin(recoverable)
        ]
        .drop_duplicates("stock_code")
        .set_index("stock_code")["description"]
    )

    missing_mask = (
        df["description"].isna()
        | df["description"].astype(str).str.strip().eq("")
    )

    recover_mask = missing_mask & df["stock_code"].isin(lookup.index)

    recovered_count = int(recover_mask.sum())

    if recovered_count:
        df.loc[recover_mask, "description"] = (
            df.loc[recover_mask, "stock_code"].map(lookup)
        )

    return df, recovered_count


def build_analytical_dataset(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Apply the analytical purchase policy.

    Canonical records are never modified. Filtering is performed on an
    in-memory dataframe and the resulting analytical dataset is written
    separately.
    """
    stats: dict[str, int] = {}

    stats["input_rows"] = len(df)

    # Basic validity.
    invalid_date = int(df["invoice_date"].isna().sum())
    stats["invalid_invoice_date"] = invalid_date

    # Exclude rows without Customer ID from customer-level analytics.
    missing_customer = int(df["customer_id"].isna().sum())
    stats["excluded_missing_customer_id"] = missing_customer

    work = df[df["customer_id"].notna()].copy()

    # Exclude cancellation transactions.
    cancellation_count = int((work["is_cancellation"] == 1).sum())
    stats["excluded_cancellations"] = cancellation_count

    work = work[work["is_cancellation"] == 0].copy()

    # Exclude non-positive quantity.
    nonpositive_quantity = int((work["quantity"] <= 0).sum())
    stats["excluded_nonpositive_quantity"] = nonpositive_quantity

    work = work[work["quantity"] > 0].copy()

    # Exclude non-positive unit price.
    nonpositive_price = int((work["unit_price"] <= 0).sum())
    stats["excluded_nonpositive_unit_price"] = nonpositive_price

    work = work[work["unit_price"] > 0].copy()

    # Exclude invalid dates.
    work = work[work["invoice_date"].notna()].copy()
    stats["excluded_invalid_invoice_date"] = invalid_date

    # Exact duplicate business records.
    duplicate_mask = work.duplicated(
        subset=DUPLICATE_KEYS,
        keep="first",
    )

    duplicate_rows_removed = int(duplicate_mask.sum())
    stats["excluded_exact_duplicates"] = duplicate_rows_removed

    work = work.loc[~duplicate_mask].copy()

    # Derived analytical value.
    work["line_amount"] = work["quantity"] * work["unit_price"]

    # Stable output order.
    work = work.sort_values(
        by=["invoice_date", "invoice", "stock_code", "transaction_id"]
    ).reset_index(drop=True)

    stats["output_rows"] = len(work)

    return work, stats


def write_outputs(
    analytical_df: pd.DataFrame,
    stats: dict[str, int],
    recovered_descriptions: int,
) -> None:
    """Write analytical dataset and cleaning summary."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    analytical_df.to_csv(
        ANALYTICAL_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        **stats,
        "recovered_descriptions": recovered_descriptions,
    }

    summary_df = pd.DataFrame(
        list(summary.items()),
        columns=["metric", "value"],
    )

    summary_df.to_csv(
        SUMMARY_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )


def validate_outputs(
    analytical_df: pd.DataFrame,
) -> None:
    """Fail loudly if analytical invariants are violated."""
    if analytical_df.empty:
        raise RuntimeError(
            "Analytical dataset is empty. Review cleaning rules."
        )

    assert analytical_df["customer_id"].notna().all()
    assert (analytical_df["is_cancellation"] == 0).all()
    assert (analytical_df["quantity"] > 0).all()
    assert (analytical_df["unit_price"] > 0).all()
    assert analytical_df["invoice_date"].notna().all()
    assert analytical_df["line_amount"].notna().all()

    duplicate_mask = analytical_df.duplicated(
        subset=DUPLICATE_KEYS,
        keep=False,
    )

    if duplicate_mask.any():
        raise AssertionError(
            "Exact duplicate business records remain in the analytical dataset."
        )


def main() -> None:
    print("=" * 90)
    print("MILESTONE 2 - CLEANING IMPLEMENTATION")
    print("=" * 90)
    print(f"Canonical database: {DB_PATH}")
    print("Canonical database will NOT be modified.")

    df = load_transactions()

    print(f"Input canonical rows: {len(df):,}")

    df, recovered_descriptions = recover_descriptions(df)

    print(
        "Recovered missing descriptions: "
        f"{recovered_descriptions:,}"
    )

    analytical_df, stats = build_analytical_dataset(df)

    validate_outputs(analytical_df)

    write_outputs(
        analytical_df=analytical_df,
        stats=stats,
        recovered_descriptions=recovered_descriptions,
    )

    print()
    print("CLEANING SUMMARY")
    print("-" * 90)

    for key, value in stats.items():
        print(f"{key:35s}: {value:,}")

    print(
        f"{'recovered_descriptions':35s}: "
        f"{recovered_descriptions:,}"
    )

    print()
    print("OUTPUTS")
    print("-" * 90)
    print(f"Analytical dataset: {ANALYTICAL_OUTPUT}")
    print(f"Cleaning summary:   {SUMMARY_OUTPUT}")

    print()
    print("=" * 90)
    print("CLEANING COMPLETE")
    print("=" * 90)
    print("Canonical SQLite database was not modified.")


if __name__ == "__main__":
    main()