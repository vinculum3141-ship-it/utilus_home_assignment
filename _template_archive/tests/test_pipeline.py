"""Test pipeline - application layer tests with mocks."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.application.pipeline import Pipeline
from app.domain.transformers import (
    PandasBronzeToSilverTransformer,
    PandasSilverToGoldTransformer,
)


class TestPipeline:
    """Test pipeline orchestration."""

    def test_runs_full_medallion_flow(self):
        """Test that pipeline executes complete Bronze -> Silver -> Gold flow."""
        # Create mock repository
        mock_repository = MagicMock()
        
        # Setup bronze data
        bronze_df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2026-02-20 10:00:00", "2026-02-20 11:00:00"]),
            "entity_id": ["entity_1", "entity_2"],
            "value": [100.0, 200.0],
        })
        mock_repository.read_bronze.return_value = bronze_df
        
        # Create pipeline
        pipeline = Pipeline(
            repository=mock_repository,
            bronze_to_silver=PandasBronzeToSilverTransformer(),
            silver_to_gold=PandasSilverToGoldTransformer(),
        )
        
        # Run pipeline
        silver_df, gold_df, silver_count, gold_count = pipeline.run_batch()
        
        # Verify bronze was read
        mock_repository.read_bronze.assert_called_once()
        
        # Verify transformations produced data
        assert len(silver_df) > 0
        assert len(gold_df) > 0
        assert silver_count == len(silver_df)
        assert gold_count == len(gold_df)

    def test_handles_empty_bronze_data(self):
        """Test that pipeline handles empty bronze data gracefully."""
        mock_repository = MagicMock()
        
        # Setup empty bronze data
        bronze_df = pd.DataFrame({
            "timestamp": [],
            "entity_id": [],
            "value": [],
        })
        mock_repository.read_bronze.return_value = bronze_df
        
        # Create pipeline
        pipeline = Pipeline(
            repository=mock_repository,
            bronze_to_silver=PandasBronzeToSilverTransformer(),
            silver_to_gold=PandasSilverToGoldTransformer(),
        )
        
        # Run pipeline
        silver_df, gold_df, silver_count, gold_count = pipeline.run_batch()
        
        # Should complete without errors
        assert silver_count == 0
        assert gold_count == 0

    def test_uses_correct_transformers(self):
        """Test that pipeline uses the provided transformers."""
        mock_repository = MagicMock()
        mock_bronze_to_silver = MagicMock()
        mock_silver_to_gold = MagicMock()
        
        # Setup mock transformers
        bronze_df = pd.DataFrame({"col": [1, 2, 3]})
        silver_df = pd.DataFrame({"col": [1, 2]})
        gold_df = pd.DataFrame({"col": [1]})
        
        mock_repository.read_bronze.return_value = bronze_df
        mock_bronze_to_silver.transform.return_value = silver_df
        mock_silver_to_gold.transform.return_value = gold_df
        
        # Create pipeline with mock transformers
        pipeline = Pipeline(
            repository=mock_repository,
            bronze_to_silver=mock_bronze_to_silver,
            silver_to_gold=mock_silver_to_gold,
        )
        
        # Run pipeline
        result_silver, result_gold, _, _ = pipeline.run_batch()
        
        # Verify transformers were called correctly
        mock_bronze_to_silver.transform.assert_called_once()
        mock_silver_to_gold.transform.assert_called_once()
        
        # Verify correct data was returned
        assert len(result_silver) == 2
        assert len(result_gold) == 1
