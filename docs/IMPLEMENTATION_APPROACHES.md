# Implementation Approach: 2-Hour Assignment vs. Production-Ready Design

## Overview

This document compares two approaches to data validation and quality:
1. **2-Hour Assignment**: Pragmatic, in-code validation suitable for take-home interviews
2. **Production Design**: Full medallion architecture with separate ETL layer (current implementation)

Both are valid depending on context. Understanding when to use each is key.

---

## 2-Hour Assignment Approach

### Philosophy
- **Fail fast at boundaries**: Validate where data enters your system
- **Minimal architecture**: No separate ETL, clean within loader if needed
- **Prove it works**: Tests with bad data showing your validation catches issues
- **Clear over clever**: Simple error messages, obvious code structure

### Reality Check: Data Quality vs. Time Box

In this assignment dataset, multiple independent quality issues exist (duplicates, malformed dates,
text in numeric fields, unknown customer references, overlaps, etc.). In a strict 2-hour window,
it is normal that teams will implement different subsets of remediation. Therefore:

- **Metric outputs may vary across valid submissions** based on assumptions and cleanup depth.
- This is **not necessarily incorrect** if assumptions are explicit and consistently applied.
- Evaluators should score for **correctness under stated assumptions**, not exact numeric parity alone.

### 2-Hour Priority Model (What to Implement First)

When time is constrained, implement in this order:

1. **Tier 1 – Must Have (Blockers)**
    - Required-column checks
    - Parseable critical dates (`signup_date`, `start_date`)
    - Numeric `monthly_price`
    - Referential integrity gate (unknown `customer_id` handling)
    - Clear failure/warning behavior (no silent corruption)

2. **Tier 2 – Should Have (High Impact, Fast Wins)**
    - Known deterministic fixes (e.g., `'thirty' -> '30'`, `'baisc' -> 'basic'`)
    - Duplicate customer handling rule (e.g., keep first)
    - Date-range invariant (`end_date >= start_date` when present)

3. **Tier 3 – Nice to Have (Advanced/Exploratory)**
    - Overlap resolution policy beyond warning
    - Outlier diagnostics
    - Additional monitoring dimensions and deep anomaly analysis

### Required Assumption Disclosure (2-Hour)

A 2-hour submission should include a short “assumptions” section in README or design notes with:

- Whether `end_date` is inclusive
- Churn threshold boundary (`<= 30` vs `> 30`)
- Retention anchor (`+3 calendar months` vs `90 days`)
- Whether partial months are prorated for MRR
- Which anomalies are corrected vs warned vs rejected

### Definition of “Good” in 2 Hours

A strong 2-hour submission is one that:

- Produces deterministic outputs
- Fails safely on critical violations
- Includes targeted tests for dirty inputs
- Documents assumptions and known limitations

It is **not required** to build a full medallion pipeline in 2 hours.

### Implementation Pattern

```python
# loader.py - Data loading with inline validation
def load_subscriptions(filepath: Path, valid_customer_ids: set[str]) -> list[Subscription]:
    """
    Load and validate subscriptions.
    
    Validation:
    - Required columns present
    - Prices are numeric (with common text->number conversion)
    - Dates are parseable
    - Customer IDs exist
    
    Raises:
        ValueError: If critical validation fails
    """
    df = pd.read_csv(filepath)
    
    # 1. Validate structure
    required = {"customer_id", "start_date", "monthly_price"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")
    
    # 2. Clean common issues (with logging)
    if (df['monthly_price'] == 'thirty').any():
        logger.warning("Converting text 'thirty' to numeric '30'")
        df['monthly_price'] = df['monthly_price'].replace('thirty', '30')
    
    # 3. Validate types
    df['monthly_price'] = pd.to_numeric(df['monthly_price'], errors='coerce')
    if df['monthly_price'].isna().any():
        bad_rows = df[df['monthly_price'].isna()]
        raise ValueError(f"Found non-numeric prices in rows: {bad_rows.index.tolist()}")
    
    # 4. Validate business rules
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
    if df['start_date'].isna().any():
        raise ValueError("Found unparseable start dates")
    
    # 5. Convert to models (Pydantic will do final validation)
    subscriptions = []
    for _, row in df.iterrows():
        if row['customer_id'] not in valid_customer_ids:
            logger.warning(f"Unknown customer {row['customer_id']} - skipping")
            continue
        
        try:
            sub = Subscription(**row.to_dict())
            subscriptions.append(sub)
        except ValidationError as e:
            logger.warning(f"Invalid subscription: {e}")
    
    return subscriptions
```

### Key Tests (Must Have)

```python
# tests/test_loader.py

def test_load_subscriptions_rejects_missing_columns():
    """Critical: Must validate structure."""
    df = pd.DataFrame({'customer_id': ['C001']})  # Missing required columns
    # Save to temp file and test
    
    with pytest.raises(ValueError, match="Missing columns"):
        load_subscriptions(temp_file, valid_ids={'C001'})

def test_load_subscriptions_handles_text_prices():
    """Critical: Must handle 'thirty' as 30."""
    df = pd.DataFrame({
        'customer_id': ['C001'],
        'monthly_price': ['thirty'],  # Text price!
        'start_date': ['2024-01-01']
    })
    
    subs = load_subscriptions_from_df(df, valid_ids={'C001'})
    
    assert len(subs) == 1
    assert subs[0].monthly_price == 30.0

def test_load_subscriptions_rejects_invalid_prices():
    """Critical: Must reject truly invalid prices."""
    df = pd.DataFrame({
        'customer_id': ['C001'],
        'monthly_price': ['not-a-number'],  # Cannot convert
        'start_date': ['2024-01-01']
    })
    
    with pytest.raises(ValueError, match="non-numeric prices"):
        load_subscriptions_from_df(df, valid_ids={'C001'})

def test_load_subscriptions_rejects_bad_dates():
    """Critical: Must validate dates."""
    df = pd.DataFrame({
        'customer_id': ['C001'],
        'monthly_price': ['30'],
        'start_date': ['not-a-date']
    })
    
    with pytest.raises(ValueError, match="unparseable start dates"):
        load_subscriptions_from_df(df, valid_ids={'C001'})
```

### Project Structure (2-Hour)

```
assignment/
├── loader.py          # Validation happens here
├── metrics.py         # Pure calculation (assumes valid data)
├── models.py          # Pydantic schemas
├── main.py            # Simple CLI
├── tests/
│   ├── test_loader.py # Must include bad data tests
│   └── test_metrics.py
└── output/
    └── report.json
```

### What Evaluators Look For

✅ **Must Have:**
- Input validation with clear error messages
- Tests proving validation works (especially with bad data)
- Handling of edge cases (text prices, invalid dates, missing data)
- No silent failures (better to crash than produce wrong results)

❌ **Don't Need:**
- Separate ETL pipeline
- Multiple data layers (bronze/silver/gold)
- Automated data cleaning infrastructure
- Production-grade observability

### Time Allocation (2 Hours)

- **30 min**: Core logic (MRR, churn, retention calculations)
- **30 min**: Data loading with validation
- **45 min**: Tests (including bad data scenarios)
- **15 min**: CLI, documentation, polish

---

## Production-Ready Design (Current Implementation)

### Philosophy
- **Separation of concerns**: ETL is separate from analytics
- **Auditable**: Raw data preserved, transformations traceable
- **Reprocessable**: Can re-run cleaning with new rules
- **Observable**: Logging, metrics, data quality monitoring

### Architecture

```
data/bronze/           ← Raw data (immutable, source of truth)
    ↓ (transformers)
data/silver/           ← Cleaned data (validated, standardized)
    ↓ (loader + metrics)
output/                ← Analytics outputs (aggregated)
```

### Implementation Pattern

```python
# src/transformers/clean_subscriptions.py
class SubscriptionDataCleaner:
    """
    Separate data cleaning layer.
    
    Responsibilities:
    - Fix known data quality issues
    - Standardize formats
    - Validate business rules
    - Log all transformations
    
    Does NOT:
    - Calculate metrics
    - Load into application models
    - Make business decisions
    """
    
    def clean(self, bronze_df: pd.DataFrame) -> pd.DataFrame:
        """Transform bronze → silver with full validation."""
        df = bronze_df.copy()
        
        # Systematic cleaning with validation
        df = self._clean_customer_id(df)  # Fails on empty
        df = self._clean_dates(df)         # Fails on critical issues
        df = self._clean_prices(df)        # Converts + validates
        df = self._clean_plans(df)         # Typo correction
        
        if self.validation_errors:
            raise ValueError("Validation failed:\n" + "\n".join(self.validation_errors))
        
        return df
```

```python
# loader.py - Assumes silver data is already clean
def load_subscriptions(filepath: Path) -> list[Subscription]:
    """
    Load validated data from silver layer.
    
    Expects: Clean CSV with correct types from silver layer
    Validation: Minimal (structure + Pydantic enforcement only)
    """
    df = pd.read_csv(filepath)
    
    # Structure validation only
    required = {"customer_id", "start_date", "monthly_price"}
    if not required.issubset(df.columns):
        raise ValueError(f"Silver data missing columns: {required - set(df.columns)}")
    
    # Load into models (Pydantic handles final validation)
    return [Subscription(**row.to_dict()) for _, row in df.iterrows()]
```

### Testing Strategy (Layered)

```python
# tests/test_clean_subscriptions.py - Tests for ETL layer
def test_cleaner_corrects_typos():
    """Test transformation logic."""
    df = pd.DataFrame({'plan': ['baisc']})
    result = cleaner.clean(df)
    assert result['plan'].iloc[0] == 'basic'

def test_cleaner_converts_text_prices():
    """Test data type conversions."""
    df = pd.DataFrame({'monthly_price': ['thirty']})
    result = cleaner.clean(df)
    assert result['monthly_price'].iloc[0] == '30'

def test_cleaner_fails_on_empty_customer_id():
    """Test critical validations."""
    df = pd.DataFrame({'customer_id': ['']})
    with pytest.raises(ValueError, match="empty customer_id"):
        cleaner.clean(df)
```

```python
# tests/test_loader.py - Tests for loading layer
def test_load_from_silver_succeeds():
    """Assumes silver data is clean."""
    subs = load_subscriptions("data/silver/subscriptions_silver.csv")
    assert len(subs) > 0
    assert all(isinstance(s, Subscription) for s in subs)

def test_load_rejects_malformed_silver_structure():
    """Only validates structure, not content."""
    df = pd.DataFrame({'wrong_columns': [1]})
    with pytest.raises(ValueError, match="missing columns"):
        load_from_df(df)
```

```python
# tests/test_metrics.py - Tests for business logic
def test_mrr_calculation():
    """Pure business logic, assumes valid input."""
    subs = [Subscription(monthly_price=30, ...)]
    mrr = calculate_monthly_mrr(subs)
    assert mrr == expected_value
```

### Project Structure (Production)

```
├── data/
│   ├── bronze/              # Raw CSVs (immutable)
│   ├── silver/              # Cleaned CSVs (generated)
│   └── gold/                # [MISSING] Would contain enriched tables
├── src/
│   └── transformers/        # ETL logic
│       └── clean_subscriptions.py
├── loader.py                # Loads from silver (minimal validation)
├── metrics.py               # Pure business logic
├── main.py                  # Orchestrates: clean → load → calculate
├── tests/
│   ├── test_clean_subscriptions.py  # ETL tests
│   ├── test_loader.py               # Loading tests
│   └── test_metrics.py              # Business logic tests
├── docs/
│   ├── DATA_QUALITY.md      # Documents known issues
│   └── DESIGN.md
└── notebooks/               # Exploratory analysis
    └── 01_subscription_data_inspection.ipynb
```

### Architectural Gap: Missing Gold Layer

**Current Reality**: We go Bronze → Silver → JSON Report

**What's Missing**: The implementation lacks a true gold layer. In proper medallion architecture:

- **Silver**: Clean individual records (customers, subscriptions)
- **Gold**: **Enriched, joined, business-ready tables** (e.g., `subscription_facts` with denormalized customer data, computed flags like `is_active`, `is_churned`, duration calculations)
- **Reports**: Aggregations reading FROM gold tables

**Current Flow**:
```
Bronze → Silver → metrics.py (does enrichment in-memory) → JSON
                  ↑ This joining/enrichment should be materialized as gold
```

**What Gold Would Look Like**:
```python
# src/transformers/create_gold_layer.py (NOT IMPLEMENTED)

def create_subscription_enriched(silver_customers_df, silver_subscriptions_df):
    """
    Silver → Gold transformation.
    
    Creates enriched table joining customers + subscriptions with computed fields:
    - customer_country, customer_signup_date (denormalized)
    - is_active (boolean based on end_date)
    - subscription_duration_days
    - months_active (count of calendar months)
    - is_churned (based on 30-day rule)
    """
    # Join and enrich...
    return enriched_df
```

Then `data/gold/subscription_enriched.csv` would be the single source for all reports.

**Why Not Implemented**:
- Time-boxed assignment scope (2 hours)
- Metrics calculation does the enrichment on-the-fly (works, just not materialized)
- Demonstrates medallion concept even if simplified
- Production would definitely add this layer

**Impact**: The current architecture is more accurately "Bronze → Silver → Report" rather than true three-layer medallion.

### What This Enables

✅ **Production Benefits:**
- **Reprocessable**: Change cleaning rules, re-run pipeline
- **Auditable**: Bronze preserves original data
- **Testable**: Each layer tested independently
- **Observable**: Logging at each layer, data quality metrics
- **Scalable**: Can replace pandas with Spark in transformers without changing metrics
- **Maintainable**: Clear separation of concerns

❌ **Overkill For:**
- 2-hour assignments
- One-off analysis
- Single-person projects
- Prototype/POC work

---

## Key Differences

| Aspect | 2-Hour Assignment | Production Design (Current) |
|--------|------------------|-------------------|
| **Validation Location** | In loader (at boundary) | Separate transformer layer |
| **Data Layers** | None (single CSV) | Bronze/Silver (+ JSON report) |
| **Gold Layer** | N/A | **Missing** (would be enriched tables) |
| **Cleaning Strategy** | Inline with validation | Separate cleaning module |
| **Test Focus** | Loader handles bad inputs | Each layer tested separately |
| **Error Handling** | Fail fast, clear messages | Layered (fail vs. warn) |
| **Code Structure** | Monolithic loader | Separated concerns |
| **Complexity** | Low (3-4 modules) | Higher (6+ modules, multiple layers) |
| **Setup Time** | Minutes | Hours |
| **Best For** | Interviews, POCs | Production systems |

## Validation Maturity Comparison

### 2-Hour: "Defensive Loading"
```python
# Single validation point
load() → validate() → parse() → use()
         ↑
    Tests prove this catches bad data
```

**Pros:**
- Simple to understand
- Fast to implement
- Tests are straightforward
- Clear error messages at entry point

**Cons:**
- Mixes concerns (loading + cleaning + validation)
- Cannot reprocess with new rules
- No audit trail of transformations

### Production: "Layered Validation"
```python
# Multiple validation layers
Bronze (raw) → Transform (validate + clean) → Silver (clean)
                    ↑                             ↓
              Tests prove cleaning          Load (validate structure only)
                                                  ↓
                                            Use (assumes valid)
```

**Pros:**
- Separation of concerns
- Reprocessable pipeline
- Audit trail (bronze preserved)
- Can test each layer independently

**Cons:**
- More complex
- More files/modules
- Requires understanding of data pipeline concepts

---

## When to Use Each Approach

### Use 2-Hour Approach For:
- ✅ Technical interviews / take-home assignments
- ✅ One-off data analysis
- ✅ Internal tools with trusted data sources
- ✅ Prototypes / POCs
- ✅ Single-person projects with limited scope
- ✅ When time is more valuable than architecture

### Use Production Approach For:
- ✅ Production data pipelines
- ✅ Systems processing untrusted external data
- ✅ Analytics platforms used by multiple teams
- ✅ Regulated industries requiring audit trails
- ✅ Long-lived systems that will evolve
- ✅ When data quality is mission-critical

---

## Recommendations

### For Interview Assignments
1. **Focus on proving your code works** with tests for bad inputs
2. **Keep validation in loader** - don't over-architect
3. **Document assumptions** clearly
4. **Show error handling** - fail fast with clear messages
5. **Time-box architecture** - 2 hours means pragmatic choices

### For Production Systems
1. **Start with medallion architecture** if you know data quality is an issue
2. **Separate ETL from analytics** for maintainability
3. **Test each layer independently**
4. **Document data quality issues** as they're discovered
5. **Make transformation logic reusable**

### Transitioning from Assignment to Production
If you built the 2-hour approach and need to productionize:

1. **Extract cleaning to separate module** (loader.py → transformers/)
2. **Add bronze/silver layers** (preserve original data)
3. **Split tests** (ETL tests vs. loading tests)
4. **Add observability** (logging, metrics, monitoring)
5. **Document data quality** (issues, decisions, trade-offs)

This is essentially what we did in this repo!

---

## Conclusion

**Both approaches are valid.** The 2-hour approach shows software engineering discipline (defensive programming, testing, error handling). The production approach shows data engineering maturity (separation of concerns, data quality focus, reprocessability).

For an interview: **Show the 2-hour approach.** Prove your code handles bad data with tests.

For production: **Use the medallion architecture.** Separate data quality from business logic.

The rejection was likely because the original submission didn't validate inputs or test with bad data **at all**, not because it lacked a medallion architecture. The current implementation is actually more sophisticated than needed for a 2-hour assignment, but it demonstrates proper production-grade data engineering.
