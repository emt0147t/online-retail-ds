PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;


-- =========================================================
-- CUSTOMERS
-- =========================================================

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY
);


-- =========================================================
-- PRODUCTS
-- =========================================================

CREATE TABLE products (
    stock_code TEXT PRIMARY KEY
);


-- =========================================================
-- TRANSACTIONS
-- =========================================================

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,

    invoice TEXT NOT NULL,

    stock_code TEXT NOT NULL,

    customer_id INTEGER,

    description TEXT,

    quantity INTEGER NOT NULL,

    invoice_date TIMESTAMP NOT NULL,

    unit_price REAL NOT NULL,

    country TEXT NOT NULL,

    is_cancellation INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (stock_code)
        REFERENCES products(stock_code),

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);


-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_transactions_invoice
    ON transactions(invoice);

CREATE INDEX idx_transactions_stock_code
    ON transactions(stock_code);

CREATE INDEX idx_transactions_customer_id
    ON transactions(customer_id);

CREATE INDEX idx_transactions_invoice_date
    ON transactions(invoice_date);