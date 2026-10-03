from pathlib import Path

import pandas as pd


RAW_FILE = Path("data/raw/online_retail_II.xlsx")


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["StockCode"] = (
        df["StockCode"]
        .astype("string")
        .str.strip()
    )

    df["Description"] = (
        df["Description"]
        .astype("string")
        .str.strip()
    )

    df["Customer ID"] = pd.to_numeric(
        df["Customer ID"],
        errors="coerce",
    ).astype("Int64")

    df["Country"] = (
        df["Country"]
        .astype("string")
        .str.strip()
    )

    return df


def main() -> None:
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {RAW_FILE}"
        )

    excel = pd.ExcelFile(RAW_FILE)

    frames = []

    for sheet_name in excel.sheet_names:
        print(f"Reading: {sheet_name}")

        df = pd.read_excel(
            RAW_FILE,
            sheet_name=sheet_name,
        )

        df = normalize(df)

        frames.append(df)

    df = pd.concat(
        frames,
        ignore_index=True,
    )

    # =========================================================
    # StockCode -> Description
    # =========================================================

    print("\n" + "=" * 80)
    print("STOCKCODE -> DESCRIPTION CONSISTENCY")
    print("=" * 80)

    stock_description_counts = (
        df.groupby("StockCode")["Description"]
        .nunique(dropna=True)
    )

    conflicting_stock_codes = (
        stock_description_counts[
            stock_description_counts > 1
        ]
    )

    print(
        f"StockCodes with multiple descriptions: "
        f"{len(conflicting_stock_codes):,}"
    )

    if len(conflicting_stock_codes) > 0:
        print("\nExamples:")

        examples = (
            df[
                df["StockCode"].isin(
                    conflicting_stock_codes.index
                )
            ][
                ["StockCode", "Description"]
            ]
            .drop_duplicates()
            .sort_values("StockCode")
            .head(30)
        )

        print(examples.to_string(index=False))

    # =========================================================
    # Customer ID -> Country
    # =========================================================

    print("\n" + "=" * 80)
    print("CUSTOMER ID -> COUNTRY CONSISTENCY")
    print("=" * 80)

    customer_country_counts = (
        df.dropna(subset=["Customer ID"])
        .groupby("Customer ID")["Country"]
        .nunique()
    )

    conflicting_customers = (
        customer_country_counts[
            customer_country_counts > 1
        ]
    )

    print(
        f"Customers with multiple countries: "
        f"{len(conflicting_customers):,}"
    )

    if len(conflicting_customers) > 0:
        print("\nExamples:")

        examples = (
            df[
                df["Customer ID"].isin(
                    conflicting_customers.index
                )
            ][
                ["Customer ID", "Country"]
            ]
            .drop_duplicates()
            .sort_values("Customer ID")
            .head(30)
        )

        print(examples.to_string(index=False))

    # =========================================================
    # Summary
    # =========================================================

    print("\n" + "=" * 80)
    print("ENTITY AUDIT SUMMARY")
    print("=" * 80)

    if (
        len(conflicting_stock_codes) == 0
        and len(conflicting_customers) == 0
    ):
        print("PASS")
        print(
            "StockCode -> Description is consistent."
        )
        print(
            "CustomerID -> Country is consistent."
        )
    else:
        print("REVIEW REQUIRED")


if __name__ == "__main__":
    main()