# Design Document: SaaS Analytics Tool

## How the Code is Structured

**Four-module functional design:** `main.py` (CLI) → `loader.py` (validation) + `metrics.py` (pure functions) → `models.py` (Pydantic)

Each module has a single responsibility. Metrics are pure functions (no I/O), enabling easy testing and extensibility. See [ARCHITECTURE.md](ARCHITECTURE.md) for SOLID principles and detailed rationale.

## How Business Rules are Modeled

**MRR**: Sum `monthly_price` for subscriptions active in each month (no pro-rating).

**Churn**: Customer churns if subscription ends and no resubscribe within 30 days (inclusive).

**Retention**: Customers with active subscription 3 months after signup / cohort size.

## How to Add Another Metric

1. Add model in `models.py` (e.g., `MonthlyARPU`)
2. Add calculation function in `metrics.py` (pure function, no side effects)
3. Wire up in `main.py` orchestration
4. Add tests

**Key**: No changes to loader or existing metrics needed. Functional design enables extension without modification.

## Assumptions and Trade-offs

**Assumptions**:
- Duplicate customers: keep first occurrence
- Overlapping subscriptions: both count toward MRR (logged)
- 30-day churn grace: inclusive (exactly 30 days = not churned)
- Date precision: day-level, no timezones, no pro-rating
- **JSON output enhancement**: Added `metadata` section (not in spec) for production-readiness: timestamp, input file tracking, data quality warnings, and summary statistics

**Gaps in Requirements**: No spec for handling overlaps (data violates "one at a time"), duplicate handling strategy, or timezone treatment.

**Trade-offs**:
- **Simplicity over scale**: In-memory pandas (won't handle millions of rows)
- **Functional over OOP**: Pure functions for clarity and testability
- **Graceful degradation**: Log data issues, process what's valid (11 warnings surfaced)
- **Console output over structured logging**: Uses Rich Console for CLI feedback instead of traditional logging module (simpler for 1-2 hour scope, data quality warnings still captured in JSON output)
- **1-2 hour scope**: Core correctness prioritized over edge cases

---

*For detailed architecture decisions, validation strategy, SOLID principles, and technology rationale, see [ARCHITECTURE.md](ARCHITECTURE.md)*
