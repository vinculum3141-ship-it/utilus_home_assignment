"""Test transformers - domain layer unit tests."""

import pandas as pd
import pytest

from app.domain.transformers import (
    PandasBronzeToSilverTransformer,
    PandasSilverToGoldTransformer,
)


class TestPandasBronzeToSilverTransformer:
    """Test bronze to silver transformation."""

    def test_removes_duplicates(self):
        """Test that duplicate records are removed."""
        transformer = PandasBronzeToSilverTransformer()
        
        # Create data with duplicates
        df = pd.DataFrame({
            "timestamp": ["2026-02-20 10:00:00", "2026-02-20 10:00:00", "2026-02-20 11:00:00"],
            "entity_id": ["entity_1", "entity_1", "entity_2"],
            "value": [100.0, 100.0, 200.0],
        })
        
        result = transformer.transform(df)
        
        # Should have 2 records (one duplicate removed)
        assert len(result) == 2

    def test_handles_missing_timestamps(self):
        """Test that records with missing timestamps are dropped."""
        transformer = PandasBronzeToSilverTransformer()
        
        df = pd.DataFrame({
            "timestamp": ["2026-02-20 10:00:00", None, "2026-02-20 11:00:00"],
            "entity_id": ["entity_1", "entity_2", "entity_3"],
            "value": [100.0, 200.0, 300.0],
        })
        
        result = transformer.transform(df)
        
        # Should have 2 records (null timestamp dropped)
        assert len(result) == 2
        assert result["timestamp"].notna().all()

    def test_adds_quality_flags(self):
        """Test that quality flags are added."""
        transformer = PandasBronzeToSilverTransformer()
        
        df = pd.DataFrame({
            "timestamp": ["2026-02-20 10:00:00", "2026-02-20 11:00:00"],
            "entity_id": ["entity_1", "entity_2"],
            "value": [100.0, "invalid"],
        })
        
        result = transformer.transform(df)
        
        assert "value_is_valid" in result.columns
        assert "processed_at" in result.columns


class TestPandasSilverToGoldTransformer:
    """Test silver to gold transformation."""

    def test_aggregates_by_entity_and_date(self):
        """Test that data is aggregated correctly."""
        transformer = PandasSilverToGoldTransformer()
        
        df = pd.DataFrame({
            "timestamp": pd.to_datetime([
                "2026-02-20 10:00:00",
                "2026-02-20 11:00:00",
                "2026-02-20 12:00:00",
            ]),
            "entity_id": ["entity_1", "entity_1", "entity_2"],
            "value": [100.0, 200.0, 300.0],
        })
        
        result = transformer.transform(df)
        
        # Should have 2 aggregated records (one per entity)
        assert len(result) == 2
        assert "total_value" in result.columns
        assert "avg_value" in result.columns
        assert "record_count" in result.columns

    def test_computes_derived_metrics(self):
        """Test that derived metrics are computed."""
        transformer = PandasSilverToGoldTransformer()
        
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2026-02-20 10:00:00", "2026-02-20 11:00:00"]),
            "entity_id": ["entity_1", "entity_1"],
            "value": [100.0, 200.0],
        })
        
        result = transformer.transform(df)
        
        assert "value_range" in result.columns
        assert "aggregated_at" in result.columns
        assert result["value_range"].iloc[0] == 100.0  # 200 - 100

    def test_handles_empty_dataframe(self):
        """Test that empty DataFrame is handled gracefully."""
        transformer = PandasSilverToGoldTransformer()
        
        df = pd.DataFrame({
            "timestamp": [],
            "entity_id": [],
            "value": [],
        })
        
        result = transformer.transform(df)
        
        # Should return empty DataFrame but with expected columns
        assert len(result) == 0
