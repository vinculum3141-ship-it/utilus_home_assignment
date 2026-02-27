# Design Document: SaaS Analytics Tool

## How the Code is Structured

**Medallion Architecture with Functional Modules:**

```
Bronze (data/bronze/)           Raw data, as-is from source
    ↓
Silver (data/silver/)           Cleaned & validated via src/transformers/
    ↓
Gold (output/)                  Aggregated metrics via metrics.py
```

**Core Modules:**
- `main.py` - CLI orchestration with 2-step pipeline (preprocess → calculate)
- `src/transformers/clean_customers.py` - Customer data cleaning (bronze → silver)
- `src/transformers/clean_subscriptions.py` - Subscription data cleaning (bronze → silver)
- `loader.py` - Data validation and Pydantic model loading (silver layer)
- `metrics.py` - Pure calculation functions (no I/O)
- `models.py` - Pydantic schemas for type safety

Each module has a single responsibility. Metrics remain pure functions (no I/O), enabling easy testing. Data quality is handled in a separate transformation layer before metrics calculation.

See [ARCHITECTURE.md](ARCHITECTURE.md) for SOLID principles and [DATA_QUALITY.md](DATA_QUALITY.md) for cleaning rationale.

## Data Processing Pipeline

**Step 1: Preprocessing (Bronze → Silver)**

Automated data cleaning handles issues discovered in data inspection:

*Customer Cleaning* (`clean_customers.py`):
- Duplicate customer ID handling (keep first occurrence)
- Malformed date removal (e.g., '2024-13-05')
- Empty signup date validation
- Missing country warnings
- Returns set of removed customer IDs

*Subscription Cleaning* (`clean_subscriptions.py`):
- Whitespace trimming on all fields
- Typo corrections ('baisc' → 'basic')
- Text-to-number conversions ('thirty' → '30')
- Date validation (fails on critical errors, warns on malformed dates)
- Filters out subscriptions for excluded customers

*Coordinated Cleaning*:
- Customers cleaned **first**, returns removed IDs
- Subscription cleaner accepts `excluded_customer_ids` parameter
- Ensures referential integrity between datasets
- Prevents orphaned subscriptions from causing metric errors

**Step 2: Metrics Calculation (Silver → Gold)**

Load validated data and calculate:
- Monthly MRR
- Monthly churn  
- Cohort retention

**Rationale**: Separation of concerns. Data quality issues are fixed once in silver layer, ensuring metrics calculations work with clean data. Bronze layer preserves original data for auditing.

## How Business Rules are Modeled

**MRR**: Sum `monthly_price` for subscriptions active in each month (no pro-rating).

**Churn**: Customer churns if subscription ends and no resubscribe within 30 days (inclusive).

**Retention**: Customers with active subscription 3 months after signup / cohort size.

## How to Add Another Metric

1. Add model in `models.py` (e.g., `MonthlyARPU`)
2. Add calculation function in `metrics.py` (pure function, no side effects)
3. Wire up in `main.py` orchestration (Step 2, after preprocessing)
4. Add tests

**Key**: No changes to data cleaning (transformers), loader, or existing metrics needed. Functional design with medallion architecture enables extension without modification.

## How to Add New Data Cleaning Rules

**For Customer Data**:
1. Add cleaning logic to `src/transformers/clean_customers.py`
2. Update `removed_customer_ids` set if customers are excluded
3. Add validation tests in `tests/test_clean_customers.py`
4. Document the issue in [DATA_QUALITY.md](DATA_QUALITY.md)

**For Subscription Data**:
1. Add cleaning logic to `src/transformers/clean_subscriptions.py`
2. Add validation tests in `tests/test_clean_subscriptions.py`
3. Document the issue in [DATA_QUALITY.md](DATA_QUALITY.md)

**Key Principles**:
- Cleaning is separate from metrics calculation
- Customer cleaning happens first, propagates removed IDs downstream
- Fix data quality issues once in silver layer, all calculations benefit
- Pipeline automatically applies cleaning on next run

## Assumptions and Trade-offs

**Assumptions**:
- **Customer duplicates**: Keep first occurrence, remove subsequent rows
- **Invalid customer dates**: Remove customer entirely (malformed dates like '2024-13-05')
- **Orphaned subscriptions**: Filter out subscriptions for removed customers
- **Overlapping subscriptions**: Both count toward MRR (logged as warning)
- **30-day churn grace**: Inclusive (exactly 30 days = not churned)
- **Date precision**: Day-level, no timezones, no pro-rating
- **Data quality**: Bronze data may contain issues; automated cleaning in silver layer fixes known problems
- **Coordinated cleaning**: Customer data cleaned first, removed IDs propagated to subscriptions
- **JSON output enhancement**: Added `metadata` section (not in spec) for production-readiness: timestamp, input file tracking, data quality warnings, and summary statistics

**Gaps in Requirements**: No spec for handling overlaps (data violates "one at a time"), duplicate handling strategy, or timezone treatment.

**Trade-offs**:
- **Medallion over monolith**: Three data layers (bronze/silver/gold) for data quality and traceability, at cost of more files/complexity
- **Automated cleaning over manual**: Fixed typos/conversions applied automatically vs. requiring source data correction
- **Simplicity over scale**: In-memory pandas (won't handle millions of rows)
- **Functional over OOP**: Pure functions for clarity and testability
- **Graceful degradation**: Log data issues, process what's valid (warnings surfaced in output)
- **Console output over structured logging**: Uses Rich Console for CLI feedback instead of traditional logging module (simpler for assignment scope, data quality warnings still captured in JSON output)
- **Correctness over speed**: Data validation prioritized over performance

## Data Quality Strategy

**Discovered Issues** (see [DATA_QUALITY.md](DATA_QUALITY.md)):
- Whitespace in all fields
- Typo: 'baisc' instead of 'basic' 
- Text value: 'thirty' instead of '30'
- Invalid date: '2024-02-30'

**Solution**: Automated cleaning pipeline (`src/transformers/`) with:
- Critical validations that fail fast (empty customer_id, malformed start_date)
- Automated corrections for known issues (typos, text-to-number)
- Warnings for non-critical issues (malformed end_date)
- 12 test cases ensuring cleaning works correctly

**Rationale**: Separate data quality concerns from business logic. Metrics code stays simple and works with validated data. Bronze layer preserves original data for auditing and reprocessing.

---

*For detailed architecture decisions, validation strategy, SOLID principles, and technology rationale, see [ARCHITECTURE.md](ARCHITECTURE.md). For data quality issues and solutions, see [DATA_QUALITY.md](DATA_QUALITY.md).*
