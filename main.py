"""
SaaS Analytics CLI Tool

Calculates MRR, churn, and cohort retention from customer and subscription CSV files.
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
    customers_file: Path = typer.Argument(
        ..., help="Path to customers.csv", exists=True
    ),
    subscriptions_file: Path = typer.Argument(
        ..., help="Path to subscriptions.csv", exists=True
    ),
    output_file: Path = typer.Argument(..., help="Path to output JSON file"),
) -> None:
    """
    Calculate SaaS metrics from CSV files.

    Reads customer and subscription data, validates inputs, and generates
    a JSON report with MRR, churn, and cohort retention metrics.
    """
    console.print("\n[bold blue]🚀 SaaS Analytics Tool[/bold blue]\n")

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
                f"\n[yellow]⚠️  Found {len(all_warnings)} data quality issues:[/yellow]"
            )
            for warning in all_warnings[:10]:  # Show first 10
                console.print(f"  • {warning}")
            if len(all_warnings) > 10:
                console.print(
                    f"  • ... and {len(all_warnings) - 10} more (see output file)"
                )

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

    except DataQualityError as e:
        console.print(f"[bold red]❌ Data quality error: {e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
