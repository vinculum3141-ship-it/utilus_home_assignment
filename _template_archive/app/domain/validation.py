"""Domain validation logic - pure validation functions."""

from typing import Any

from app.domain.models import ValidationResult


def validate_bronze_schema(df: Any) -> ValidationResult:
    """
    Validate bronze layer data schema.

    Args:
        df: DataFrame to validate

    Returns:
        ValidationResult with validation outcome
    """
    errors = []
    warnings = []
    records_failed = 0

    try:
        # Check for required columns
        required_columns = ["timestamp", "entity_id", "value"]
        
        if hasattr(df, "columns"):  # pandas
            actual_columns = set(df.columns)
            missing = set(required_columns) - actual_columns
            
            if missing:
                errors.append(f"Missing required columns: {missing}")
            
            # Check for empty dataframe
            if len(df) == 0:
                warnings.append("DataFrame is empty")
            
            # Check for null values in critical columns
            for col in required_columns:
                if col in df.columns:
                    null_count = df[col].isna().sum()
                    if null_count > 0:
                        warnings.append(f"Column '{col}' has {null_count} null values")
                        records_failed += null_count
            
            records_validated = len(df)
        
        else:  # Assume Spark DataFrame
            actual_columns = set(df.columns)
            missing = set(required_columns) - actual_columns
            
            if missing:
                errors.append(f"Missing required columns: {missing}")
            
            # Check for empty dataframe
            count = df.count()
            if count == 0:
                warnings.append("DataFrame is empty")
            
            records_validated = count

    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        records_validated = 0

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        records_validated=records_validated,
        records_failed=records_failed,
    )


def validate_silver_quality(df: Any) -> ValidationResult:
    """
    Validate silver layer data quality.

    Args:
        df: DataFrame to validate

    Returns:
        ValidationResult with validation outcome
    """
    errors = []
    warnings = []
    records_failed = 0

    try:
        if hasattr(df, "columns"):  # pandas
            records_validated = len(df)
            
            # Check for duplicates
            if "entity_id" in df.columns and "timestamp" in df.columns:
                duplicates = df.duplicated(subset=["entity_id", "timestamp"]).sum()
                if duplicates > 0:
                    errors.append(f"Found {duplicates} duplicate records")
                    records_failed += duplicates
            
            # Check data quality flags if present
            if "value_is_valid" in df.columns:
                invalid_count = (~df["value_is_valid"]).sum()
                if invalid_count > 0:
                    warnings.append(f"Found {invalid_count} records with invalid values")
        
        else:  # Spark
            records_validated = df.count()
            
            # Check for duplicates
            if "entity_id" in df.columns and "timestamp" in df.columns:
                distinct_count = df.select("entity_id", "timestamp").distinct().count()
                duplicates = records_validated - distinct_count
                if duplicates > 0:
                    errors.append(f"Found {duplicates} duplicate records")
                    records_failed += duplicates

    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        records_validated = 0

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        records_validated=records_validated,
        records_failed=records_failed,
    )
