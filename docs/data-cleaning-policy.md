# Data Cleaning Policy

## 1. Purpose

This document defines the data-quality and cleaning rules for the Online Retail II project.

The policy separates:

1. **Canonical data preservation** — retain the original business information as faithfully as possible.
2. **Analytical data preparation** — construct a reliable subset for customer-level analytics, RFM, clustering, and anomaly analysis.

No cleaning rule should silently destroy information from the canonical dataset.

---

## 2. Core Principles

* Do not modify the original Excel workbook.
* Do not overwrite the canonical SQLite database during cleaning.
* Do not delete suspicious records without an explicit rule and evidence.
* Preserve problematic records for auditability.
* Apply different filters according to the analytical objective.
* Every exclusion must be reproducible and documented.

---

## 3. Cross-Sheet Replication

### Finding

The two workbook sheets overlap in December 2010. The overlap was investigated and verified as replicated transaction records.

### Policy

When constructing the canonical dataset:

* Preserve Sheet 1.
* Remove the replicated Sheet 2 rows identified by the validated common-invoice overlap.
* Maintain the canonical row-count assertion.

The canonical dataset therefore contains the de-duplicated cross-sheet representation of the workbook.

This operation is performed during canonicalization, not during later analytical cleaning.

---

## 4. Exact Internal Duplicates

### Finding

The canonical database still contains exact duplicate transaction combinations.

### Policy

Do not blindly delete exact duplicates from the canonical database.

They must remain available for data-quality investigation.

For customer-level analytical datasets, identical duplicate transaction records must not be allowed to silently inflate metrics. Any deduplication used for RFM or clustering must be deterministic and explicitly documented.

---

## 5. Missing Customer ID

### Finding

Some transaction rows have no Customer ID.

### Policy

* Preserve missing Customer IDs in the canonical transaction table.
* Do not impute Customer IDs.
* Do not assign transactions to customers based on inference.

For customer-level analytics:

```text
Customer ID IS NOT NULL
```

is required.

Rows without Customer ID may still be retained for transaction-level descriptive analysis.

---

## 6. Cancellation Transactions

### Definition

A cancellation is represented by the dedicated `is_cancellation` flag.

### Policy

* Preserve cancellation transactions in the canonical database.
* Do not redefine cancellation solely from `Quantity < 0`.
* Exclude cancellation transactions from the normal purchase dataset used for RFM.

Analytical purchase rule:

```text
is_cancellation = 0
```

---

## 7. Negative Quantity

### Finding

Negative quantities occur both in cancellation records and in non-cancellation operational records.

Examples of non-cancellation descriptions include:

* `short`
* `damages`
* `lost`
* `wet`
* `sold as gold`
* inventory correction / operational notes

### Policy

Do not treat all negative quantities as cancellations.

For the canonical dataset:

* Preserve all negative-quantity records.
* Preserve their descriptions and operational context.

For normal customer-purchase analytics:

```text
Quantity > 0
```

is required.

Negative-quantity non-cancellation records remain available for data-quality and anomaly analysis.

---

## 8. Non-Positive Unit Price

### Finding

The dataset contains both zero-price and negative-price rows.

### Policy

* Preserve all non-positive-price records in the canonical database.
* Do not replace zero or negative prices with arbitrary values.
* Do not impute price without supporting evidence.

For revenue and Monetary calculations:

```text
Unit Price > 0
```

is required.

Rows with `Unit Price <= 0` must remain available for audit and anomaly investigation.

---

## 9. Missing Description

### Policy

Missing descriptions should not be filled blindly.

A missing description may be recovered only when the corresponding StockCode has exactly one consistent non-null description in the canonical dataset.

Therefore:

```text
IF missing description
AND StockCode has exactly one non-null description
→ recover using that description
```

Otherwise:

```text
→ keep Description as NULL
```

The canonical transaction record must remain unchanged.

---

## 10. StockCode–Description Consistency

### Finding

A StockCode may correspond to multiple descriptions.

### Policy

`Description` must remain a transaction-level attribute.

Do not create a one-to-one `products(stock_code, description)` dependency.

The `products` table therefore uses:

```text
StockCode
```

as its stable product identifier, while transaction-level descriptions remain in `transactions`.

---

## 11. Customer–Country Consistency

### Finding

Some customers appear with multiple countries.

### Policy

Do not force a single country value onto a customer.

`Country` remains transaction-level data.

Customer-level country may only be derived later using an explicit aggregation rule, such as the most frequently observed country, if the analysis requires it.

No such derived country should overwrite the transaction-level value.

---

## 12. Analytical Purchase Dataset

The standard customer-purchase dataset for RFM should satisfy:

```text
Customer ID IS NOT NULL
AND is_cancellation = 0
AND Quantity > 0
AND Unit Price > 0
```

Rows failing these conditions remain in the canonical dataset and are excluded only from the corresponding customer-purchase analysis.

---

## 13. RFM Eligibility

A transaction may contribute to customer-level RFM only when:

* Customer ID is present.
* The transaction is not a cancellation.
* Quantity is positive.
* Unit Price is positive.
* InvoiceDate is valid.

Monetary contribution:

```text
LineAmount = Quantity × Unit Price
```

RFM calculations must therefore use only analytically valid purchase records.

---

## 14. Data Lineage

The project should maintain the following conceptual layers:

```text
Raw Excel
    │
    ▼
Canonical Dataset
    │
    ├── Data Quality Audit
    │
    ├── Investigation
    │
    ▼
Analytical Dataset
    │
    ├── RFM
    ├── EDA
    ├── Scaling
    ├── PCA
    ├── Clustering
    └── Anomaly Detection
```

The canonical dataset is the preservation layer.

The analytical dataset is the modeling layer.

---

## 15. Validation Requirements

After cleaning, the pipeline must report at minimum:

* Input row count
* Output row count
* Rows excluded by each rule
* Missing Customer ID count
* Cancellation count
* Negative quantity count
* Non-positive price count
* Missing description count
* Exact duplicate count
* Customer-country conflict count
* StockCode-description conflict count

The pipeline must fail loudly if an unexpected structural change occurs.

---

## 16. Non-Goals

This policy does not attempt to:

* infer missing customer identities;
* invent product descriptions;
* infer business meaning for every operational adjustment;
* claim that every anomaly represents fraud;
* permanently delete suspicious records from the canonical dataset.

---

## 17. Final Rule

**Preserve first, filter second, document always.**

The canonical database represents the observed source data after validated cross-sheet canonicalization.

Analytical datasets may apply stricter business rules, but every exclusion must be explicit, reproducible, and traceable to this policy.
