"""
SaaS Analytics CLI Tool

Calculates MRR, churn, and cohort retention from customer and subscription CSV files.

Medallion Architecture:
- Bronze: Raw data from assignment folder
- Silver: Cleaned and validated data
- Gold: Aggregated metrics and analytics
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from loader import DataQualityError, load_customers, load_subscriptions
from metrics import (
    calculate_cohort_retention,
    calculate_monthly_churn,
    calculate_monthly_mrr,
    detect_overlapping_subscriptions,
)
from models import AnalyticsReport
from src.transformers.clean_subscriptions import clean_subscriptions_bronze_to_silver
from src.transformers.clean_customers import clean_customers_bronze_to_silver

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="SaaS Analytics Tool")
console = Console()


@app.command()
def main(
    customers_file: Path = typer.Option(
        "data/silver/customers_silver.csv",
        help="Path to customers CSV (silver layer)",
    ),
    subscriptions_file: Path = typer.Option(
        "data/silver/subscriptions_silver.csv",
        help="Path to subscriptions CSV (silver layer)",
    ),
    output_file: Path = typer.Option(
        "output/report.json",
        help="Path to output JSON file",
    ),
    skip_preprocessing: bool = typer.Option(
        False,
        help="Skip bronze to silver preprocessing (use if silver data already exists)",
    ),
) -> None:
    """
    Calculate SaaS metrics from CSV files.
    
    By default, runs bronze→silver preprocessing first, then calculates metrics.
    """
    console.print("[bold blue]SaaS Analytics Tool[/bold blue]")
    
    # Step 1: Preprocessing (bronze → silver)
    if not skip_preprocessing:
        console.print("\n[bold cyan]Step 1: Data Preprocessing (Bronze → Silver)[/bold cyan]")
        bronze_subs = Path("data/bronze/subscriptions.csv")
        bronze_customers = Path("data/bronze/customers.csv")
        silver_subs = Path("data/silver/subscriptions_silver.csv")
        silver_customers = Path("data/silver/customers_silver.csv")
        
        if not bronze_subs.exists() or not bronze_customers.exists():
            console.print(f"[red]Error: Bronze data not found[/red]")
            sys.exit(1)
        
        try:
            # Clean customers FIRST and track removed IDs
            console.print("  • Cleaning customer data...")
            removed_customer_ids = clean_customers_bronze_to_silver(
                bronze_path=bronze_customers,
                silver_path=silver_customers,
            )
            
            if removed_customer_ids:
                console.print(
                    f"\n[bold yellow]⚠️  DATA QUALITY ALERT[/bold yellow]"
                )
                console.print(
                    f"    Removed {len(removed_customer_ids)} invalid customers: "
                    f"{sorted(removed_customer_ids)}"
                )
                console.print(
                    f"    [yellow]→ These customers excluded from all metrics calculations[/yellow]"
                )
            
            # Clean subscriptions and filter out removed customers
            console.print("  • Cleaning subscription data...")
            clean_subscriptions_bronze_to_silver(
                bronze_path=bronze_subs,
                silver_path=silver_subs,
                customers_bronze_path=silver_customers,
                excluded_customer_ids=removed_customer_ids,
            )
            console.print("[green]✓ Data cleaning complete[/green]")
        except ValueError as e:
            console.print(f"[red]Data quality validation failed:[/red]\n{e}")
            sys.exit(1)
    else:
        console.print("\n[yellow]Skipping preprocessing, using existing silver data[/yellow]")
    
    # Step 2: Load data
    console.print("\n[bold cyan]Step 2: Loading Data[/bold cyan]")
    
    if not customers_file.exists():
        console.print(f"[red]Error: File not found: {customers_file}[/red]")
        sys.exit(1)
    
    if not subscriptions_file.exists():
        console.print(f"[red]Error: File not found: {subscriptions_file}[/red]")
        sys.exit(1)

    all_warnings = []

    try:
        # Load customers
        console.print(f"📂 Loading customers from {customers_file}...")
        customers, customer_warnings = load_customers(customers_file)
        all_warnings.extend(customer_warnings)

        if not customers:
            console.print(
                "[bold red]❌ No valid customers found. Cannot proceed.[/bold red]"
            )
            sys.exit(1)

        console.print(f"✅ Loaded {len(customers)} customers")

        # Load subscriptions
        console.print(f"📂 Loading subscriptions from {subscriptions_file}...")
        valid_customer_ids = {c.customer_id for c in customers}
        subscriptions, subscription_warnings = load_subscriptions(
            subscriptions_file, valid_customer_ids
        )
        all_warnings.extend(subscription_warnings)

        if not subscriptions:
            console.print(
                "[bold red]❌ No valid subscriptions found. Cannot proceed.[/bold red]"
            )
            sys.exit(1)

        console.print(f"✅ Loaded {len(subscriptions)} subscriptions")

        # Check for overlapping subscriptions
        overlap_warnings = detect_overlapping_subscriptions(subscriptions)
        all_warnings.extend(overlap_warnings)

        # Display warnings
        if all_warnings:
            console.print(
                f"\n[bold red]⚠️  DATA QUALITY WARNING: Found {len(all_warnings)} issues[/bold red]"
            )
            console.print(
                "[yellow]These issues affect metric accuracy. Fix source data for production use.[/yellow]"
            )
            console.print("\nIssues detected:")
            for warning in all_warnings[:10]:  # Show first 10
                console.print(f"  • {warning}")
            if len(all_warnings) > 10:
                console.print(
                    f"  • ... and {len(all_warnings) - 10} more (see output file)"
                )
            console.print()

        # Calculate metrics
        console.print("\n[bold cyan]📊 Calculating metrics...[/bold cyan]")

        console.print("  • Monthly MRR...")
        mrr_data = calculate_monthly_mrr(subscriptions)

        console.print("  • Monthly churn...")
        churn_data = calculate_monthly_churn(customers, subscriptions)

        console.print("  • Cohort retention...")
        cohort_data = calculate_cohort_retention(customers, subscriptions)

        # Build report
        report = AnalyticsReport(
            metadata={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "input_files": {
                    "customers": str(customers_file),
                    "subscriptions": str(subscriptions_file),
                },
                "data_quality_warnings": all_warnings,
                "summary": {
                    "total_customers": len(customers),
                    "total_subscriptions": len(subscriptions),
                    "warning_count": len(all_warnings),
                },
            },
            monthly_mrr=mrr_data,
            monthly_churn=churn_data,
            cohort_retention=cohort_data,
        )

        # Write output
        console.print(f"\n💾 Writing report to {output_file}...")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(report.model_dump(), f, indent=2)

        console.print(f"[bold green]✅ Report generated successfully![/bold green]")
        console.print(f"\n📈 Summary:")
        console.print(f"  • MRR data points: {len(mrr_data)}")
        console.print(f"  • Churn data points: {len(churn_data)}")
        console.print(f"  • Cohorts analyzed: {len(cohort_data)}")
        
        if all_warnings:
            console.print(
                f"\n[bold yellow]⚠️  REMINDER: {len(all_warnings)} data quality issues detected[/bold yellow]"
            )
            console.print(
                "[yellow]Metrics are calculated on cleaned data only.[/yellow]"
            )
            console.print(
                "[yellow]Fix issues in source data (data/bronze/) for accurate production metrics.[/yellow]"
            )

    except DataQualityError as e:
        console.print(f"[bold red]❌ Data quality error: {e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
