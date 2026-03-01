"""
Data cleaning transformation for subscriptions data (Bronze -> Silver).

This module implements all data quality checks and corrections discovered in
notebooks/01_subscription_data_inspection.ipynb.

Data Quality Issues Fixed:
1. Whitespace trimming on all string fields
2. Typo correction: 'baisc' -> 'basic' in plan field
3. Text-to-numeric conversion: 'thirty' -> '30' in monthly_price field
4. Empty/malformed date validation
5. Non-numeric price validation
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SubscriptionDataCleaner:
    """Cleans and validates subscription data from bronze to silver layer."""

    def __init__(
        self,
        excluded_customer_ids: Optional[set[str]] = None,
        valid_customer_ids: Optional[set[str]] = None,
        customer_signup_dates: Optional[dict[str, pd.Timestamp]] = None,
        overlap_policy: str = "warn",
    ):
        """
        Initialize the cleaner.
        
        Args:
            excluded_customer_ids: Set of customer IDs that were removed during
                                   customer data cleaning and should be filtered out
            valid_customer_ids: Set of known valid customer IDs. If provided,
                                subscriptions for unknown customers are filtered out.
            customer_signup_dates: Mapping of customer_id -> signup_date used to
                                   validate subscription start_date is on/after signup.
            overlap_policy: How to handle overlapping subscriptions for same customer:
                            "warn" (default) or "strict".
        """
        self.validation_errors: list[str] = []
        self.excluded_customer_ids = excluded_customer_ids or set()
        self.valid_customer_ids = valid_customer_ids
        self.customer_signup_dates = customer_signup_dates or {}
        if overlap_policy not in {"warn", "strict"}:
            raise ValueError("overlap_policy must be either 'warn' or 'strict'")
        self.overlap_policy = overlap_policy

    def clean(self, bronze_df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean subscription data with all transformations.

        Args:
            bronze_df: Raw subscription data from bronze layer

        Returns:
            Cleaned subscription data ready for silver layer

        Raises:
            ValueError: If critical data quality issues prevent processing
        """
        logger.info(f"Starting data cleaning for {len(bronze_df)} rows")
        self.validation_errors = []

        df = bronze_df.copy()

        # Filter out subscriptions for excluded customers FIRST
        if self.excluded_customer_ids:
            excluded_mask = df['customer_id'].isin(self.excluded_customer_ids)
            excluded_count = excluded_mask.sum()
            if excluded_count > 0:
                excluded_subs = df[excluded_mask]['customer_id'].value_counts()
                logger.warning(
                    f"Filtering out {excluded_count} subscriptions for "
                    f"{len(excluded_subs)} excluded customers: {dict(excluded_subs)}"
                )
                df = df[~excluded_mask].copy()

        # Apply all cleaning steps
        df = self._clean_customer_id(df)
        df = self._filter_unknown_customers(df)
        df = self._clean_start_date(df)
        df = self._clean_end_date(df)
        df = self._clean_plan(df)
        df = self._clean_monthly_price(df)
        df = self._validate_date_ranges(df)
        df = self._validate_start_after_signup(df)
        self._handle_overlaps(df)
        self._run_quality_diagnostics(df)

        if self.validation_errors:
            error_msg = "\n".join(self.validation_errors)
            raise ValueError(f"Data quality validation failed:\n{error_msg}")

        logger.info(f"Data cleaning complete: {len(df)} rows validated")
        return df

    def _filter_unknown_customers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter subscriptions with customer IDs not present in customer reference data."""
        if not self.valid_customer_ids:
            return df

        unknown_mask = ~df['customer_id'].isin(self.valid_customer_ids)
        unknown_count = unknown_mask.sum()

        if unknown_count > 0:
            unknown_examples = df.loc[unknown_mask, 'customer_id'].head(10).tolist()
            logger.warning(
                "Filtering out %s subscriptions with unknown customer_id values. "
                "Examples: %s",
                unknown_count,
                unknown_examples,
            )
            df = df[~unknown_mask].copy()

        return df

    def _clean_customer_id(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate customer_id field."""
        df['customer_id'] = df['customer_id'].str.strip()

        # Check for empty customer IDs
        empty_mask = df['customer_id'].replace('', np.nan).str.strip().isna()
        empty_count = empty_mask.sum()

        if empty_count > 0:
            self.validation_errors.append(
                f"Found {empty_count} empty customer_id values. "
                "Cannot process without valid customer identifiers."
            )
            logger.error(f"Empty customer_id found in {empty_count} rows")

        return df

    def _clean_start_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate start_date field."""
        df['start_date'] = df['start_date'].str.strip()

        # Check for empty start dates
        empty_mask = df['start_date'].replace('', np.nan).str.strip().isna()
        empty_count = empty_mask.sum()

        if empty_count > 0:
            self.validation_errors.append(
                f"Found {empty_count} empty start_date values. "
                "Cannot infer subscription start without this field."
            )
            logger.error(f"Empty start_date found in {empty_count} rows")

        # Check for malformed dates
        temp_dates = pd.to_datetime(df['start_date'], errors='coerce')
        malformed_mask = temp_dates.isna() & ~empty_mask
        malformed_count = malformed_mask.sum()

        if malformed_count > 0:
            malformed_examples = df[malformed_mask]['start_date'].head(5).tolist()
            self.validation_errors.append(
                f"Found {malformed_count} malformed start_date values. "
                f"Examples: {malformed_examples}"
            )
            logger.error(f"Malformed start_date found in {malformed_count} rows")

        return df

    def _clean_end_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate end_date field (empty values allowed for active subscriptions)."""
        df['end_date'] = df['end_date'].str.strip()

        # Normalize empty strings to NaN (after stripping)
        df['end_date'] = df['end_date'].replace('', np.nan)
        genuinely_empty_count = df['end_date'].isna().sum()

        # Check for malformed dates (non-empty but unparseable)
        temp_dates = pd.to_datetime(df['end_date'], errors='coerce')
        malformed_mask = temp_dates.isna() & df['end_date'].notna()
        malformed_count = malformed_mask.sum()

        if malformed_count > 0:
            malformed_examples = df[malformed_mask]['end_date'].head(5).tolist()
            logger.warning(
                f"Found {malformed_count} malformed end_date values "
                f"(not empty but unparseable). Examples: {malformed_examples}"
            )

        logger.info(f"end_date: {genuinely_empty_count} empty (active subs), "
                   f"{malformed_count} malformed")

        return df

    def _clean_plan(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize plan field."""
        df['plan'] = df['plan'].str.strip()

        # Fix known typo
        typo_count = (df['plan'] == 'baisc').sum()
        if typo_count > 0:
            logger.info(f"Correcting 'baisc' -> 'basic' typo in {typo_count} rows")
            df['plan'] = df['plan'].replace('baisc', 'basic')

        unique_plans = df['plan'].unique()
        logger.info(f"Found {len(unique_plans)} unique plans: {unique_plans}")

        return df

    def _clean_monthly_price(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate monthly_price field."""
        df['monthly_price'] = df['monthly_price'].str.strip()

        # Fix known text-to-number issue
        text_price_count = (df['monthly_price'] == 'thirty').sum()
        if text_price_count > 0:
            logger.info(f"Converting 'thirty' -> '30' in {text_price_count} rows")
            df['monthly_price'] = df['monthly_price'].replace('thirty', '30')

        # Validate all prices are numeric
        temp_numeric = pd.to_numeric(df['monthly_price'], errors='coerce')
        non_numeric_mask = temp_numeric.isna()
        non_numeric_count = non_numeric_mask.sum()

        if non_numeric_count > 0:
            non_numeric_examples = df[non_numeric_mask]['monthly_price'].head(5).tolist()
            self.validation_errors.append(
                f"Found {non_numeric_count} non-numeric monthly_price values. "
                f"Examples: {non_numeric_examples}"
            )
            logger.error(f"Non-numeric monthly_price found in {non_numeric_count} rows")

        return df

    def _validate_date_ranges(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate that end_date is not earlier than start_date when end_date exists."""
        start_dates = pd.to_datetime(df['start_date'], errors='coerce')
        end_dates = pd.to_datetime(df['end_date'], errors='coerce')

        invalid_mask = end_dates.notna() & start_dates.notna() & (end_dates < start_dates)
        invalid_count = invalid_mask.sum()

        if invalid_count > 0:
            examples = (
                df.loc[invalid_mask, ['customer_id', 'start_date', 'end_date']]
                .head(5)
                .to_dict('records')
            )
            self.validation_errors.append(
                f"Found {invalid_count} subscriptions with end_date before start_date. "
                f"Examples: {examples}"
            )
            logger.error(f"Invalid date ranges found in {invalid_count} rows")

        return df

    def _validate_start_after_signup(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate subscription start_date is on/after customer's signup_date when available."""
        if not self.customer_signup_dates:
            return df

        start_dates = pd.to_datetime(df['start_date'], errors='coerce')
        signup_series = df['customer_id'].map(self.customer_signup_dates)
        signup_dates = pd.to_datetime(signup_series, errors='coerce')

        invalid_mask = start_dates.notna() & signup_dates.notna() & (start_dates < signup_dates)
        invalid_count = invalid_mask.sum()

        if invalid_count > 0:
            examples = (
                df.loc[invalid_mask, ['customer_id', 'start_date']]
                .assign(signup_date=signup_dates[invalid_mask].dt.strftime('%Y-%m-%d').values)
                .head(5)
                .to_dict('records')
            )
            self.validation_errors.append(
                f"Found {invalid_count} subscriptions with start_date before customer signup_date. "
                f"Examples: {examples}"
            )
            logger.error("Subscriptions starting before signup found in %s rows", invalid_count)

        return df

    def _handle_overlaps(self, df: pd.DataFrame) -> None:
        """Detect overlapping subscriptions per customer and apply configured policy."""
        work = df.copy()
        work['start_dt'] = pd.to_datetime(work['start_date'], errors='coerce')
        work['end_dt'] = pd.to_datetime(work['end_date'], errors='coerce')
        work['end_for_overlap'] = work['end_dt'].fillna(pd.Timestamp.max.normalize())

        overlap_examples: list[dict[str, str]] = []
        overlap_count = 0

        grouped = work.dropna(subset=['start_dt']).sort_values(['customer_id', 'start_dt']).groupby('customer_id')
        for customer_id, group in grouped:
            prev_end = None
            prev_start = None
            for _, row in group.iterrows():
                if prev_end is not None and row['start_dt'] <= prev_end:
                    overlap_count += 1
                    if len(overlap_examples) < 5:
                        overlap_examples.append(
                            {
                                'customer_id': customer_id,
                                'previous_start': prev_start.strftime('%Y-%m-%d') if prev_start is not None else '',
                                'previous_end': prev_end.strftime('%Y-%m-%d') if prev_end != pd.Timestamp.max.normalize() else 'active',
                                'current_start': row['start_dt'].strftime('%Y-%m-%d'),
                                'current_end': row['end_dt'].strftime('%Y-%m-%d') if pd.notna(row['end_dt']) else 'active',
                            }
                        )
                if prev_end is None or row['end_for_overlap'] > prev_end:
                    prev_end = row['end_for_overlap']
                    prev_start = row['start_dt']

        if overlap_count > 0:
            msg = (
                f"Found {overlap_count} overlapping subscription pairs. "
                f"Examples: {overlap_examples}"
            )
            if self.overlap_policy == 'strict':
                self.validation_errors.append(msg)
                logger.error("Overlapping subscriptions found and rejected by strict policy")
            else:
                logger.warning("%s", msg)

    def _run_quality_diagnostics(self, df: pd.DataFrame) -> None:
        """Run non-blocking quality diagnostics (warnings only)."""
        prices = pd.to_numeric(df['monthly_price'], errors='coerce')
        valid_prices = prices.dropna()

        # Outlier diagnostics (IQR-based, warning only)
        if len(valid_prices) >= 4:
            q1 = valid_prices.quantile(0.25)
            q3 = valid_prices.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outlier_mask = (prices < lower_bound) | (prices > upper_bound)
                outlier_count = outlier_mask.sum()

                if outlier_count > 0:
                    outlier_examples = (
                        df.loc[outlier_mask, ['customer_id', 'plan', 'monthly_price']]
                        .head(5)
                        .to_dict('records')
                    )
                    logger.warning(
                        "Price outlier diagnostic: found %s potential outliers "
                        "outside IQR bounds [%.2f, %.2f]. Examples: %s",
                        outlier_count,
                        lower_bound,
                        upper_bound,
                        outlier_examples,
                    )

        # Intra-plan price spread diagnostics (warning only)
        diagnostic_df = df[['plan']].copy()
        diagnostic_df['monthly_price_numeric'] = prices
        diagnostic_df = diagnostic_df.dropna(subset=['plan', 'monthly_price_numeric'])

        if not diagnostic_df.empty:
            for plan, group in diagnostic_df.groupby('plan'):
                if len(group) < 2:
                    continue

                unique_price_count = group['monthly_price_numeric'].nunique()
                min_price = group['monthly_price_numeric'].min()
                max_price = group['monthly_price_numeric'].max()

                if unique_price_count > 1:
                    logger.warning(
                        "Plan pricing diagnostic: plan '%s' has %s distinct prices "
                        "(min=%.2f, max=%.2f)",
                        plan,
                        unique_price_count,
                        min_price,
                        max_price,
                    )


def clean_subscriptions_bronze_to_silver(
    bronze_path: Path,
    silver_path: Path,
    customers_bronze_path: Optional[Path] = None,
    excluded_customer_ids: Optional[set[str]] = None,
    overlap_policy: str = "warn",
) -> None:
    """
    Main entry point to clean subscription data from bronze to silver layer.

    Args:
        bronze_path: Path to bronze subscriptions.csv
        silver_path: Path to output cleaned subscriptions_silver.csv
        customers_bronze_path: Optional path to customer reference CSV
        excluded_customer_ids: Set of customer IDs removed during customer cleaning
                               that should be filtered out of subscriptions
        overlap_policy: How to handle overlaps: "warn" or "strict"

    Raises:
        ValueError: If data quality validation fails
    """
    logger.info(f"Loading bronze subscription data from {bronze_path}")
    bronze_df = pd.read_csv(bronze_path)
    logger.info(f"Loaded {len(bronze_df)} rows from bronze layer")

    valid_customer_ids: Optional[set[str]] = None
    customer_signup_dates: Optional[dict[str, pd.Timestamp]] = None

    if customers_bronze_path and customers_bronze_path.exists():
        customers_df = pd.read_csv(customers_bronze_path)
        customers_df['customer_id'] = customers_df['customer_id'].astype(str).str.strip()
        customers_df = customers_df.drop_duplicates(subset=['customer_id'], keep='first')

        # Exclude customers already removed in customer cleaning step
        if excluded_customer_ids:
            customers_df = customers_df[~customers_df['customer_id'].isin(excluded_customer_ids)].copy()

        valid_customer_ids = set(customers_df['customer_id'])

        if 'signup_date' in customers_df.columns:
            parsed_signup = pd.to_datetime(customers_df['signup_date'], errors='coerce')
            customer_signup_dates = {
                cid: signup
                for cid, signup in zip(customers_df['customer_id'], parsed_signup)
                if pd.notna(signup)
            }

    cleaner = SubscriptionDataCleaner(
        excluded_customer_ids=excluded_customer_ids,
        valid_customer_ids=valid_customer_ids,
        customer_signup_dates=customer_signup_dates,
        overlap_policy=overlap_policy,
    )
    silver_df = cleaner.clean(bronze_df)

    # Save to silver layer
    silver_path.parent.mkdir(parents=True, exist_ok=True)
    silver_df.to_csv(silver_path, index=False)
    logger.info(f"Saved {len(silver_df)} cleaned rows to {silver_path}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the cleaning pipeline
    from pathlib import Path

    base_path = Path(__file__).parent.parent.parent
    bronze_subs = base_path / "data" / "bronze" / "subscriptions.csv"
    bronze_customers = base_path / "data" / "bronze" / "customers.csv"
    silver_subs = base_path / "data" / "silver" / "subscriptions_silver.csv"

    clean_subscriptions_bronze_to_silver(
        bronze_path=bronze_subs,
        silver_path=silver_subs,
        customers_bronze_path=bronze_customers
    )
