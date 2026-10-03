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


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

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
            .fillna("<NA>")
        )

    df["Quantity"] = (
        pd.to_numeric(
            df["Quantity"],
            errors="coerce",
        )
        .astype("string")
        .fillna("<NA>")
    )

    df["Price"] = (
        pd.to_numeric(
            df["Price"],
            errors="coerce",
        )
        .round(10)
        .astype("string")
        .fillna("<NA>")
    )

    df["Customer ID"] = (
        pd.to_numeric(
            df["Customer ID"],
            errors="coerce",
        )
        .astype("string")
        .fillna("<NA>")
    )

    df["InvoiceDate"] = (
        pd.to_datetime(
            df["InvoiceDate"],
            errors="coerce",
        )
        .astype("string")
        .fillna("<NA>")
    )

    return df[COMPARE_COLUMNS]


def main() -> None:
    excel = pd.ExcelFile(RAW_FILE)

    sheet1 = normalize(
        pd.read_excel(
            RAW_FILE,
            sheet_name=excel.sheet_names[0],
        )
    )

    sheet2 = normalize(
        pd.read_excel(
            RAW_FILE,
            sheet_name=excel.sheet_names[1],
        )
    )

    # Count each exact transaction combination.
    counts1 = (
        sheet1
        .value_counts(
            subset=COMPARE_COLUMNS,
            dropna=False,
        )
        .rename("count_sheet1")
        .reset_index()
    )

    counts2 = (
        sheet2
        .value_counts(
            subset=COMPARE_COLUMNS,
            dropna=False,
        )
        .rename("count_sheet2")
        .reset_index()
    )

    comparison = counts1.merge(
        counts2,
        on=COMPARE_COLUMNS,
        how="outer",
    )

    comparison["count_sheet1"] = (
        comparison["count_sheet1"]
        .fillna(0)
        .astype(int)
    )

    comparison["count_sheet2"] = (
        comparison["count_sheet2"]
        .fillna(0)
        .astype(int)
    )

    comparison["count_difference"] = (
        comparison["count_sheet1"]
        - comparison["count_sheet2"]
    )

    # Only transactions belonging to common invoices
    common_invoices = set(
        sheet1["Invoice"]
        .unique()
    ).intersection(
        set(sheet2["Invoice"].unique())
    )

    common_comparison = comparison[
        comparison["Invoice"].isin(common_invoices)
    ].copy()

    different = common_comparison[
        common_comparison["count_difference"] != 0
    ].copy()

    print("=" * 90)
    print("CROSS-SHEET MULTIPLICITY VERIFICATION")
    print("=" * 90)

    print(
        f"\nCommon invoice numbers: "
        f"{len(common_invoices):,}"
    )

    print(
        f"Unique exact transaction combinations "
        f"across common invoices: "
        f"{len(common_comparison):,}"
    )

    print(
        f"Transactions with different multiplicity: "
        f"{len(different):,}"
    )

    if len(different) == 0:
        print(
            "\nRESULT: PASS"
        )
        print(
            "Every exact transaction combination appears "
            "the same number of times in both sheets."
        )
    else:
        print(
            "\nRESULT: DIFFERENCES FOUND"
        )

        print("\nTop multiplicity differences:")

        print(
            different
            .sort_values(
                "count_difference",
                key=lambda s: s.abs(),
                ascending=False,
            )
            .head(30)
            .to_string(index=False)
        )

    output = Path(
        "data/processed/cross_sheet_multiplicity.csv"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    common_comparison.to_csv(
        output,
        index=False,
    )

    print(
        f"\nSaved comparison to: {output}"
    )


if __name__ == "__main__":
    main()