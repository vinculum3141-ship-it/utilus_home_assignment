"""Pipeline orchestration - medallion architecture flow."""

from typing import Any

from app.domain.transformers import BronzeToSilverTransformer, SilverToGoldTransformer
from app.infrastructure.repositories.base import BaseRepository


class Pipeline:
    """Orchestrates the medallion architecture data flow."""

    def __init__(
        self,
        repository: BaseRepository,
        bronze_to_silver: BronzeToSilverTransformer,
        silver_to_gold: SilverToGoldTransformer,
    ):
        """
        Initialize pipeline.

        Args:
            repository: Data repository
            bronze_to_silver: Bronze to Silver transformer
            silver_to_gold: Silver to Gold transformer
        """
        self.repository = repository
        self.bronze_to_silver = bronze_to_silver
        self.silver_to_gold = silver_to_gold

    def run_batch(self) -> tuple[Any, Any, int, int]:
        """
        Run batch processing through medallion layers.

        Returns:
            Tuple of (silver_df, gold_df, silver_count, gold_count)
        """
        # Bronze -> Silver
        bronze_df = self.repository.read_bronze()
        silver_df = self.bronze_to_silver.transform(bronze_df)
        
        # Get count based on DataFrame type
        if hasattr(silver_df, "__len__"):  # pandas
            silver_count = len(silver_df)
        else:  # Spark
            silver_count = silver_df.count()

        # Silver -> Gold
        gold_df = self.silver_to_gold.transform(silver_df)
        
        # Get count based on DataFrame type
        if hasattr(gold_df, "__len__"):  # pandas
            gold_count = len(gold_df)
        else:  # Spark
            gold_count = gold_df.count()

        return silver_df, gold_df, silver_count, gold_count
