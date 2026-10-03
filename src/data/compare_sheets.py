from pathlib import Path

import pandas as pd


RAW_FILE = Path("data/raw/online_retail_II.xlsx")

COMPARE_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize columns so that the same logical values have
    the same representation across both sheets.
    """

    df = df.copy()

    # ---------------------------------------------------------
    # String columns
    # ---------------------------------------------------------

    for column in ["Invoice", "StockCode", "Country"]:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Description:
    # preserve missingness, then use a sentinel only for
    # exact-comparison operations later.
    df["Description"] = (
        df["Description"]
        .astype("string")
        .str.strip()
    )

    # ---------------------------------------------------------
    # Numeric columns
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Date
    # ---------------------------------------------------------

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce",
    )

    return df


def canonicalize_for_exact_comparison(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a canonical representation suitable for exact
    cross-sheet comparison.

    Missing values are converted to a common sentinel so
    that NaN/NA in both sheets can be compared consistently.
    """

    result = df[COMPARE_COLUMNS].copy()

    # Strings
    for column in [
        "Invoice",
        "StockCode",
        "Description",
        "Country",
    ]:
        result[column] = (
            result[column]
            .astype("string")
            .fillna("<NA>")
        )

    # Integers
    for column in [
        "Quantity",
        "Customer ID",
    ]:
        result[column] = (
            result[column]
            .astype("string")
            .fillna("<NA>")
        )

    # Datetime
    result["InvoiceDate"] = (
        pd.to_datetime(
            result["InvoiceDate"],
            errors="coerce",
        )
        .astype("string")
        .fillna("<NA>")
    )

    # Float
    result["Price"] = (
        pd.to_numeric(
            result["Price"],
            errors="coerce",
        )
        .round(10)
        .astype("string")
        .fillna("<NA>")
    )

    return result


def main() -> None:

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {RAW_FILE}"
        )

    excel = pd.ExcelFile(RAW_FILE)

    sheet1_name = excel.sheet_names[0]
    sheet2_name = excel.sheet_names[1]

    print("=" * 90)
    print("CROSS-SHEET DATA AUDIT")
    print("=" * 90)

    # ---------------------------------------------------------
    # Read
    # ---------------------------------------------------------

    df1_raw = pd.read_excel(
        RAW_FILE,
        sheet_name=sheet1_name,
    )

    df2_raw = pd.read_excel(
        RAW_FILE,
        sheet_name=sheet2_name,
    )

    # ---------------------------------------------------------
    # Diagnose Invoice types BEFORE normalization
    # ---------------------------------------------------------

    print("\n[1] ORIGINAL INVOICE TYPES")

    print(f"\n{sheet1_name}:")
    print(
        df1_raw["Invoice"]
        .map(type)
        .value_counts()
    )

    print(f"\n{sheet2_name}:")
    print(
        df2_raw["Invoice"]
        .map(type)
        .value_counts()
    )

    # ---------------------------------------------------------
    # Normalize
    # ---------------------------------------------------------

    df1 = normalize_dataframe(df1_raw)
    df2 = normalize_dataframe(df2_raw)

    print("\n[2] NORMALIZED INVOICE TYPES")

    print(f"\n{sheet1_name}:")
    print(
        df1["Invoice"]
        .map(type)
        .value_counts()
    )

    print(f"\n{sheet2_name}:")
    print(
        df2["Invoice"]
        .map(type)
        .value_counts()
    )

    # ---------------------------------------------------------
    # Common invoices
    # ---------------------------------------------------------

    invoices1 = set(
        df1["Invoice"]
        .dropna()
        .unique()
    )

    invoices2 = set(
        df2["Invoice"]
        .dropna()
        .unique()
    )

    common_invoices = (
        invoices1.intersection(invoices2)
    )

    print("\n[3] COMMON INVOICES")

    print(
        f"Unique invoices in {sheet1_name}: "
        f"{len(invoices1):,}"
    )

    print(
        f"Unique invoices in {sheet2_name}: "
        f"{len(invoices2):,}"
    )

    print(
        f"Common invoice numbers: "
        f"{len(common_invoices):,}"
    )

    # ---------------------------------------------------------
    # Common invoice row counts
    # ---------------------------------------------------------

    common_rows1 = df1[
        df1["Invoice"].isin(common_invoices)
    ].copy()

    common_rows2 = df2[
        df2["Invoice"].isin(common_invoices)
    ].copy()

    print("\n[4] ROW COUNTS FOR COMMON INVOICES")

    print(
        f"{sheet1_name}: "
        f"{len(common_rows1):,}"
    )

    print(
        f"{sheet2_name}: "
        f"{len(common_rows2):,}"
    )

    # ---------------------------------------------------------
    # Exact comparison
    # ---------------------------------------------------------

    canonical1 = canonicalize_for_exact_comparison(
        df1
    )

    canonical2 = canonicalize_for_exact_comparison(
        df2
    )

    # Keep unique exact transaction combinations
    unique1 = canonical1.drop_duplicates(
        subset=COMPARE_COLUMNS
    )

    unique2 = canonical2.drop_duplicates(
        subset=COMPARE_COLUMNS
    )

    # Convert to tuples for set intersection
    set1 = set(
        map(tuple, unique1.to_numpy())
    )

    set2 = set(
        map(tuple, unique2.to_numpy())
    )

    exact_common = set1.intersection(set2)

    print("\n[5] EXACT CROSS-SHEET TRANSACTION MATCHES")

    print(
        f"Unique exact transaction combinations "
        f"in {sheet1_name}: "
        f"{len(set1):,}"
    )

    print(
        f"Unique exact transaction combinations "
        f"in {sheet2_name}: "
        f"{len(set2):,}"
    )

    print(
        f"Unique exact transaction combinations "
        f"present in BOTH: "
        f"{len(exact_common):,}"
    )

    # ---------------------------------------------------------
    # Exact matches restricted to common invoices
    # ---------------------------------------------------------

    common_canonical1 = canonical1[
        canonical1["Invoice"].isin(common_invoices)
    ]

    common_canonical2 = canonical2[
        canonical2["Invoice"].isin(common_invoices)
    ]

    common_unique1 = common_canonical1.drop_duplicates(
        subset=COMPARE_COLUMNS
    )

    common_unique2 = common_canonical2.drop_duplicates(
        subset=COMPARE_COLUMNS
    )

    common_set1 = set(
        map(tuple, common_unique1.to_numpy())
    )

    common_set2 = set(
        map(tuple, common_unique2.to_numpy())
    )

    exact_common_invoice_rows = (
        common_set1.intersection(common_set2)
    )

    print(
        "\nExact transaction combinations "
        f"within common invoices: "
        f"{len(exact_common_invoice_rows):,}"
    )

    # ---------------------------------------------------------
    # Date overlap
    # ---------------------------------------------------------

    start1 = df1["InvoiceDate"].min()
    end1 = df1["InvoiceDate"].max()

    start2 = df2["InvoiceDate"].min()
    end2 = df2["InvoiceDate"].max()

    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)

    print("\n[6] DATE RANGE")

    print(
        f"{sheet1_name}: "
        f"{start1} → {end1}"
    )

    print(
        f"{sheet2_name}: "
        f"{start2} → {end2}"
    )

    print(
        f"Overlap: "
        f"{overlap_start} → {overlap_end}"
    )

    # ---------------------------------------------------------
    # Sample common invoices
    # ---------------------------------------------------------

    print("\n[7] SAMPLE COMMON INVOICES")

    sample_common = sorted(
        common_invoices
    )[:20]

    print(sample_common)


if __name__ == "__main__":
    main()