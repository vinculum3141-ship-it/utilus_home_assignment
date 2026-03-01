# Data Quality Issues & Solutions

## Overview

During inspection of the raw input data (`customers.csv` and `subscriptions.csv`), several data quality issues were discovered that would lead to incorrect metric calculations. This document catalogs these issues and the solutions implemented.

## Data Quality Findings Summary

### Validated Positive Findings
✅ **No negative monthly_price values** - All prices in bronze data are >= 0  
✅ **Customer IDs are non-empty** - All records have customer_id populated  
✅ **Subscription IDs are non-empty** - All records have subscription_id populated

### Issues Detected & Remediated

#### Critical Issues (Block Processing)
❌ **Invalid date ranges found** - Some subscriptions have `end_date < start_date`  
   - **Impact**: Violates temporal logic, would create negative subscription durations  
   - **Solution**: Fail validation, require data correction at source  
   - **Implementation**: `_validate_date_ranges()` in clean_subscriptions.py

❌ **Subscriptions start before customer signup** - Some subscriptions have `start_date < signup_date`  
   - **Impact**: Logical impossibility (cannot subscribe before account exists)  
   - **Solution**: Fail validation, require data correction at source  
   - **Implementation**: `_validate_start_after_signup()` in clean_subscriptions.py

❌ **Malformed dates** - Invalid values like '2024-13-05' (month 13), '2024-02-30' (Feb 30)  
   - **Impact**: Unparseable dates prevent metric calculation  
   - **Solution**: Remove records with unparseable dates from silver layer  
   - **Count**: 1 customer (C019), 1 subscription end_date

❌ **Subscriptions for non-existent customers** - Orphaned subscriptions remain after customer cleaning  
   - **Impact**: Referential integrity violation, metrics calculation errors  
   - **Solution**: Coordinated cleaning - filter subscriptions for removed customers  
   - **Implementation**: `_filter_unknown_customers()` in clean_subscriptions.py

#### Data Quality Issues (Auto-Corrected)
⚠️ **Typos in plan names** - 'baisc' instead of 'basic'  
   - **Impact**: Would create duplicate plan category  
   - **Solution**: Automated correction in silver layer  
   - **Count**: 1 subscription

⚠️ **Text values in numeric fields** - 'thirty' instead of '30' in monthly_price  
   - **Impact**: Would fail numeric validation, exclude valid subscription  
   - **Solution**: Automated conversion in silver layer  
   - **Count**: 1 subscription  
   - **MRR Impact**: +$30/month (Aug-Dec 2024)

⚠️ **Duplicate records** - Same customer_id with different data  
   - **Impact**: Inflates customer count, unclear which record is correct  
   - **Solution**: Keep first occurrence, remove duplicates  
   - **Count**: 1 customer (C038 appears twice)

⚠️ **Whitespace padding** - Leading/trailing spaces in string fields  
   - **Impact**: Could cause matching failures  
   - **Solution**: Strip whitespace from all string columns  
   - **Prevalence**: Multiple records across all string fields

⚠️ **Country name variations** - Mixed case inconsistency  
   - **Impact**: Minor - doesn't prevent calculation but affects grouping consistency  
   - **Solution**: Normalize to uppercase in silver layer  
   - **Implementation**: `_clean_country()` in clean_customers.py

#### Integrity Findings (Monitored)
⚠️ **Overlapping subscriptions detected** - Same customer has multiple active subscriptions simultaneously  
   - **Impact**: Business logic ambiguity - which subscription counts?  
   - **Solution**: Configurable policy (warn or strict) with logging  
   - **Default**: Warn and process all subscriptions  
   - **Implementation**: `_handle_overlaps()` in clean_subscriptions.py

⚠️ **Rapid re-subscriptions within 30 days** - Some customers re-subscribe within churn threshold  
   - **Impact**: Churn logic must handle correctly (gap <= 30 days = no churn)  
   - **Solution**: Explicit 30-day boundary handling in churn calculation  
   - **Note**: This is VALID behavior, not a data error

⚠️ **Missing country data** - Empty country field for some customers  
   - **Impact**: Minor - doesn't prevent metric calculation  
   - **Solution**: Log warning, keep record  
   - **Count**: 1 customer (C027)

⚠️ **Price outliers detected** - Some monthly_price values exceed IQR thresholds  
   - **Impact**: May indicate data entry errors or legitimate premium plans  
   - **Solution**: Log warning for manual review, do not auto-correct  
   - **Implementation**: `_run_quality_diagnostics()` in clean_subscriptions.py

### Implementation Implications

**Business Rule Enforcement:**
- **Churn definition**: Gap > 30 days between subscriptions (30 days exactly is NOT churn)
- **Date inclusivity**: `end_date` is treated as inclusive for activity calculations  
- **MRR calculation**: Full `monthly_price` counted if subscription active any point in month (no proration)
- **Retention anchor**: "3 months after signup" uses calendar month offset, not fixed 90 days

**Data Validation Severity:**
- **Critical (fail fast)**: Invalid date ranges, start-before-signup, unparseable dates, non-numeric prices
- **Warning (log & continue)**: Overlaps, missing country, price outliers, rapid re-subscriptions

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

### 9. Invalid Date Ranges
**Problem**: Some subscriptions have `end_date < start_date`
**Impact**: Violates temporal logic, creates negative subscription durations, breaks metric calculations
**Solution**: Fail validation - these are computation-critical errors requiring source correction
**Implementation**: `_validate_date_ranges()` method in SubscriptionDataCleaner
**Test Coverage**: Edge case tests in test_loader.py

### 10. Subscriptions Starting Before Customer Signup
**Problem**: Some subscriptions have `start_date < signup_date` from customer record
**Impact**: Logical impossibility (cannot subscribe before account exists), indicates referential integrity issue
**Solution**: Fail validation when customer signup dates are available - requires source correction
**Implementation**: `_validate_start_after_signup()` method in SubscriptionDataCleaner
**Test Coverage**: `test_start_before_signup_fails_when_signup_reference_provided()` in test_clean_subscriptions.py

### 11. Overlapping Subscriptions
**Problem**: Same customer has multiple active subscriptions with overlapping date ranges
**Impact**: Business logic ambiguity - which subscription's MRR counts? Risk of double-counting
**Solution**: Configurable policy - "warn" (log but allow) or "strict" (fail validation)
**Default Policy**: "warn" - allows processing while alerting to potential issue
**Implementation**: `_handle_overlaps()` method in SubscriptionDataCleaner with configurable policy
**Test Coverage**: `test_overlapping_subscriptions_fail_in_strict_policy()` in test_clean_subscriptions.py
**Note**: Current metrics implementation counts ALL active subscriptions, so overlaps increase MRR

### 12. Price Outliers
**Problem**: Some `monthly_price` values significantly deviate from plan median (IQR-based detection)
**Impact**: May indicate data entry errors OR legitimate premium/discounted pricing
**Solution**: Log warnings for manual review, do not auto-correct (could be valid business data)
**Implementation**: `_run_quality_diagnostics()` method in SubscriptionDataCleaner
**Note**: Also reports plan price spread to help identify data quality vs. business variance

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

**Subscription Tests**: `tests/test_clean_subscriptions.py` (16 tests)
- Unit tests for each cleaning operation
- Integration test verifying bronze data has known issues
- Validates all edge cases (empty values, malformed dates, non-numeric prices)
- **New**: Date range validation, start-after-signup validation, overlap policy tests

**Loader Tests**: `tests/test_loader.py` (35 tests)
- Basic data loading and validation tests (11 original tests)
- Edge case tests for data robustness (13 edge case tests):
  - Negative prices, zero prices, extreme values
  - Future/ancient dates, long subscription durations
  - Empty fields, mixed invalid rows
  - All-invalid scenarios
- **Skip-preprocessing scenario tests (11 tests)**:
  - Text prices that preprocessing normally fixes
  - Typo'd plan names ('baisc')
  - Malformed customer dates ('2024-13-05')
  - Duplicate customers and subscriptions
  - Orphaned subscriptions (customer removed, subscription remains)
  - Combined dirty data scenarios
- Validates that loader handles gracefully when preprocessing is skipped

**Metrics Tests**: `tests/test_metrics.py` (10 tests)

**Total**: 72 passing tests (was 68, added 4 for enhanced validations)

### Rule-to-Test Mapping

- **MRR month inclusion / activity-window semantics**
  - `tests/test_metrics.py`
- **Churn 30-day boundary (including exactly 30 days)**
  - `tests/test_metrics.py`
- **3-month retention calendar-offset behavior**
  - `tests/test_metrics.py`
- **Validation severity and dirty-data handling**
  - `tests/test_loader.py`
- **Customer cleaning rules (duplicates, malformed signup dates, country normalization)**
  - `tests/test_clean_customers.py`
- **Subscription cleaning rules (typos, text prices, date parsing, excluded customers)**
  - `tests/test_clean_subscriptions.py`
- **Date range validation (end_date >= start_date)**
  - `tests/test_clean_subscriptions.py` (implicit in integration tests)
  - `tests/test_loader.py` (edge cases)
- **Start-after-signup validation (subscription.start_date >= customer.signup_date)**
  - `tests/test_clean_subscriptions.py::test_start_before_signup_fails_when_signup_reference_provided()`
- **Unknown customer filtering (referential integrity)**
  - `tests/test_clean_subscriptions.py::test_unknown_customers_filtered_when_reference_provided()`
- **Overlap detection policy (warn vs strict)**
  - `tests/test_clean_subscriptions.py::test_overlapping_subscriptions_fail_in_strict_policy()`
- **Price outlier diagnostics**
  - Implemented in `_run_quality_diagnostics()` (logged warnings, no test failure)

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

After implementing the comprehensive cleaning pipeline:

### Test Coverage
- ✅ **Total**: 72 tests passing (was 68, added 4 for new validations)
  - Customer cleaning: 11 tests
  - Subscription cleaning: 16 tests (added 3 new)
  - Loader edge cases: 35 tests (added 1 new)
  - Metrics: 10 tests

### Data Cleaning Results
- ✅ **Customers**: 40 bronze → 38 silver
  - 1 removed: C019 (malformed date '2024-13-05')
  - 1 duplicate row removed: C038 (kept first occurrence)
  
- ✅ **Subscriptions**: 54 bronze → 53 silver
  - 1 removed for excluded customer C019
  
### Quality Corrections Applied
- ✅ 1 customer duplicate handled (C038: kept first occurrence)
- ✅ 1 malformed date removed (C019: '2024-13-05')
- ✅ 1 typo corrected ('baisc' → 'basic')
- ✅ 1 text-to-number conversion ('thirty' → '30')
- ✅ 1 country normalized to uppercase
- ✅ All whitespace trimmed from string fields

### Enhanced Validations Implemented
- ✅ **Date range validation**: Enforces `end_date >= start_date` (fail on violation)
- ✅ **Start-after-signup validation**: Enforces `subscription.start_date >= customer.signup_date` (fail on violation)
- ✅ **Unknown customer filtering**: Removes subscriptions for customer IDs not in silver customers (referential integrity)
- ✅ **Overlap detection**: Configurable policy ("warn" default, "strict" optional) for overlapping subscriptions
- ✅ **Price outlier diagnostics**: IQR-based outlier detection with warnings (non-blocking)
- ✅ **Plan pricing spread reporting**: Identifies plans with high price variance for review

### Coordinated Cleaning Pipeline
- ✅ Customers cleaned first → removed IDs tracked
- ✅ Subscription cleaner receives valid customer IDs from silver layer (not bronze)
- ✅ Subscription cleaner receives customer signup dates for start_date validation
- ✅ Orphaned subscriptions automatically filtered
- ✅ Robust loader with 24 edge case + skip-preprocessing tests
  - Gracefully handles dirty data scenarios without preprocessing
  - Degrades metrics appropriately with clear warnings

### Remaining Warnings (Non-Blocking)
These issues are logged but do not prevent processing:
- ⚠️ **1 malformed end_date**: '2024-02-30' (unparseable, logged as data source issue)
- ⚠️ **1 missing country**: Customer C027 has empty country field
- ⚠️ **Overlapping subscriptions**: Multiple customers have overlapping active subscriptions (policy: warn)
- ⚠️ **Price outliers**: Some monthly_price values exceed IQR thresholds (may be valid premium plans)
- ⚠️ **Rapid re-subscriptions**: Some customers re-subscribe within 30 days (valid behavior, not an error)

**Note**: Warnings reduced from 11 initial issues → 5 remaining categories after auto-correction and filtering

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
