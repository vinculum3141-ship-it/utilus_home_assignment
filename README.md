# SaaS Analytics Tool

A simple CLI tool for calculating SaaS metrics (MRR, churn, cohort retention) from CSV files.

## Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

For production use (running the tool):
```bash
pip install -r requirements.txt
```

For development (running tests, contributing):
```bash
pip install -r requirements-dev.txt
```

### 3. Run

```bash
python main.py assignment/customers.csv assignment/subscriptions.csv output/report.json
```

**Arguments:**
- `customers.csv` - Customer data (customer_id, signup_date, country)
- `subscriptions.csv` - Subscription data (customer_id, start_date, end_date, plan, monthly_price)
- `output_path` - Output file path for analytics report (e.g., `output/report.json`)

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

The tool validates inputs and logs data quality issues such as:
- Duplicate customer IDs
- Unknown customer references in subscriptions
- Invalid dates or prices
- Overlapping subscriptions
- Missing required fields

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
├── main.py                  # CLI entry point
├── loader.py                # Data loading and validation
├── metrics.py               # Business logic (MRR, churn, cohorts)
├── models.py                # Pydantic data models
├── tests/                   # Test suite
├── assignment/              # Assignment data (customers.csv, subscriptions.csv)
├── output/                  # Generated reports (gitignored)
├── docs/                    # Documentation
│   ├── DESIGN.md
│   └── ARCHITECTURE.md
├── requirements.txt         # 4 production deps
├── requirements-dev.txt     # +2 dev deps
└── README.md                # This file
```

## Design

See [docs/DESIGN.md](docs/DESIGN.md) for detailed architecture and design decisions.
