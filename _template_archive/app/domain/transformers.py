"""Domain transformers - pure, stateless transformation logic."""

from abc import ABC, abstractmethod
from typing import Any, Protocol


class DataFrame(Protocol):
    """Protocol for DataFrame-like objects (pandas.DataFrame or pyspark.sql.DataFrame)."""

    pass


class BronzeToSilverTransformer(ABC):
    """Abstract transformer for Bronze -> Silver layer."""

    @abstractmethod
    def transform(self, df: DataFrame) -> DataFrame:
        """
        Transform bronze data to silver.

        Args:
            df: Raw bronze data

        Returns:
            Cleaned and validated silver data
        """
        pass


class SilverToGoldTransformer(ABC):
    """Abstract transformer for Silver -> Gold layer."""

    @abstractmethod
    def transform(self, df: DataFrame) -> DataFrame:
        """
        Transform silver data to gold.

        Args:
            df: Cleaned silver data

        Returns:
            Aggregated gold data
        """
        pass


class PandasBronzeToSilverTransformer(BronzeToSilverTransformer):
    """Pandas implementation of Bronze -> Silver transformation."""

    def transform(self, df: Any) -> Any:
        """
        Clean and validate bronze data using pandas.

        Transformations:
        - Remove duplicates
        - Handle missing values
        - Enforce data types
        - Add quality flags
        """
        import pandas as pd

        # Remove duplicates
        df = df.drop_duplicates()

        # Handle missing values in critical columns
        if "timestamp" in df.columns:
            df = df.dropna(subset=["timestamp"])

        if "entity_id" in df.columns:
            df = df.dropna(subset=["entity_id"])

        # Convert timestamp to datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"])

        # Convert value to numeric
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df["value_is_valid"] = df["value"].notna()

        # Add processing timestamp
        df["processed_at"] = pd.Timestamp.now()

        return df


class PandasSilverToGoldTransformer(SilverToGoldTransformer):
    """Pandas implementation of Silver -> Gold transformation."""

    def transform(self, df: Any) -> Any:
        """
        Aggregate silver data to business metrics using pandas.

        Transformations:
        - Group by entity and time period
        - Calculate aggregations (sum, avg, count)
        - Compute derived metrics
        """
        import pandas as pd

        # Ensure timestamp is datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Create time-based aggregations
        if "timestamp" in df.columns and "entity_id" in df.columns and "value" in df.columns:
            # Add date column for grouping
            df["date"] = df["timestamp"].dt.date

            # Aggregate by entity and date
            gold = (
                df.groupby(["entity_id", "date"])
                .agg(
                    total_value=("value", "sum"),
                    avg_value=("value", "mean"),
                    min_value=("value", "min"),
                    max_value=("value", "max"),
                    record_count=("value", "count"),
                )
                .reset_index()
            )

            # Add computed metrics
            gold["value_range"] = gold["max_value"] - gold["min_value"]
            gold["aggregated_at"] = pd.Timestamp.now()

            return gold

        # If columns don't match expected schema, return as-is
        return df


class SparkBronzeToSilverTransformer(BronzeToSilverTransformer):
    """Spark implementation of Bronze -> Silver transformation."""

    def transform(self, df: Any) -> Any:
        """
        Clean and validate bronze data using PySpark.

        Transformations:
        - Remove duplicates
        - Handle missing values
        - Enforce data types
        - Add quality flags
        """
        from pyspark.sql import functions as F

        # Remove duplicates
        df = df.dropDuplicates()

        # Handle missing values in critical columns
        if "timestamp" in df.columns:
            df = df.filter(F.col("timestamp").isNotNull())

        if "entity_id" in df.columns:
            df = df.filter(F.col("entity_id").isNotNull())

        # Convert timestamp to proper type
        if "timestamp" in df.columns:
            df = df.withColumn("timestamp", F.to_timestamp(F.col("timestamp")))
            df = df.filter(F.col("timestamp").isNotNull())

        # Convert value to numeric and add validation flag
        if "value" in df.columns:
            df = df.withColumn("value", F.col("value").cast("double"))
            df = df.withColumn("value_is_valid", F.col("value").isNotNull())

        # Add processing timestamp
        df = df.withColumn("processed_at", F.current_timestamp())

        return df


class SparkSilverToGoldTransformer(SilverToGoldTransformer):
    """Spark implementation of Silver -> Gold transformation."""

    def transform(self, df: Any) -> Any:
        """
        Aggregate silver data to business metrics using PySpark.

        Transformations:
        - Group by entity and time period
        - Calculate aggregations (sum, avg, count)
        - Compute derived metrics
        """
        from pyspark.sql import functions as F

        # Ensure timestamp is proper type
        if "timestamp" in df.columns:
            df = df.withColumn("timestamp", F.to_timestamp(F.col("timestamp")))

        # Create time-based aggregations
        if "timestamp" in df.columns and "entity_id" in df.columns and "value" in df.columns:
            # Add date column for grouping
            df = df.withColumn("date", F.to_date(F.col("timestamp")))

            # Aggregate by entity and date
            gold = df.groupBy("entity_id", "date").agg(
                F.sum("value").alias("total_value"),
                F.avg("value").alias("avg_value"),
                F.min("value").alias("min_value"),
                F.max("value").alias("max_value"),
                F.count("value").alias("record_count"),
            )

            # Add computed metrics
            gold = gold.withColumn("value_range", F.col("max_value") - F.col("min_value"))
            gold = gold.withColumn("aggregated_at", F.current_timestamp())

            return gold

        # If columns don't match expected schema, return as-is
        return df
