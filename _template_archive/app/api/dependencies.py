"""API dependencies - dependency injection for FastAPI."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.transformers import (
    PandasBronzeToSilverTransformer,
    PandasSilverToGoldTransformer,
    SparkBronzeToSilverTransformer,
    SparkSilverToGoldTransformer,
)
from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.repositories.pandas_repository import PandasRepository
from app.infrastructure.repositories.spark_repository import SparkRepository
from app.infrastructure.settings import get_settings


def get_repository() -> BaseRepository:
    """
    Get repository based on execution mode.

    Returns:
        Repository instance
    """
    settings = get_settings()
    
    if settings.execution_mode == "local":
        return PandasRepository(settings)
    elif settings.execution_mode == "databricks":
        return SparkRepository(settings)
    else:
        raise ValueError(f"Unknown execution mode: {settings.execution_mode}")


def get_transformers() -> tuple:
    """
    Get transformers based on execution mode.

    Returns:
        Tuple of (bronze_to_silver, silver_to_gold) transformers
    """
    settings = get_settings()
    
    if settings.execution_mode == "local":
        return (
            PandasBronzeToSilverTransformer(),
            PandasSilverToGoldTransformer(),
        )
    elif settings.execution_mode == "databricks":
        return (
            SparkBronzeToSilverTransformer(),
            SparkSilverToGoldTransformer(),
        )
    else:
        raise ValueError(f"Unknown execution mode: {settings.execution_mode}")


def get_db_engine():
    """Get database engine."""
    settings = get_settings()
    return create_engine(settings.database_url)


def get_session_maker():
    """Get SQLAlchemy session maker."""
    engine = get_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Yields:
        Database session
    """
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
