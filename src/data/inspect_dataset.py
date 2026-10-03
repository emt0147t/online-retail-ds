from pathlib import Path

import pandas as pd


RAW_FILE = Path("data/raw/online_retail_II.xlsx")


def inspect_sheet(file_path: Path, sheet_name: str) -> pd.DataFrame:
    print("\n" + "=" * 90)
    print(f"SHEET: {sheet_name}")
    print("=" * 90)

    df = pd.read_excel(file_path, sheet_name=sheet_name)

    print(f"\nShape: {df.shape}")

    print("\nColumns:")
    print(list(df.columns))

    print("\nDtypes:")
    print(df.dtypes)

    # ---------------------------------------------------------
    # Missing values
    # ---------------------------------------------------------
    print("\n[1] MISSING VALUES")

    missing = df.isna().sum()
    missing_percent = (missing / len(df) * 100).round(2)

    print(
        pd.DataFrame(
            {
                "missing_count": missing,
                "missing_percent": missing_percent,
            }
        )
    )

    # ---------------------------------------------------------
    # Duplicates
    # ---------------------------------------------------------
    print("\n[2] DUPLICATES")

    duplicate_count = df.duplicated().sum()
    print(f"Exact duplicate rows: {duplicate_count}")

    # ---------------------------------------------------------
    # Quantity
    # ---------------------------------------------------------
    print("\n[3] QUANTITY")

    print(f"Quantity < 0: {(df['Quantity'] < 0).sum()}")
    print(f"Quantity == 0: {(df['Quantity'] == 0).sum()}")
    print(f"Quantity > 0: {(df['Quantity'] > 0).sum()}")

    # ---------------------------------------------------------
    # Price
    # ---------------------------------------------------------
    print("\n[4] PRICE")

    print(f"Price < 0: {(df['Price'] < 0).sum()}")
    print(f"Price == 0: {(df['Price'] == 0).sum()}")
    print(f"Price > 0: {(df['Price'] > 0).sum()}")

    # ---------------------------------------------------------
    # Invoice
    # ---------------------------------------------------------
    print("\n[5] INVOICE")

    invoice_str = df["Invoice"].astype("string").str.strip()

    starts_with_c = invoice_str.str.upper().str.startswith("C")

    print(f"Invoice starting with C: {starts_with_c.sum()}")

    print("\nInvoice prefix distribution:")

    prefix = invoice_str.str[0].str.upper()

    print(prefix.value_counts(dropna=False).head(20))

    # ---------------------------------------------------------
    # Relation: cancellation vs quantity
    # ---------------------------------------------------------
    print("\n[6] CANCELLATION × QUANTITY")

    cancellation_table = pd.crosstab(
        starts_with_c,
        df["Quantity"] < 0,
        rownames=["Invoice starts with C"],
        colnames=["Quantity < 0"],
    )

    print(cancellation_table)

    # ---------------------------------------------------------
    # StockCode
    # ---------------------------------------------------------
    print("\n[7] STOCK CODE")

    stock = df["StockCode"].astype("string").str.strip()

    print(f"Unique StockCode: {stock.nunique(dropna=True)}")

    print("\nTop StockCodes:")
    print(stock.value_counts(dropna=False).head(20))

    # ---------------------------------------------------------
    # Customer
    # ---------------------------------------------------------
    print("\n[8] CUSTOMER")

    print(f"Unique Customer ID: {df['Customer ID'].nunique(dropna=True)}")

    # ---------------------------------------------------------
    # Date
    # ---------------------------------------------------------
    print("\n[9] DATE RANGE")

    print(f"Min date: {df['InvoiceDate'].min()}")
    print(f"Max date: {df['InvoiceDate'].max()}")

    return df


def main() -> None:
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {RAW_FILE}"
        )

    excel = pd.ExcelFile(RAW_FILE)

    print("Available sheets:")
    print(excel.sheet_names)

    data = {}

    for sheet_name in excel.sheet_names:
        data[sheet_name] = inspect_sheet(
            RAW_FILE,
            sheet_name
        )

    # ---------------------------------------------------------
    # Cross-sheet analysis
    # ---------------------------------------------------------
    print("\n" + "=" * 90)
    print("CROSS-SHEET ANALYSIS")
    print("=" * 90)

    df1 = data[excel.sheet_names[0]]
    df2 = data[excel.sheet_names[1]]

    # Date overlap
    start1 = df1["InvoiceDate"].min()
    end1 = df1["InvoiceDate"].max()

    start2 = df2["InvoiceDate"].min()
    end2 = df2["InvoiceDate"].max()

    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)

    print("\n[1] DATE OVERLAP")

    print(f"Sheet 1: {start1} → {end1}")
    print(f"Sheet 2: {start2} → {end2}")
    print(f"Overlap:  {overlap_start} → {overlap_end}")

    # Exact duplicate rows across sheets
    print("\n[2] EXACT DUPLICATES ACROSS SHEETS")

    combined = pd.concat(
        [
            df1.assign(_source_sheet=excel.sheet_names[0]),
            df2.assign(_source_sheet=excel.sheet_names[1]),
        ],
        ignore_index=True,
    )

    compare_cols = [
        "Invoice",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "Price",
        "Customer ID",
        "Country",
    ]

    cross_sheet_duplicates = combined.duplicated(
        subset=compare_cols,
        keep=False,
    )

    print(
        "Rows participating in cross-sheet exact duplicates:",
        cross_sheet_duplicates.sum(),
    )

    duplicate_groups = (
        combined.loc[cross_sheet_duplicates, compare_cols]
        .value_counts()
        .head(20)
    )

    print("\nTop cross-sheet duplicate groups:")
    print(duplicate_groups)

    # Invoice overlap
    print("\n[3] INVOICE OVERLAP")

    invoices1 = set(
        df1["Invoice"]
        .astype("string")
        .dropna()
        .unique()
    )

    invoices2 = set(
        df2["Invoice"]
        .astype("string")
        .dropna()
        .unique()
    )

    common_invoices = invoices1.intersection(invoices2)

    print(f"Unique invoices in Sheet 1: {len(invoices1)}")
    print(f"Unique invoices in Sheet 2: {len(invoices2)}")
    print(f"Common invoice numbers: {len(common_invoices)}")

    if common_invoices:
        print("\nSample common invoices:")
        print(sorted(common_invoices)[:20])


if __name__ == "__main__":
    main()