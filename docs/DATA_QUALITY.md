# Data Quality Issues & Solutions

## Overview

During inspection of the raw input data (`customers.csv` and `subscriptions.csv`), several data quality issues were discovered that would lead to incorrect metric calculations. This document catalogs these issues and the solutions implemented.

## Canonical Business Rules

These rules are the single source of truth for metric behavior and are enforced by implementation and tests.

1. **MRR month inclusion**
  - If a subscription is active at any point in a calendar month, full `monthly_price` is counted for that month.
  - No proration is applied.

2. **`end_date` inclusivity**
  - `end_date` is treated as inclusive when evaluating whether a subscription is active.

3. **Churn definition and boundary**
  - Churn occurs when a subscription has an `end_date` and no new subscription starts within 30 days.
  - Boundary behavior: `gap_days <= 30` is not churn; `gap_days > 30` is churn.

4. **3-month retention anchor**
  - “3 months after signup” is computed as calendar month offset (`signup_date + DateOffset(months=3)`), not fixed 90 days.

5. **Validation severity model**
  - Computation-critical and business-logic-critical fields fail fast on invalid values.
  - Integrity-monitoring fields (for example `country`) are warning-level and non-blocking.

## Customer Data Issues

### 1. Malformed Signup Dates
**Problem**: Invalid dates like '2024-13-05' (month 13 doesn't exist)
**Impact**: Cannot parse date, customer record is invalid
**Solution**: Remove customers with unparseable dates from silver layer
**Affected Records**: 1 customer (C019)
**Downstream Impact**: Also removes associated subscription(s)

### 2. Duplicate Customer IDs
**Problem**: Same customer_id appears multiple times with different data
**Impact**: Unclear which record is correct, inflates customer count
**Solution**: Keep first occurrence, remove duplicates
**Affected Records**: 1 customer (C038 - 2 entries)

### 3. Missing Country Data
**Problem**: Empty country field
**Impact**: Minor - doesn't prevent metric calculation
**Solution**: Log warning, keep record
**Affected Records**: 1 customer (C027)

## Subscription Data Issues

### 4. Whitespace in All Fields
**Problem**: Extra leading/trailing whitespace in all string fields  
**Impact**: Could cause matching failures, duplicate records  
**Solution**: Strip whitespace from all string columns during bronze→silver transformation

### 5. Typo in Plan Field
**Problem**: 'baisc' instead of 'basic'
**Impact**: Would create duplicate plan category, inflate plan count
**Solution**: Automated correction `'baisc' → 'basic'` in silver layer
**Affected Records**: 1 subscription

### 6. Text Value in Numeric Field
**Problem**: 'thirty' instead of '30' in monthly_price
**Impact**: Would fail numeric validation, exclude valid subscription from MRR calculation
**Solution**: Automated conversion `'thirty' → '30'` in silver layer
**Affected Records**: 1 subscription

### 7. Invalid Date Format
**Problem**: '2024-02-30' (February 30th doesn't exist)
**Impact**: Cannot parse end_date, unclear if subscription is active
**Solution**: Log warning, treat as unparseable (data issue at source)
**Affected Records**: 1 subscription

### 8. Subscriptions for Invalid Customers
**Problem**: Subscriptions exist for customers removed during cleaning (e.g., C019)
**Impact**: Orphaned subscriptions would cause metrics calculation errors
**Solution**: Coordinated cleaning - remove subscriptions for excluded customers
**Affected Records**: 1 subscription (for C019)

## Architectural Solution: Medallion Structure

We implemented a **medallion architecture** with three data layers:

### Bronze Layer (`data/bronze/`)
- **Purpose**: Raw data, exactly as received from source
- **Contents**: Original CSV files with all issues intact
- **Rationale**: Preserves source data for auditing and reprocessing

### Silver Layer (`data/silver/`)
- **Purpose**: Cleaned, validated, standardized data
- **Transformations Applied**:
  - Whitespace trimming
  - Typo corrections
  - Text-to-number conversions
  - Date validation
  - Data type enforcement
- **Quality Gates**: Critical issues (empty customer_id, malformed start_date) cause pipeline failure
- **Warnings**: Non-critical issues (malformed end_date) are logged but don't block processing

### Gold Layer (`data/gold/` or `output/`)
- **Purpose**: Aggregated metrics and analytics
- **Contents**: MRR, churn, retention reports
- **Rationale**: Business-ready outputs calculated from validated silver data

## Implementation

### Data Cleaning Modules

**Customer Cleaning**: `src/transformers/clean_customers.py`
- `CustomerDataCleaner`: Class implementing customer data cleaning
- `clean_customers_bronze_to_silver()`: Entry point function
- Returns set of removed customer IDs for downstream filtering
- Comprehensive validation with clear error messages

**Subscription Cleaning**: `src/transformers/clean_subscriptions.py`
- `SubscriptionDataCleaner`: Class implementing subscription cleaning logic
- `clean_subscriptions_bronze_to_silver()`: Entry point function
- Accepts `excluded_customer_ids` parameter for coordinated cleaning
- Filters out subscriptions for removed customers

### Testing

**Customer Tests**: `tests/test_clean_customers.py` (11 tests)
- Unit tests for duplicate handling, date validation, field cleaning
- Integration test for bronze→silver transformation

**Subscription Tests**: `tests/test_clean_subscriptions.py` (12 tests)
- Unit tests for each cleaning operation
- Integration test verifying bronze data has known issues
- Validates all edge cases (empty values, malformed dates, non-numeric prices)

**Loader Tests**: `tests/test_loader.py` (35 tests)
- Basic data loading and validation tests (11 original tests)
- Edge case tests for data robustness (13 edge case tests):
  - Negative prices, zero prices, extreme values
  - Future/ancient dates, long subscription durations
  - Empty fields, mixed invalid rows
  - All-invalid scenarios
- **Skip-preprocessing scenario tests (11 tests)** - NEW:
  - Text prices that preprocessing normally fixes
  - Typo'd plan names ('baisc')
  - Malformed customer dates ('2024-13-05')
  - Duplicate customers and subscriptions
  - Orphaned subscriptions (customer removed, subscription remains)
  - Combined dirty data scenarios
- Validates that loader handles gracefully when preprocessing is skipped

**Metrics Tests**: `tests/test_metrics.py` (10 tests)

**Total**: 68 passing tests

### Rule-to-Test Mapping

- **MRR month inclusion / activity-window semantics**
  - `tests/test_metrics.py`
- **Churn 30-day boundary (including exactly 30 days)**
  - `tests/test_metrics.py`
- **3-month retention calendar-offset behavior**
  - `tests/test_metrics.py`
- **Validation severity and dirty-data handling**
  - `tests/test_loader.py`
- **Customer cleaning rules (duplicates, malformed signup dates)**
  - `tests/test_clean_customers.py`
- **Subscription cleaning rules (typos, text prices, date parsing, excluded customers)**
  - `tests/test_clean_subscriptions.py`

### Pipeline Integration
`main.py`

- Runs bronze→silver preprocessing by default
- `--skip-preprocessing` flag for re-running metrics without re-cleaning
- **Coordinated Cleaning**: Customers cleaned first, removed IDs passed to subscription cleaner
- **Enhanced Warnings**: Prominent alerts when data quality issues affect metrics
- Three-step process:
  1. Customer Data Cleaning (Bronze → Silver)
  2. Subscription Data Cleaning (Bronze → Silver, filtering excluded customers)
  3. Metrics Calculation (Silver → Gold)
  2. Metrics Calculation (Silver → Gold)

## Usage

### Run full pipeline (with preprocessing):
```bash
python main.py
```

### Skip preprocessing (use existing silver data):
```bash
python main.py --skip-preprocessing
```

### Run cleaning separately:
```bash
python -m src.transformers.clean_subscriptions
```

## Validation Results

After implementing the cleaning pipeline:
- ✅ All 68 tests passing
- ✅ **Customers**: 40 bronze → 38 silver (2 removed: C019 malformed date + 1 C038 duplicate row)
- ✅ **Subscriptions**: 54 bronze → 53 silver (1 removed for excluded customer C019)
- ✅ 1 customer duplicate handled (C038: kept first occurrence)
- ✅ 1 malformed date removed (C019: '2024-13-05')
- ✅ 1 typo corrected ('baisc' → 'basic')
- ✅ 1 text-to-number conversion ('thirty' → '30')
- ✅ Coordinated cleaning: subscriptions filtered for removed customers
- ✅ Robust loader with 24 edge case + skip-preprocessing tests
  - Gracefully handles dirty data scenarios without preprocessing
  - Degrades metrics appropriately with clear warnings
- ⚠️ 1 malformed end_date logged (data source issue)
- ⚠️ 7 remaining warnings (overlaps, missing data, etc.)

### Metrics Impact
- **MRR**: Increased by $30/month (Aug-Dec 2024) due to 'thirty' fix
- **Subscriptions**: Net +1 valid subscription (recovered 'thirty', removed C019)
- **Data Quality**: Warnings reduced from 11 → 7 (36% improvement)

## Recommendations for Production

1. **Source Data Validation**: Implement checks at data ingestion point to catch issues earlier
2. **Automated Monitoring**: Alert when cleaning rules trigger (indicates upstream data quality degradation)
3. **Reject vs. Correct**: Current implementation auto-corrects known issues; consider making this configurable
4. **Date Validation**: '2024-02-30' should be rejected at source, not silently handled downstream

## References

- Inspection Notebook: [notebooks/01_subscription_data_inspection.ipynb](../notebooks/01_subscription_data_inspection.ipynb)
- Cleaning Code: [src/transformers/clean_subscriptions.py](../src/transformers/clean_subscriptions.py)
- Tests: [tests/test_clean_subscriptions.py](../tests/test_clean_subscriptions.py)
