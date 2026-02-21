# Architecture Documentation

## 🏛️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Users/Systems                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │      FastAPI REST API          │
         │     (Thin Interface)           │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │    Application Layer           │
         │  ┌─────────┐  ┌──────────┐   │
         │  │Pipeline │  │  Runner  │   │
         │  └─────────┘  └──────────┘   │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │      Domain Layer              │
         │  ┌────────────┐               │
         │  │Transformers│               │
         │  │(Pure Logic)│               │
         │  └────────────┘               │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   Infrastructure Layer         │
         │  ┌────────────┐               │
         │  │Repositories│               │
         │  │  Storage   │               │
         │  │  Logging   │               │
         │  └────────────┘               │
         └───────────────┬───────────────┘
                         │
                         ▼
    ┌────────────────────┴─────────────────────┐
    │                                           │
    ▼                                           ▼
┌─────────────┐                         ┌──────────────┐
│   Storage   │                         │   Database   │
│Bronze/Silver│                         │  (Metadata)  │
│   /Gold     │                         └──────────────┘
└─────────────┘
```

## 🎯 Medallion Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Flow Pipeline                           │
└─────────────────────────────────────────────────────────────────┘

    Raw Data Sources
          │
          ▼
    ┌──────────────────────┐
    │   BRONZE LAYER       │  ← Raw Data Ingestion
    │  • No transformation  │
    │  • Original format    │
    │  • Full history       │
    └──────────┬───────────┘
               │
               │ BronzeToSilverTransformer
               │ • Remove duplicates
               │ • Handle nulls
               │ • Type conversion
               │ • Quality flags
               ▼
    ┌──────────────────────┐
    │   SILVER LAYER       │  ← Cleaned & Validated
    │  • Deduplicated      │
    │  • Validated         │
    │  • Typed correctly   │
    │  • Quality flags     │
    └──────────┬───────────┘
               │
               │ SilverToGoldTransformer
               │ • Aggregations
               │ • Business logic
               │ • Derived metrics
               │ • Time windows
               ▼
    ┌──────────────────────┐
    │   GOLD LAYER         │  ← Business Ready
    │  • Aggregated        │
    │  • Business metrics  │
    │  • Analytics ready   │
    │  • API exposed       │
    └──────────────────────┘
               │
               ▼
       Analytics & Reports
```

## 🔄 Component Interactions

### Batch Processing Flow

```
CLI/Scheduler
    │
    ├─ Instantiate Components
    │  ├─ Repository (based on execution_mode)
    │  ├─ Transformers (based on execution_mode)
    │  └─ Pipeline
    │
    ├─ Create BatchRunner
    │  ├─ Generate batch_id
    │  ├─ Start timing
    │  └─ Log start
    │
    └─ Execute Pipeline
       │
       ├─ Read Bronze (Repository)
       │  └─ Load raw data
       │
       ├─ Transform to Silver (Transformer)
       │  └─ Clean & validate
       │
       ├─ Write Silver (Repository)
       │  ├─ Save data
       │  └─ Save metadata
       │
       ├─ Transform to Gold (Transformer)
       │  └─ Aggregate & compute
       │
       ├─ Write Gold (Repository)
       │  ├─ Save data
       │  └─ Save metadata
       │
       └─ Return Metrics
          ├─ Records processed
          ├─ Duration
          └─ Success rate
```

### API Request Flow

```
HTTP Request
    │
    ├─ FastAPI Router
    │  └─ Route matching
    │
    ├─ Dependency Injection
    │  ├─ get_repository()
    │  │  └─ Returns correct repo for execution_mode
    │  └─ get_transformers()
    │     └─ Returns correct transformers
    │
    ├─ Route Handler
    │  ├─ /health → Check repository.health_check()
    │  ├─ /metrics → Read gold, calculate stats
    │  └─ /gold → Query gold layer
    │
    └─ Response
       └─ JSON serialization
```

## 🔌 Execution Modes

### Local Mode (Pandas)
```
Settings: execution_mode=local
    │
    ├─ PandasRepository
    │  ├─ Reads: Parquet files
    │  ├─ Writes: Parquet files
    │  └─ Storage: Local filesystem
    │
    └─ Pandas Transformers
       ├─ PandasBronzeToSilverTransformer
       └─ PandasSilverToGoldTransformer
```

### Databricks Mode (Spark)
```
Settings: execution_mode=databricks
    │
    ├─ SparkRepository
    │  ├─ Reads: Delta Lake
    │  ├─ Writes: Delta Lake
    │  └─ Storage: Cloud storage (S3/ADLS/GCS)
    │
    └─ Spark Transformers
       ├─ SparkBronzeToSilverTransformer
       └─ SparkSilverToGoldTransformer
```

## 📊 Data Model

### BatchMetadata
```python
{
    "batch_id": "20260220_143022",
    "source": "cli",
    "ingestion_time": "2026-02-20T14:30:22Z",
    "record_count": 1000,
    "checksum": "abc123...",
    "layer": "silver"
}
```

### PipelineMetrics
```python
{
    "records_in": 1000,
    "records_out": 950,
    "duration_seconds": 12.5,
    "errors": 0,
    "success_rate": 95.0,
    "throughput": 80.0
}
```

## 🔐 Security Considerations

### Authentication & Authorization
- API: Add OAuth2/JWT authentication
- Database: Use connection pooling with credentials management
- Cloud: Use IAM roles/service principals

### Data Protection
- Encryption at rest (storage layer)
- Encryption in transit (TLS/SSL)
- PII masking in transformers
- Audit logging

## 📈 Scalability Strategy

### Vertical Scaling
- Increase container resources (CPU/memory)
- Use larger database instances
- Optimize query performance

### Horizontal Scaling
- Multiple API instances behind load balancer
- Distributed processing with Spark
- Partitioned storage (date/entity)
- Parallel batch processing

## 🔍 Monitoring Strategy

### Application Metrics
- Pipeline execution time
- Records processed per batch
- Error rates
- API response times

### Infrastructure Metrics
- CPU/Memory usage
- Storage utilization
- Database connections
- Network throughput

### Business Metrics
- Data quality scores
- Processing latency
- Data freshness
- Coverage metrics

## 🚨 Error Handling

### Retry Strategy
```
┌─────────────┐
│   Attempt   │
└──────┬──────┘
       │
   Failed? ──No──> Success
       │
      Yes
       │
   Retry < Max? ──No──> Log & Alert
       │
      Yes
       │
   Wait (backoff)
       │
       └──> Retry
```

### Circuit Breaker Pattern
- Detect repeated failures
- Open circuit (stop attempts)
- Allow recovery period
- Half-open state for testing
- Close when stable

## 🔄 CI/CD Pipeline

```
Code Push
    │
    ├─ Linting (ruff)
    ├─ Type Checking (mypy)
    ├─ Unit Tests (pytest)
    ├─ Integration Tests
    ├─ Coverage Check
    │
    ├─ Build Docker Image
    │
    ├─ Security Scan
    │
    └─ Deploy
       ├─ Dev → Automatic
       ├─ Staging → Manual approval
       └─ Prod → Manual approval + smoke tests
```

## 📝 Configuration Management

```
Environment Variables (.env)
    │
    ├─ Development
    │  ├─ execution_mode=local
    │  ├─ log_level=DEBUG
    │  └─ storage_path=./data
    │
    ├─ Staging
    │  ├─ execution_mode=databricks
    │  ├─ log_level=INFO
    │  └─ storage_path=/mnt/staging-data
    │
    └─ Production
       ├─ execution_mode=databricks
       ├─ log_level=WARNING
       └─ storage_path=/mnt/prod-data
```

## 🎓 Extension Points

### Adding New Data Sources
1. Implement new Repository class
2. Extend BaseRepository interface
3. Update dependency injection
4. No changes to domain/application layers needed

### Adding New Transformations
1. Create new transformer classes
2. Implement transform() method
3. Keep logic pure (no I/O)
4. Inject into Pipeline

### Adding New API Endpoints
1. Define schemas in api/schemas.py
2. Add routes in api/routes.py
3. Keep handlers thin
4. Delegate to application layer

### Adding Streaming Support
1. Implement StreamingRunner fully
2. Add streaming data sources
3. Configure checkpointing
4. Add window operations in transformers
