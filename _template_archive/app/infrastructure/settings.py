"""Application settings using Pydantic BaseSettings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Execution configuration
    execution_mode: Literal["local", "databricks"] = Field(
        default="local", description="Execution engine mode"
    )
    processing_mode: Literal["batch", "stream"] = Field(
        default="batch", description="Processing mode"
    )

    # Storage configuration
    storage_path: str = Field(default="./data", description="Base storage path")
    bronze_path: str = Field(default="bronze", description="Bronze layer relative path")
    silver_path: str = Field(default="silver", description="Silver layer relative path")
    gold_path: str = Field(default="gold", description="Gold layer relative path")
    metadata_path: str = Field(default="metadata", description="Metadata storage path")

    # Database configuration
    database_url: str = Field(
        default="sqlite:///./energy_platform.db", description="Database connection URL"
    )

    # API configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=False, description="API auto-reload")

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: Literal["json", "text"] = Field(default="json", description="Log format")

    # Databricks configuration (optional)
    databricks_host: str = Field(default="", description="Databricks workspace URL")
    databricks_token: str = Field(default="", description="Databricks access token")
    databricks_cluster_id: str = Field(default="", description="Databricks cluster ID")

    # Processing configuration
    batch_size: int = Field(default=1000, description="Batch processing size")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, description="Retry delay in seconds")

    @property
    def bronze_full_path(self) -> str:
        """Get full bronze layer path."""
        return f"{self.storage_path}/{self.bronze_path}"

    @property
    def silver_full_path(self) -> str:
        """Get full silver layer path."""
        return f"{self.storage_path}/{self.silver_path}"

    @property
    def gold_full_path(self) -> str:
        """Get full gold layer path."""
        return f"{self.storage_path}/{self.gold_path}"

    @property
    def metadata_full_path(self) -> str:
        """Get full metadata path."""
        return f"{self.storage_path}/{self.metadata_path}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
