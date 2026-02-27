"""
Data cleaning transformation for customers data (Bronze -> Silver).

This module implements data quality checks discovered in
notebooks/02_customer_data_inspection_ipynb.ipynb.

Data Quality Issues Fixed:
1. Whitespace trimming on all string fields
2. Duplicate customer_id handling (keep first occurrence)
3. Invalid signup_date validation (malformed dates like '2024-13-05')
4. Empty customer_id validation
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class CustomerDataCleaner:
    """Cleans and validates customer data from bronze to silver layer."""

    def __init__(self):
        self.validation_errors: list[str] = []
        self.removed_customer_ids: set[str] = set()  # Track removed customers

    def clean(self, bronze_df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean customer data with all transformations.

        Args:
            bronze_df: Raw customer data from bronze layer

        Returns:
            Cleaned customer data ready for silver layer

        Raises:
            ValueError: If critical data quality issues prevent processing
        """
        logger.info(f"Starting customer data cleaning for {len(bronze_df)} rows")
        self.validation_errors = []
        self.removed_customer_ids = set()

        df = bronze_df.copy()

        # Apply all cleaning steps
        df = self._clean_customer_id(df)
        df = self._clean_signup_date(df)
        df = self._clean_country(df)

        if self.validation_errors:
            error_msg = "\n".join(self.validation_errors)
            raise ValueError(f"Customer data quality validation failed:\n{error_msg}")

        logger.info(f"Customer data cleaning complete: {len(df)} rows validated")
        if self.removed_customer_ids:
            logger.warning(
                f"Removed {len(self.removed_customer_ids)} customers: "
                f"{sorted(self.removed_customer_ids)}"
            )

        return df

    def _clean_customer_id(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate customer_id field."""
        df['customer_id'] = df['customer_id'].str.strip()

        # Check for empty customer IDs
        empty_mask = df['customer_id'].isnull() | (df['customer_id'] == '')
        empty_count = empty_mask.sum()

        if empty_count > 0:
            self.validation_errors.append(
                f"Found {empty_count} empty customer_id values. "
                "Cannot process without valid customer identifiers."
            )
            logger.error(f"Empty customer_id found in {empty_count} rows")

        # Check for duplicates
        duplicates = df[df['customer_id'].duplicated(keep=False)]
        if not duplicates.empty:
            duplicate_ids = duplicates['customer_id'].unique()
            logger.warning(
                f"Found {len(duplicates)} duplicate customer entries "
                f"for IDs: {list(duplicate_ids)}. Keeping first occurrence."
            )
            
            # Track which customers are being removed (all but first occurrence)
            for cid in duplicate_ids:
                dup_rows = df[df['customer_id'] == cid]
                # All rows except the first are being removed
                removed = dup_rows.iloc[1:]
                if not removed.empty:
                    # Note: We're not actually removing duplicate IDs, just duplicate rows
                    # The ID remains valid, just deduplicated
                    pass
            
            # Remove duplicates, keeping first occurrence
            original_count = len(df)
            df = df.drop_duplicates(subset=['customer_id'], keep='first')
            removed_count = original_count - len(df)
            logger.info(f"Removed {removed_count} duplicate customer rows")

        return df

    def _clean_signup_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate signup_date field."""
        df['signup_date'] = df['signup_date'].str.strip()

        # Check for empty signup dates
        empty_mask = df['signup_date'].isnull() | (df['signup_date'] == '')
        empty_count = empty_mask.sum()

        if empty_count > 0:
            empty_customers = df[empty_mask]['customer_id'].tolist()
            logger.warning(
                f"Found {empty_count} empty signup_date values "
                f"for customers: {empty_customers}"
            )
            # Remove customers with empty signup dates
            df = df[~empty_mask].copy()
            self.removed_customer_ids.update(empty_customers)

        # Convert to datetime and check for malformed dates
        df['signup_date_parsed'] = pd.to_datetime(df['signup_date'], errors='coerce')
        malformed_mask = df['signup_date_parsed'].isnull() & df['signup_date'].notnull()
        
        if malformed_mask.any():
            malformed_customers = df[malformed_mask][['customer_id', 'signup_date']].values.tolist()
            logger.error(
                f"Found {malformed_mask.sum()} malformed signup_date values: "
                f"{malformed_customers}"
            )
            
            # Remove customers with malformed dates
            malformed_ids = df[malformed_mask]['customer_id'].tolist()
            df = df[~malformed_mask].copy()
            self.removed_customer_ids.update(malformed_ids)
            
            logger.warning(
                f"Removed {len(malformed_ids)} customers with invalid signup dates: "
                f"{malformed_ids}"
            )

        # Replace with parsed datetime
        df['signup_date'] = df['signup_date_parsed']
        df = df.drop('signup_date_parsed', axis=1)

        return df

    def _clean_country(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean country field (optional)."""
        if 'country' in df.columns:
            df['country'] = df['country'].str.strip()
            
            # Log missing countries but don't fail
            missing_country = df['country'].isnull() | (df['country'] == '')
            if missing_country.any():
                missing_count = missing_country.sum()
                missing_ids = df[missing_country]['customer_id'].tolist()
                logger.warning(
                    f"Found {missing_count} customers with missing country: {missing_ids}"
                )

        return df


def clean_customers_bronze_to_silver(
    bronze_path: Path,
    silver_path: Path
) -> set[str]:
    """
    Main entry point to clean customer data from bronze to silver layer.

    Args:
        bronze_path: Path to bronze customers.csv
        silver_path: Path to output cleaned customers_silver.csv

    Returns:
        Set of customer IDs that were removed during cleaning

    Raises:
        ValueError: If data quality validation fails
    """
    logger.info(f"Loading bronze customer data from {bronze_path}")
    bronze_df = pd.read_csv(bronze_path)
    logger.info(f"Loaded {len(bronze_df)} rows from bronze layer")

    cleaner = CustomerDataCleaner()
    silver_df = cleaner.clean(bronze_df)

    # Save to silver layer
    silver_path.parent.mkdir(parents=True, exist_ok=True)
    silver_df.to_csv(silver_path, index=False)
    logger.info(f"Saved {len(silver_df)} cleaned rows to {silver_path}")

    return cleaner.removed_customer_ids


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    from pathlib import Path

    base_path = Path(__file__).parent.parent.parent
    bronze_customers = base_path / "data" / "bronze" / "customers.csv"
    silver_customers = base_path / "data" / "silver" / "customers_silver.csv"

    removed_ids = clean_customers_bronze_to_silver(
        bronze_path=bronze_customers,
        silver_path=silver_customers
    )

    if removed_ids:
        print(f"\nWARNING: The following customer IDs were removed during cleaning:")
        print(f"  {sorted(removed_ids)}")
        print(f"\nThese customers should also be excluded from subscription data!")
