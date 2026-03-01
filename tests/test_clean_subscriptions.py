"""
Tests for subscription data cleaning transformations.

Tests cover all data quality issues discovered in the inspection notebook.
"""

import numpy as np
import pandas as pd
import pytest
from src.transformers.clean_subscriptions import SubscriptionDataCleaner


class TestSubscriptionDataCleaner:
    """Test suite for SubscriptionDataCleaner class."""

    @pytest.fixture
    def cleaner(self):
        """Create a fresh cleaner instance for each test."""
        return SubscriptionDataCleaner()

    @pytest.fixture
    def valid_bronze_data(self):
        """Create valid bronze data for testing."""
        return pd.DataFrame({
            'customer_id': ['C001', 'C002', 'C003'],
            'start_date': ['2023-01-01', '2023-02-01', '2023-03-01'],
            'end_date': ['2023-12-31', '', '2024-03-01'],
            'plan': ['basic', 'premium', 'basic'],
            'monthly_price': ['10', '30', '10']
        })

    def test_clean_valid_data(self, cleaner, valid_bronze_data):
        """Test cleaning of valid data succeeds."""
        result = cleaner.clean(valid_bronze_data)
        assert len(result) == 3
        assert len(cleaner.validation_errors) == 0

    def test_whitespace_trimming(self, cleaner):
        """Test that whitespace is trimmed from all fields."""
        df = pd.DataFrame({
            'customer_id': [' C001 ', 'C002 '],
            'start_date': [' 2023-01-01', '2023-02-01 '],
            'end_date': ['2023-12-31 ', ' '],
            'plan': [' basic ', 'premium'],
            'monthly_price': [' 10 ', '30']
        })

        result = cleaner.clean(df)
        assert result['customer_id'].iloc[0] == 'C001'
        assert result['start_date'].iloc[0] == '2023-01-01'
        assert result['plan'].iloc[0] == 'basic'
        assert result['monthly_price'].iloc[0] == '10'

    def test_empty_customer_id_fails(self, cleaner):
        """Test that empty customer_id causes validation error."""
        df = pd.DataFrame({
            'customer_id': ['', 'C002'],
            'start_date': ['2023-01-01', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', '30']
        })

        with pytest.raises(ValueError, match="empty customer_id"):
            cleaner.clean(df)

    def test_empty_start_date_fails(self, cleaner):
        """Test that empty start_date causes validation error."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002'],
            'start_date': ['', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', '30']
        })

        with pytest.raises(ValueError, match="empty start_date"):
            cleaner.clean(df)

    def test_malformed_start_date_fails(self, cleaner):
        """Test that malformed start_date causes validation error."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002'],
            'start_date': ['not-a-date', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', '30']
        })

        with pytest.raises(ValueError, match="malformed start_date"):
            cleaner.clean(df)

    def test_empty_end_date_allowed(self, cleaner):
        """Test that empty end_date is allowed (active subscriptions)."""
        df = pd.DataFrame({
            'customer_id': ['C001'],
            'start_date': ['2023-01-01'],
            'end_date': [''],
            'plan': ['basic'],
            'monthly_price': ['10']
        })

        result = cleaner.clean(df)
        assert len(result) == 1
        assert len(cleaner.validation_errors) == 0

    def test_plan_typo_correction(self, cleaner):
        """Test that 'baisc' typo is corrected to 'basic'."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002'],
            'start_date': ['2023-01-01', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['baisc', 'premium'],
            'monthly_price': ['10', '30']
        })

        result = cleaner.clean(df)
        assert result['plan'].iloc[0] == 'basic'
        assert result['plan'].iloc[1] == 'premium'

    def test_monthly_price_text_to_number(self, cleaner):
        """Test that 'thirty' is converted to '30'."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002'],
            'start_date': ['2023-01-01', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', 'thirty']
        })

        result = cleaner.clean(df)
        assert result['monthly_price'].iloc[1] == '30'

    def test_non_numeric_monthly_price_fails(self, cleaner):
        """Test that non-numeric monthly_price causes validation error."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002'],
            'start_date': ['2023-01-01', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', 'forty-five']
        })

        with pytest.raises(ValueError, match="non-numeric monthly_price"):
            cleaner.clean(df)

    def test_end_date_before_start_date_fails(self, cleaner):
        """Test that end_date earlier than start_date causes validation error."""
        df = pd.DataFrame({
            'customer_id': ['C001', 'C002'],
            'start_date': ['2023-03-01', '2023-02-01'],
            'end_date': ['2023-01-01', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', '30']
        })

        with pytest.raises(ValueError, match="end_date before start_date"):
            cleaner.clean(df)

    def test_unknown_customers_filtered_when_reference_provided(self):
        """Test that unknown customer subscriptions are filtered during preprocessing."""
        cleaner = SubscriptionDataCleaner(valid_customer_ids={'C001'})
        df = pd.DataFrame({
            'customer_id': ['C001', 'C999'],
            'start_date': ['2023-01-01', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', '30']
        })

        result = cleaner.clean(df)
        assert len(result) == 1
        assert result['customer_id'].tolist() == ['C001']

    def test_start_before_signup_fails_when_signup_reference_provided(self):
        """Test that subscription start before customer signup fails validation."""
        cleaner = SubscriptionDataCleaner(
            customer_signup_dates={'C001': pd.Timestamp('2023-02-01')}
        )
        df = pd.DataFrame({
            'customer_id': ['C001'],
            'start_date': ['2023-01-01'],
            'end_date': [''],
            'plan': ['basic'],
            'monthly_price': ['10']
        })

        with pytest.raises(ValueError, match="start_date before customer signup_date"):
            cleaner.clean(df)

    def test_overlapping_subscriptions_fail_in_strict_policy(self):
        """Test that overlapping subscriptions fail when overlap policy is strict."""
        cleaner = SubscriptionDataCleaner(overlap_policy='strict')
        df = pd.DataFrame({
            'customer_id': ['C001', 'C001'],
            'start_date': ['2023-01-01', '2023-01-15'],
            'end_date': ['2023-02-01', '2023-03-01'],
            'plan': ['basic', 'premium'],
            'monthly_price': ['10', '30']
        })

        with pytest.raises(ValueError, match="overlapping subscription"):
            cleaner.clean(df)

    def test_all_known_issues_together(self, cleaner):
        """Test fixing all known data quality issues in one dataset."""
        df = pd.DataFrame({
            'customer_id': [' C001 ', 'C002'],
            'start_date': [' 2023-01-01 ', '2023-02-01'],
            'end_date': ['2023-12-31', ' '],
            'plan': ['baisc ', ' premium'],
            'monthly_price': [' thirty', '10 ']
        })

        result = cleaner.clean(df)

        # Verify all corrections applied
        assert result['customer_id'].iloc[0] == 'C001'
        assert result['plan'].iloc[0] == 'basic'
        assert result['monthly_price'].iloc[0] == '30'
        assert result['monthly_price'].iloc[1] == '10'

    def test_multiple_validation_errors_reported(self, cleaner):
        """Test that multiple validation errors are all reported."""
        df = pd.DataFrame({
            'customer_id': ['', 'C002'],
            'start_date': ['not-a-date', '2023-02-01'],
            'end_date': ['', ''],
            'plan': ['basic', 'premium'],
            'monthly_price': ['invalid', '30']
        })

        with pytest.raises(ValueError) as exc_info:
            cleaner.clean(df)

        error_msg = str(exc_info.value)
        # Should contain all three types of errors
        assert "customer_id" in error_msg
        assert "start_date" in error_msg
        assert "monthly_price" in error_msg


class TestDataCleaning:
    """Integration tests for the cleaning process."""

    def test_bronze_data_matches_known_issues(self):
        """
        Test that our actual bronze data has the known issues.
        This validates that the cleaning is actually needed.
        """
        from pathlib import Path
        bronze_path = Path("data/bronze/subscriptions.csv")

        if not bronze_path.exists():
            pytest.skip("Bronze data not available")

        df = pd.read_csv(bronze_path)

        # Check for the known issues
        has_baisc_typo = (df['plan'] == 'baisc').any()
        has_thirty_text = (df['monthly_price'] == 'thirty').any()

        # At least one of these issues should exist in the bronze data
        assert has_baisc_typo or has_thirty_text, \
            "Bronze data should contain known quality issues for cleaning to be meaningful"
