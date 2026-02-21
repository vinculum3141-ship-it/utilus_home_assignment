"""Data loading and validation."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from models import Customer, Subscription

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Raised when data quality issues prevent processing."""

    pass


def load_customers(filepath: Path) -> tuple[list[Customer], list[str]]:
    """
    Load and validate customers from CSV.

    Args:
        filepath: Path to customers.csv

    Returns:
        Tuple of (validated customers, warning messages)

    Raises:
        DataQualityError: If required columns are missing or file cannot be read
    """
    warnings = []

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise DataQualityError(f"Failed to read {filepath}: {e}")

    # Validate required columns
    required_cols = {"customer_id", "signup_date", "country"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise DataQualityError(f"Missing required columns in customers.csv: {missing}")

    # Track seen customer IDs for duplicate detection
    seen_ids = set()
    customers = []

    for idx, row in df.iterrows():
        try:
            # Check for duplicates
            if row["customer_id"] in seen_ids:
                warnings.append(
                    f"Duplicate customer_id '{row['customer_id']}' at row {idx+2} - skipping"
                )
                continue

            # Parse and validate
            customer = Customer(
                customer_id=str(row["customer_id"]),
                signup_date=pd.to_datetime(row["signup_date"]).date(),
                country=str(row["country"]) if pd.notna(row["country"]) else "",
            )

            # Warn about missing country
            if not customer.country:
                warnings.append(
                    f"Customer '{customer.customer_id}' has missing country - keeping record"
                )

            customers.append(customer)
            seen_ids.add(customer.customer_id)

        except (ValidationError, ValueError, pd.errors.OutOfBoundsDatetime) as e:
            warnings.append(f"Invalid customer at row {idx+2}: {e} - skipping")
            continue

    logger.info(f"Loaded {len(customers)} customers with {len(warnings)} warnings")
    return customers, warnings


def load_subscriptions(
    filepath: Path, valid_customer_ids: set[str]
) -> tuple[list[Subscription], list[str]]:
    """
    Load and validate subscriptions from CSV.

    Args:
        filepath: Path to subscriptions.csv
        valid_customer_ids: Set of valid customer IDs for reference checking

    Returns:
        Tuple of (validated subscriptions, warning messages)

    Raises:
        DataQualityError: If required columns are missing or file cannot be read
    """
    warnings = []

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise DataQualityError(f"Failed to read {filepath}: {e}")

    # Validate required columns
    required_cols = {"customer_id", "start_date", "end_date", "plan", "monthly_price"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise DataQualityError(
            f"Missing required columns in subscriptions.csv: {missing}"
        )

    subscriptions = []

    for idx, row in df.iterrows():
        try:
            customer_id = str(row["customer_id"])

            # Check if customer exists
            if customer_id not in valid_customer_ids:
                warnings.append(
                    f"Unknown customer_id '{customer_id}' at row {idx+2} - skipping subscription"
                )
                continue

            # Parse dates
            start_date = pd.to_datetime(str(row["start_date"]).strip()).date()

            end_date = None
            if pd.notna(row["end_date"]) and str(row["end_date"]).strip():
                try:
                    end_date = pd.to_datetime(str(row["end_date"]).strip()).date()
                except:
                    warnings.append(
                        f"Invalid end_date for subscription at row {idx+2} - treating as active"
                    )

            # Parse price (handle non-numeric strings)
            try:
                price = float(row["monthly_price"])
            except (ValueError, TypeError):
                warnings.append(
                    f"Invalid monthly_price '{row['monthly_price']}' at row {idx+2} - skipping"
                )
                continue

            # Validate with Pydantic
            subscription = Subscription(
                customer_id=customer_id,
                start_date=start_date,
                end_date=end_date,
                plan=str(row["plan"]),
                monthly_price=price,
            )

            # Warn about data quality issues
            if end_date and end_date < start_date:
                warnings.append(
                    f"Subscription for '{customer_id}' has end_date before start_date - skipping"
                )
                continue

            subscriptions.append(subscription)

        except (ValidationError, ValueError, pd.errors.OutOfBoundsDatetime) as e:
            warnings.append(f"Invalid subscription at row {idx+2}: {e} - skipping")
            continue

    logger.info(
        f"Loaded {len(subscriptions)} subscriptions with {len(warnings)} warnings"
    )
    return subscriptions, warnings
