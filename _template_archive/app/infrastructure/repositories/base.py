"""Base repository interface."""

from abc import ABC, abstractmethod
from typing import Any

from app.domain.models import BatchMetadata


class BaseRepository(ABC):
    """Abstract base repository for data operations."""

    @abstractmethod
    def read_bronze(self) -> Any:
        """
        Read data from bronze layer.

        Returns:
            DataFrame with bronze data
        """
        pass

    @abstractmethod
    def write_silver(self, df: Any, metadata: BatchMetadata) -> None:
        """
        Write data to silver layer.

        Args:
            df: DataFrame to write
            metadata: Batch metadata
        """
        pass

    @abstractmethod
    def read_silver(self) -> Any:
        """
        Read data from silver layer.

        Returns:
            DataFrame with silver data
        """
        pass

    @abstractmethod
    def write_gold(self, df: Any, metadata: BatchMetadata) -> None:
        """
        Write data to gold layer.

        Args:
            df: DataFrame to write
            metadata: Batch metadata
        """
        pass

    @abstractmethod
    def read_gold(self) -> Any:
        """
        Read data from gold layer.

        Returns:
            DataFrame with gold data
        """
        pass

    @abstractmethod
    def save_metadata(self, metadata: BatchMetadata) -> None:
        """
        Save batch metadata.

        Args:
            metadata: Batch metadata to save
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if repository is accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass
