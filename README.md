# SaaS Analytics Tool

A CLI tool for calculating SaaS metrics (MRR, churn, cohort retention) from CSV files, with built-in data quality validation and cleaning.

## Architecture

This project uses a **medallion architecture** with three data layers:

- **Bronze** (`data/bronze/`): Raw data as-is from source
- **Silver** (`data/silver/`): Cleaned and validated data
- **Gold** (`output/`): Aggregated metrics and analytics

See [docs/DATA_QUALITY.md](docs/DATA_QUALITY.md) for details on data issues and cleaning.

## Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

For development (running tests):
```bash
pip install -r requirements-dev.txt
```

### 3. Place Raw Data

Put your CSV files in `data/bronze/`:
- `data/bronze/customers.csv`
- `data/bronze/subscriptions.csv`

### 4. Run

```bash
# Full pipeline with data cleaning
python main.py

# Or skip preprocessing if silver data already exists
python main.py --skip-preprocessing
```

**Options:**
- `--customers-file`: Path to customers CSV (default: `data/silver/customers_silver.csv`)
- `--subscriptions-file`: Path to subscriptions CSV (default: `data/silver/subscriptions_silver.csv`)  
- `--output-file`: Output JSON path (default: `output/report.json`)
- `--skip-preprocessing`: Skip bronze→silver cleaning step

## Data Processing Pipeline

The tool automatically:

1. **Preprocessing** (Bronze → Silver):
   - **Customer Cleaning**:
     - Removes duplicate customer records (keeps first occurrence)
     - Removes customers with malformed dates (e.g., '2024-13-05')
     - Validates signup dates
     - Normalizes country names to uppercase
     - Logs missing country warnings
   - **Subscription Cleaning**:
     - Trims whitespace from all fields
     - Corrects known typos ('baisc' → 'basic')
     - Converts text to numbers ('thirty' → '30')
     - **Validates date ranges** (end_date >= start_date)
     - **Validates start-after-signup** (subscription.start_date >= customer.signup_date)
     - **Filters unknown customers** (referential integrity from silver layer)
     - **Detects overlapping subscriptions** (configurable warn/strict policy)
     - **Identifies price outliers** (IQR-based diagnostics)
     - Validates dates and numeric fields
   - **Quality Gates**: Fails on critical issues, warns on minor ones
   - **Coordination**: Customers cleaned first, removed IDs and signup dates propagated to subscriptions

2. **Metrics Calculation** (Silver → Gold):
   - Loads validated data
   - Calculates MRR, churn, retention
   - Generates JSON report with prominent data quality warnings

## Business Rules (Canonical)

The following rules are the canonical definitions used by implementation and tests:

1. **MRR month inclusion**
  - A subscription contributes full `monthly_price` for any calendar month where it is active at least one day.
  - No proration is applied.

2. **End date treatment**
  - `end_date` is treated as **inclusive** for activity checks.

3. **Churn threshold**
  - Churn occurs when a subscription has an `end_date` and no new subscription starts within 30 days.
  - Boundary rule: `gap_days <= 30` is **not churn**; `gap_days > 30` is **churn**.

4. **3-month retention anchor**
  - “3 months after signup” is computed as a **calendar month offset** (`signup_date + DateOffset(months=3)`), not fixed 90 days.

5. **Validation severity**
  - Computation-critical fields fail fast on invalid input.
  - Monitoring fields (e.g., `country`) generate warnings but do not block metric computation.

See [docs/DATA_QUALITY.md](docs/DATA_QUALITY.md) for full rule rationale and validation behavior.

## Output Format

The tool generates a JSON report with:

1. **Monthly MRR** - Monthly Recurring Revenue for each calendar month
2. **Monthly Churn** - Number of churned customers per month
3. **Cohort Retention** - 3-month retention rates by signup cohort

Example output structure:
```json
{
  "metadata": {
    "generated_at": "2026-02-21T10:30:00Z",
    "input_files": {...},
    "data_quality_warnings": [...]
  },
  "monthly_mrr": [
    {"month": "2024-01", "mrr": 150.0}
  ],
  "monthly_churn": [
    {"month": "2024-01", "churned_count": 2}
  ],
  "cohort_retention": [
    {
      "cohort_month": "2024-01",
      "cohort_size": 10,
      "active_after_3_months": 8,
      "retention_rate_3m": 0.80
    }
  ]
}
```

## Data Quality

The tool performs comprehensive validation and logs data quality issues:

**Validated positive findings:**
- ✅ No negative prices
- ✅ All IDs populated

**Critical issues (block processing):**
- ❌ Invalid date ranges (end_date < start_date)
- ❌ Subscriptions starting before customer signup
- ❌ Malformed dates
- ❌ Orphaned subscriptions (referential integrity)

**Auto-corrected issues:**
- ⚠️ Typos, text-in-numeric-fields, duplicates, whitespace

**Monitored issues (non-blocking):**
- ⚠️ Overlapping subscriptions (configurable policy)
- ⚠️ Missing country data
- ⚠️ Price outliers

See [docs/DATA_QUALITY.md](docs/DATA_QUALITY.md) for complete findings summary with 12 documented issues.

Data quality warnings are included in the output JSON.

## Testing

**Note**: Tests require development dependencies.

```bash
# Install dev dependencies first
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## Project Structure

```
.
├── data/
│   ├── bronze/              # Raw input data
│   ├── silver/              # Cleaned data (generated)
│   └── gold/                # Future: aggregated views
├── src/
│   └── transformers/        # Data cleaning pipeline
├── tests/                   # Test suite (72 tests)
├── notebooks/               # Data exploration
├── docs/                    # Documentation
│   ├── DESIGN.md
│   ├── ARCHITECTURE.md
│   ├── DATA_QUALITY.md
│   ├── IMPLEMENTATION_APPROACHES.md
│   ├── METRICS_IMPACT_ANALYSIS.md
│   └── RESTRUCTURING_SUMMARY.md
├── main.py                  # CLI entry point (2-step pipeline)
├── loader.py                # Data loading and validation
├── metrics.py               # Business logic (MRR, churn, cohorts)
├── models.py                # Pydantic data models
├── output/                  # Generated reports
└── README.md                # This file
```

## Documentation

- **[DESIGN.md](docs/DESIGN.md)** - Architecture and design decisions
- **[DATA_QUALITY.md](docs/DATA_QUALITY.md)** - Data issues discovered and solutions
- **[IMPLEMENTATION_APPROACHES.md](docs/IMPLEMENTATION_APPROACHES.md)** - 2-hour vs. production design
- **[METRICS_IMPACT_ANALYSIS.md](docs/METRICS_IMPACT_ANALYSIS.md)** - How cleaning affected metrics
- **[RESTRUCTURING_SUMMARY.md](docs/RESTRUCTURING_SUMMARY.md)** - What changed and why

## Design

See [docs/DESIGN.md](docs/DESIGN.md) for detailed architecture and design decisions.
