"""CLI entrypoint for orchestration."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import typer

from app.application.pipeline import Pipeline
from app.application.runner import BatchRunner, StreamingRunner
from app.domain.transformers import (
    PandasBronzeToSilverTransformer,
    PandasSilverToGoldTransformer,
    SparkBronzeToSilverTransformer,
    SparkSilverToGoldTransformer,
)
from app.infrastructure.logging import get_logger, setup_logging
from app.infrastructure.repositories.pandas_repository import PandasRepository
from app.infrastructure.repositories.spark_repository import SparkRepository
from app.infrastructure.settings import get_settings

# Create Typer app
app = typer.Typer(
    name="energy-platform",
    help="Energy Data Platform - Medallion Architecture Data Pipeline",
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


@app.command()
def run_batch(
    source: str = typer.Option("cli", help="Data source identifier"),
    generate_sample: bool = typer.Option(False, help="Generate sample bronze data"),
) -> None:
    """
    Run batch processing pipeline.

    Executes the full medallion architecture flow:
    Bronze -> Silver -> Gold
    """
    settings = get_settings()
    
    logger.info(
        "cli_batch_started",
        execution_mode=settings.execution_mode,
        processing_mode=settings.processing_mode,
        source=source,
    )

    # Generate sample data if requested
    if generate_sample:
        _generate_sample_bronze_data(settings)
        logger.info("sample_data_generated")

    # Instantiate components based on execution mode
    if settings.execution_mode == "local":
        repository = PandasRepository(settings)
        bronze_to_silver = PandasBronzeToSilverTransformer()
        silver_to_gold = PandasSilverToGoldTransformer()
    elif settings.execution_mode == "databricks":
        repository = SparkRepository(settings)
        bronze_to_silver = SparkBronzeToSilverTransformer()
        silver_to_gold = SparkSilverToGoldTransformer()
    else:
        logger.error("invalid_execution_mode", mode=settings.execution_mode)
        raise typer.BadParameter(f"Unknown execution mode: {settings.execution_mode}")

    # Create pipeline and runner
    pipeline = Pipeline(
        repository=repository,
        bronze_to_silver=bronze_to_silver,
        silver_to_gold=silver_to_gold,
    )
    
    runner = BatchRunner(
        pipeline=pipeline,
        repository=repository,
        source=source,
    )

    # Execute pipeline
    try:
        metrics = runner.run()
        
        logger.info(
            "cli_batch_completed",
            metrics=metrics.to_dict(),
        )
        
        typer.echo(f"✅ Batch processing completed successfully!")
        typer.echo(f"📊 Records In: {metrics.records_in}")
        typer.echo(f"📊 Records Out: {metrics.records_out}")
        typer.echo(f"⏱️  Duration: {metrics.duration_seconds:.2f}s")
        typer.echo(f"📈 Success Rate: {metrics.success_rate:.1f}%")
        
    except Exception as e:
        logger.error("cli_batch_failed", error=str(e), exc_info=True)
        typer.echo(f"❌ Batch processing failed: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def run_stream(
    source: str = typer.Option("cli", help="Data source identifier"),
) -> None:
    """
    Run streaming processing pipeline (scaffold only).

    This command is scaffolded but not fully implemented.
    Extend StreamingRunner to integrate with your streaming platform.
    """
    settings = get_settings()
    
    logger.info(
        "cli_stream_started",
        execution_mode=settings.execution_mode,
        processing_mode="stream",
        source=source,
    )

    # Instantiate components
    if settings.execution_mode == "local":
        repository = PandasRepository(settings)
        bronze_to_silver = PandasBronzeToSilverTransformer()
        silver_to_gold = PandasSilverToGoldTransformer()
    elif settings.execution_mode == "databricks":
        repository = SparkRepository(settings)
        bronze_to_silver = SparkBronzeToSilverTransformer()
        silver_to_gold = SparkSilverToGoldTransformer()
    else:
        raise typer.BadParameter(f"Unknown execution mode: {settings.execution_mode}")

    # Create pipeline and runner
    pipeline = Pipeline(
        repository=repository,
        bronze_to_silver=bronze_to_silver,
        silver_to_gold=silver_to_gold,
    )
    
    runner = StreamingRunner(
        pipeline=pipeline,
        repository=repository,
        source=source,
    )

    # Execute pipeline
    try:
        runner.run()
    except NotImplementedError as e:
        logger.warning("streaming_not_implemented", message=str(e))
        typer.echo(f"⚠️  {str(e)}")
        typer.echo("💡 Extend StreamingRunner to add streaming functionality")
        raise typer.Exit(code=0)
    except Exception as e:
        logger.error("cli_stream_failed", error=str(e), exc_info=True)
        typer.echo(f"❌ Streaming processing failed: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def health() -> None:
    """Check system health."""
    settings = get_settings()
    
    typer.echo("🏥 Checking system health...")
    
    # Check repository
    if settings.execution_mode == "local":
        repository = PandasRepository(settings)
    else:
        repository = SparkRepository(settings)
    
    storage_ok = repository.health_check()
    
    if storage_ok:
        typer.echo("✅ Storage: Healthy")
    else:
        typer.echo("❌ Storage: Unhealthy")
    
    if storage_ok:
        typer.echo("\n✅ System is healthy")
    else:
        typer.echo("\n❌ System is unhealthy")
        raise typer.Exit(code=1)


def _generate_sample_bronze_data(settings) -> None:
    """Generate sample bronze data for testing."""
    import numpy as np
    
    # Create sample data
    dates = pd.date_range(start="2026-02-01", end="2026-02-20", freq="h")
    entities = ["entity_1", "entity_2", "entity_3"]
    
    records = []
    for date in dates:
        for entity in entities:
            records.append({
                "timestamp": date,
                "entity_id": entity,
                "value": float(np.random.uniform(10, 100)),
            })
    
    df = pd.DataFrame(records)
    
    # Ensure bronze directory exists
    bronze_path = Path(settings.bronze_full_path)
    bronze_path.mkdir(parents=True, exist_ok=True)
    
    # Write to bronze layer
    output_file = bronze_path / "sample_data.parquet"
    df.to_parquet(output_file, index=False)
    
    typer.echo(f"📝 Generated {len(df)} sample records in bronze layer")


if __name__ == "__main__":
    app()
