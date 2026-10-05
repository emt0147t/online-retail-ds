from pathlib import Path
import sqlite3


DB_FILE = Path("data/retail.db")


def scalar(
    connection: sqlite3.Connection,
    query: str,
) -> int | float | str | None:
    result = connection.execute(query).fetchone()
    return result[0] if result else None


def print_section(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def main() -> None:

    if not DB_FILE.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_FILE}"
        )

    connection = sqlite3.connect(DB_FILE)

    try:
        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        print_section(
            "MILESTONE 2 - DATA QUALITY AUDIT"
        )

        # =====================================================
        # 1. Basic dataset statistics
        # =====================================================

        print_section("1. BASIC COUNTS")

        transaction_count = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions;
            """,
        )

        customer_count = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM customers;
            """,
        )

        product_count = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM products;
            """,
        )

        print(
            f"Transactions: {transaction_count:,}"
        )

        print(
            f"Customers: {customer_count:,}"
        )

        print(
            f"Products: {product_count:,}"
        )

        # =====================================================
        # 2. Missing values
        # =====================================================

        print_section("2. MISSING VALUES")

        missing_customer = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE customer_id IS NULL;
            """,
        )

        missing_description = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE description IS NULL
               OR TRIM(description) = '';
            """,
        )

        missing_stock_code = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE stock_code IS NULL
               OR TRIM(stock_code) = '';
            """,
        )

        missing_invoice = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE invoice IS NULL
               OR TRIM(invoice) = '';
            """,
        )

        missing_date = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE invoice_date IS NULL;
            """,
        )

        print(
            f"Missing Customer ID: {missing_customer:,}"
        )

        print(
            f"Missing Description: {missing_description:,}"
        )

        print(
            f"Missing StockCode: {missing_stock_code:,}"
        )

        print(
            f"Missing Invoice: {missing_invoice:,}"
        )

        print(
            f"Missing InvoiceDate: {missing_date:,}"
        )

        # =====================================================
        # 3. Quantity
        # =====================================================

        print_section("3. QUANTITY")

        quantity_negative = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE quantity < 0;
            """,
        )

        quantity_zero = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE quantity = 0;
            """,
        )

        quantity_positive = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE quantity > 0;
            """,
        )

        print(
            f"Quantity < 0: {quantity_negative:,}"
        )

        print(
            f"Quantity = 0: {quantity_zero:,}"
        )

        print(
            f"Quantity > 0: {quantity_positive:,}"
        )

        # =====================================================
        # 4. Price
        # =====================================================

        print_section("4. PRICE")

        price_negative = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE unit_price < 0;
            """,
        )

        price_zero = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE unit_price = 0;
            """,
        )

        price_positive = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE unit_price > 0;
            """,
        )

        print(
            f"Price < 0: {price_negative:,}"
        )

        print(
            f"Price = 0: {price_zero:,}"
        )

        print(
            f"Price > 0: {price_positive:,}"
        )

        # =====================================================
        # 5. Cancellation
        # =====================================================

        print_section("5. CANCELLATION")

        cancellation_count = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE is_cancellation = 1;
            """,
        )

        negative_quantity_cancellation = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE is_cancellation = 1
              AND quantity < 0;
            """,
        )

        negative_quantity_non_cancellation = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE is_cancellation = 0
              AND quantity < 0;
            """,
        )

        print(
            f"Cancellation transactions: "
            f"{cancellation_count:,}"
        )

        print(
            f"Cancellation + Quantity < 0: "
            f"{negative_quantity_cancellation:,}"
        )

        print(
            f"Non-cancellation + Quantity < 0: "
            f"{negative_quantity_non_cancellation:,}"
        )

        # =====================================================
        # 6. Price <= 0 details
        # =====================================================

        print_section(
            "6. NON-POSITIVE PRICE DETAILS"
        )

        rows = connection.execute(
            """
            SELECT
                stock_code,
                description,
                invoice,
                quantity,
                unit_price,
                is_cancellation,
                COUNT(*) AS rows
            FROM transactions
            WHERE unit_price <= 0
            GROUP BY
                stock_code,
                description,
                invoice,
                quantity,
                unit_price,
                is_cancellation
            ORDER BY rows DESC
            LIMIT 30;
            """
        ).fetchall()

        for row in rows:
            print(row)

        # =====================================================
        # 7. Missing description by StockCode
        # =====================================================

        print_section(
            "7. MISSING DESCRIPTION BY STOCKCODE"
        )

        rows = connection.execute(
            """
            SELECT
                stock_code,
                COUNT(*) AS rows
            FROM transactions
            WHERE description IS NULL
               OR TRIM(description) = ''
            GROUP BY stock_code
            ORDER BY rows DESC
            LIMIT 30;
            """
        ).fetchall()

        for row in rows:
            print(row)

        # =====================================================
        # 8. Negative quantity not marked cancellation
        # =====================================================

        print_section(
            "8. NEGATIVE QUANTITY WITHOUT CANCELLATION"
        )

        rows = connection.execute(
            """
            SELECT
                invoice,
                stock_code,
                description,
                quantity,
                unit_price,
                customer_id,
                country,
                COUNT(*) AS rows
            FROM transactions
            WHERE quantity < 0
              AND is_cancellation = 0
            GROUP BY
                invoice,
                stock_code,
                description,
                quantity,
                unit_price,
                customer_id,
                country
            ORDER BY rows DESC
            LIMIT 30;
            """
        ).fetchall()

        for row in rows:
            print(row)

        # =====================================================
        # 9. Exact duplicate groups
        # =====================================================

        print_section(
            "9. INTERNAL EXACT DUPLICATES"
        )

        duplicate_groups = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    invoice,
                    stock_code,
                    description,
                    quantity,
                    invoice_date,
                    unit_price,
                    customer_id,
                    country
                FROM transactions
                GROUP BY
                    invoice,
                    stock_code,
                    description,
                    quantity,
                    invoice_date,
                    unit_price,
                    customer_id,
                    country
                HAVING COUNT(*) > 1
            );
            """,
        )

        duplicate_extra_rows = scalar(
            connection,
            """
            SELECT COALESCE(
                SUM(occurrences - 1),
                0
            )
            FROM (
                SELECT COUNT(*) AS occurrences
                FROM transactions
                GROUP BY
                    invoice,
                    stock_code,
                    description,
                    quantity,
                    invoice_date,
                    unit_price,
                    customer_id,
                    country
                HAVING COUNT(*) > 1
            );
            """,
        )

        duplicate_total_rows = scalar(
            connection,
            """
            SELECT COALESCE(
                SUM(occurrences),
                0
            )
            FROM (
                SELECT COUNT(*) AS occurrences
                FROM transactions
                GROUP BY
                    invoice,
                    stock_code,
                    description,
                    quantity,
                    invoice_date,
                    unit_price,
                    customer_id,
                    country
                HAVING COUNT(*) > 1
            );
            """,
        )

        print(
            f"Duplicate groups: "
            f"{duplicate_groups:,}"
        )

        print(
            f"Rows beyond first occurrence: "
            f"{duplicate_extra_rows:,}"
        )

        print(
            f"Rows participating in duplicate groups: "
            f"{duplicate_total_rows:,}"
        )

        # =====================================================
        # 10. Top duplicate groups
        # =====================================================

        print_section(
            "10. TOP INTERNAL DUPLICATE GROUPS"
        )

        rows = connection.execute(
            """
            SELECT
                invoice,
                stock_code,
                description,
                quantity,
                invoice_date,
                unit_price,
                customer_id,
                country,
                COUNT(*) AS occurrences
            FROM transactions
            GROUP BY
                invoice,
                stock_code,
                description,
                quantity,
                invoice_date,
                unit_price,
                customer_id,
                country
            HAVING COUNT(*) > 1
            ORDER BY occurrences DESC
            LIMIT 30;
            """
        ).fetchall()

        for row in rows:
            print(row)

        # =====================================================
        # 11. Revenue impact
        # =====================================================

        print_section(
            "11. LINE AMOUNT IMPACT"
        )

        result = connection.execute(
            """
            SELECT
                COUNT(*) AS rows,
                COALESCE(
                    SUM(quantity * unit_price),
                    0
                ) AS line_amount
            FROM transactions
            WHERE unit_price <= 0;
            """
        ).fetchone()

        print(
            f"Rows with Price <= 0: {result[0]:,}"
        )

        print(
            f"Total line amount from Price <= 0: "
            f"{result[1]:,.2f}"
        )

        # =====================================================
        # 12. Country/customer consistency
        # =====================================================

        print_section(
            "12. CUSTOMER-COUNTRY CONSISTENCY"
        )

        conflicting_customers = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM (
                SELECT customer_id
                FROM transactions
                WHERE customer_id IS NOT NULL
                GROUP BY customer_id
                HAVING COUNT(DISTINCT country) > 1
            );
            """,
        )

        print(
            f"Customers with multiple countries: "
            f"{conflicting_customers:,}"
        )

        # =====================================================
        # 13. StockCode-description consistency
        # =====================================================

        print_section(
            "13. STOCKCODE-DESCRIPTION CONSISTENCY"
        )

        conflicting_stockcodes = scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM (
                SELECT stock_code
                FROM transactions
                WHERE description IS NOT NULL
                GROUP BY stock_code
                HAVING COUNT(DISTINCT description) > 1
            );
            """,
        )

        print(
            f"StockCodes with multiple non-null "
            f"descriptions: "
            f"{conflicting_stockcodes:,}"
        )

        # =====================================================
        # 14. Final audit status
        # =====================================================

        print_section(
            "14. AUDIT COMPLETE"
        )

        print(
            "No data was modified by this script."
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()