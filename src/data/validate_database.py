from pathlib import Path
import sqlite3


DB_FILE = Path("data/retail.db")


def main() -> None:

    if not DB_FILE.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_FILE}"
        )

    connection = sqlite3.connect(
        DB_FILE
    )

    try:

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        print("=" * 80)
        print("DATABASE VALIDATION")
        print("=" * 80)

        # =====================================================
        # Tables
        # =====================================================

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name;
            """
        ).fetchall()

        print("\n[TABLES]")

        for table in tables:
            print(f" - {table[0]}")

        # =====================================================
        # Row counts
        # =====================================================

        print("\n[ROW COUNTS]")

        expected_counts = {
            "transactions": 1_044_848,
        }

        for table_name in [
            "customers",
            "products",
            "transactions",
        ]:

            count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM {table_name};
                """
            ).fetchone()[0]

            print(
                f"{table_name}: "
                f"{count:,}"
            )

            if (
                table_name in expected_counts
                and count != expected_counts[table_name]
            ):
                raise AssertionError(
                    f"{table_name} row count mismatch: "
                    f"expected "
                    f"{expected_counts[table_name]:,}, "
                    f"got {count:,}"
                )

        # =====================================================
        # Foreign keys
        # =====================================================

        print("\n[FOREIGN KEY CHECK]")

        violations = connection.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

        print(
            f"Violations: "
            f"{len(violations)}"
        )

        if violations:
            for violation in violations[:20]:
                print(violation)

            raise AssertionError(
                "Foreign-key violations detected."
            )

        # =====================================================
        # NULL customer IDs
        # =====================================================

        print("\n[CUSTOMER ID CHECK]")

        missing_customer = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE customer_id IS NULL;
            """
        ).fetchone()[0]

        print(
            f"Transactions without Customer ID: "
            f"{missing_customer:,}"
        )

        # =====================================================
        # Cancellation check
        # =====================================================

        print("\n[CANCELLATION CHECK]")

        cancellation_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE is_cancellation = 1;
            """
        ).fetchone()[0]

        print(
            f"Cancellation transactions: "
            f"{cancellation_count:,}"
        )

        inconsistent_cancellations = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE is_cancellation = 1
              AND invoice NOT LIKE 'C%';
            """
        ).fetchone()[0]

        print(
            "Cancellation flag inconsistencies: "
            f"{inconsistent_cancellations:,}"
        )

        if inconsistent_cancellations != 0:
            raise AssertionError(
                "Cancellation flag is inconsistent."
            )

        # =====================================================
        # JOIN validation
        # =====================================================

        print("\n[JOIN CHECK]")

        join_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions AS t
            INNER JOIN products AS p
                ON t.stock_code = p.stock_code
            """
        ).fetchone()[0]

        print(
            f"Transactions successfully joined "
            f"to products: "
            f"{join_count:,}"
        )

        if join_count == 0:
            raise AssertionError(
                "Product JOIN returned zero rows."
            )

        # =====================================================
        # Sample
        # =====================================================

        print("\n[JOIN SAMPLE]")

        rows = connection.execute(
            """
            SELECT
                t.transaction_id,
                t.invoice,
                t.stock_code,
                p.stock_code,
                t.customer_id,
                c.customer_id,
                t.description,
                t.quantity,
                t.unit_price,
                t.country
            FROM transactions AS t
            JOIN products AS p
                ON t.stock_code = p.stock_code
            LEFT JOIN customers AS c
                ON t.customer_id = c.customer_id
            LIMIT 10;
            """
        ).fetchall()

        for row in rows:
            print(row)

        # =====================================================
        # Duplicate check
        # =====================================================

        print("\n[INTERNAL EXACT DUPLICATE CHECK]")

        duplicate_groups = connection.execute(
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
            LIMIT 10;
            """
        ).fetchall()

        print(
            f"Duplicate groups found: "
            f"{len(duplicate_groups)}"
        )

        for row in duplicate_groups:
            print(row)

        print("\n" + "=" * 80)
        print("DATABASE VALIDATION PASSED")
        print("=" * 80)

    finally:
        connection.close()


if __name__ == "__main__":
    main()