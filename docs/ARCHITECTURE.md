# Architecture Document: SaaS Analytics Tool

## Data Architecture: Medallion Pattern (Simplified)

**Current Implementation**: Bronze → Silver → Report (JSON)

**Architectural Reality**:
- **Bronze Layer** (`data/bronze/`): Raw CSV files as received
- **Silver Layer** (`data/silver/`): Cleaned, validated CSV files (12 data quality issues remediated)
- **"Gold Layer"**: Currently just the JSON report output (`output/report.json`)

**Honest Assessment**:
The current implementation lacks a true gold layer. We go from silver (clean individual records) directly to aggregated reports. In a proper medallion architecture:

**What's Missing (True Gold Layer)**:
- **Enriched datasets**: Joined customer + subscription data with computed fields
- **Business-ready tables**: e.g., `subscription_facts` with `is_active`, `months_active`, `is_churned` flags
- **Denormalized structures**: Analytics-optimized tables ready for querying/reporting
- **Reusable artifacts**: Gold tables that multiple reports/dashboards could consume

**Current Flow**:
```
Bronze (raw) → Silver (cleaned) → Metrics Functions → JSON Report
                                  ↑ (This isn't really "gold")
```

**Proper Flow Would Be**:
```
Bronze (raw) → Silver (cleaned) → Gold (enriched tables) → Reports/Dashboards
```

**Why This Approach for Assignment**:
- **Time-boxed scope**: 2-hour assignment doesn't warrant full data warehouse
- **Good enough**: Metrics calculation does the enrichment/joining on-the-fly
- **Clear intent**: Shows understanding of medallion concepts even if simplified
- **Pragmatic**: Don't over-engineer when direct silver→report path works

**Production Recommendation**:
Add a `src/transformers/create_gold_layer.py` that materializes enriched tables:
- `customer_subscription_enriched.csv`: Joined data with computed flags
- `monthly_aggregates.csv`: Pre-computed monthly metrics
- Then reporting layer reads from gold, not silver

This would make the architecture claim legitimate and enable multiple downstream consumers.

## Architectural Style: Functional over OOP

**Design Decision**: Use functional programming patterns for data transformations, OOP for data modeling.

**Rationale**:
- **Data pipelines favor pure functions**: Same input → same output, no hidden state
- **Testability**: Pure functions in `metrics.py` have zero side effects, easy to test
- **Composability**: Functions chain naturally (load → validate → transform → output)
- **Simplicity**: No class hierarchies, inheritance, or stateful objects to manage
- **Pythonic**: Aligns with Python's "simple is better than complex" philosophy

**OOP Where Appropriate**:
- **Pydantic models**: Encapsulate validation logic and data structure
- **Exception hierarchy**: `DataQualityError` provides clear error boundaries
- **Type safety**: Models provide contracts between layers

**Benefits for This Problem**:
- Business logic is inherently transformational (CSV → metrics)
- No need for persistent state or complex object interactions
- Easy to add new metrics without modifying existing classes
- Clear data flow: `List[Customer]` → `calculate_cohort_retention()` → `List[CohortRetention]`

**Alternative OOP Approach Considered**:
- Could use `MRRCalculator`, `ChurnAnalyzer`, `CohortAnalyzer` classes
- Rejected: Adds complexity without benefit for stateless transformations
- Would violate YAGNI (You Aren't Gonna Need It) principle

## Design Principles Adherence

### SOLID Principles

**Single Responsibility Principle** ✅
- `loader.py`: Only loads and validates data
- `metrics.py`: Only calculates business metrics
- `models.py`: Only defines data structures
- `main.py`: Only orchestrates CLI flow

**Open/Closed Principle** ✅
- Add new metrics: extend `metrics.py` with new function, no modification to existing code
- Add new validation: extend Pydantic models with new validators
- Add new output format: modify only `main.py` serialization

**Liskov Substitution Principle** ✅
- Pydantic models are substitutable (any `Subscription` works anywhere)
- All metric functions accept standard types (`list[Customer]`, etc.)

**Interface Segregation Principle** ✅
- Small, focused modules - no "god objects"
- Each function has minimal parameters
- No forced dependencies on unused functionality

**Dependency Inversion Principle** ✅
- High-level logic (`metrics.py`) depends on abstractions (`models.py`)
- Low-level details (`loader.py`) depend on same abstractions
- No direct CSV parsing in business logic

### Additional Patterns

- **Fail Fast**: Invalid data caught at boundaries (Pydantic validation)
- **Immutability**: Models are immutable (Pydantic BaseModel)
- **Pure Functions**: `metrics.py` has no side effects
- **Type Safety**: Full type hints throughout
- **Explicit is Better**: Clear function names, no magic

## Technology Choices

- **Pandas**: Industry standard for CSV/tabular data
- **Pydantic**: Type-safe models with built-in validation
- **Typer + Rich**: Modern CLI with great UX (colors, progress)
- **Pytest**: De facto standard for Python testing

### Dependency Management

**Design Decision**: Separate production and development dependencies.

**Structure**:
- `requirements.txt`: Production dependencies only (4 packages)
- `requirements-dev.txt`: Development/testing dependencies (includes requirements.txt via `-r`)

**Rationale**:
- **Separation of concerns**: Production environments don't need test frameworks
- **Lighter deployments**: Fewer packages to install in production
- **Standard practice**: Follows Python community conventions
- **Clear intent**: Makes it obvious what's needed to run vs develop

**Usage**:
```bash
# Production use
pip install -r requirements.txt
python main.py assignment/customers.csv assignment/subscriptions.csv output/report.json

# Development/testing
pip install -r requirements-dev.txt
pytest
```

## Testing Strategy

**Coverage**:
- ✅ Core business logic (churn, retention, MRR)
- ✅ Edge cases (30-day boundary, 3-month boundary, overlaps)
- ✅ Validation (missing columns, invalid data)
- ✅ Data quality handling (duplicates, unknowns)

**Not Tested** (time constraint):
- End-to-end CLI integration
- JSON output format validation
- All possible date edge cases

## Future Enhancements

- **Structured logging**: Replace Rich Console output with proper logging module (DEBUG/INFO/WARNING/ERROR levels, log files, structured JSON logs for production monitoring)
- **Incremental processing**: Process only new records (requires state tracking)
- **Streaming**: Handle large files without loading fully into memory
- **Database output**: Write directly to SQL instead of JSON
- **API mode**: Expose as REST API instead of CLI
- **Data quality rules**: Configurable validation rules
- **Performance**: Optimize with vectorized pandas operations or Polars