"""Domain exceptions - production error hierarchy."""


class EnergyPlatformError(Exception):
    """Base exception for all platform errors.
    
    Use this for catching all platform-specific errors at boundaries
    (API error handlers, CLI error handling, etc.)
    """

    pass


class DomainError(EnergyPlatformError):
    """Domain layer errors - business logic violations.
    
    Raised when:
    - Business rule violations
    - Invalid state transitions
    - Domain constraint violations
    
    Maps to: HTTP 422 Unprocessable Entity
    """

    pass


class ValidationError(DomainError):
    """Data validation failed.
    
    Raised when:
    - Schema validation fails
    - Data type mismatches
    - Value out of acceptable range
    - Required field missing
    
    Maps to: HTTP 400 Bad Request
    """

    pass


class TransformationError(DomainError):
    """Transformation logic failed.
    
    Raised when:
    - Transformer cannot process data
    - Aggregation logic fails
    - Data enrichment fails
    
    Maps to: HTTP 422 Unprocessable Entity
    """

    pass


class RepositoryError(EnergyPlatformError):
    """Infrastructure layer errors - storage failures.
    
    Raised when:
    - Cannot connect to storage
    - Write/read operations fail
    - Storage quota exceeded
    - Permission denied
    
    Maps to: HTTP 503 Service Unavailable
    Retry: Yes (with backoff)
    """

    pass


class StorageUnavailableError(RepositoryError):
    """Storage system is unavailable.
    
    Raised when:
    - Database connection fails
    - File system unmounted
    - S3/Azure Storage unreachable
    
    Maps to: HTTP 503 Service Unavailable
    Circuit Breaker: Open on repeated failures
    """

    pass


class DataIntegrityError(RepositoryError):
    """Data integrity violation.
    
    Raised when:
    - Checksum mismatch
    - Duplicate data detected
    - Corrupted data
    
    Maps to: HTTP 409 Conflict
    Retry: No (data issue, not transient)
    """

    pass


class PipelineExecutionError(EnergyPlatformError):
    """Application layer errors - orchestration failures.
    
    Raised when:
    - Pipeline stage fails
    - Metadata generation fails
    - Batch processing fails
    
    Maps to: HTTP 500 Internal Server Error
    """

    pass


class ConfigurationError(EnergyPlatformError):
    """Configuration errors - setup issues.
    
    Raised when:
    - Invalid configuration
    - Missing required settings
    - Environment variable not set
    
    Maps to: HTTP 500 Internal Server Error
    Retry: No (configuration issue)
    """

    pass
