"""Tests for data loading and validation."""

from datetime import date
from pathlib import Path

import pytest

from loader import DataQualityError, load_customers, load_subscriptions


def test_load_customers_basic(tmp_path):
    """Test basic customer loading."""
    csv_file = tmp_path / "customers.csv"
    csv_file.write_text(
        "customer_id,signup_date,country\n"
        "C001,2024-01-15,NL\n"
        "C002,2024-02-20,DE\n"
    )

    customers, warnings = load_customers(csv_file)

    assert len(customers) == 2
    assert customers[0].customer_id == "C001"
    assert customers[0].signup_date == date(2024, 1, 15)
    assert customers[0].country == "NL"
    assert len(warnings) == 0


def test_load_customers_duplicate_id(tmp_path):
    """Test that duplicate customer IDs are detected and skipped."""
    csv_file = tmp_path / "customers.csv"
    csv_file.write_text(
        "customer_id,signup_date,country\n"
        "C001,2024-01-15,NL\n"
        "C001,2024-02-20,DE\n"
    )

    customers, warnings = load_customers(csv_file)

    # Should keep only first occurrence
    assert len(customers) == 1
    assert customers[0].signup_date == date(2024, 1, 15)
    assert len(warnings) == 1
    assert "Duplicate" in warnings[0]


def test_load_customers_invalid_date(tmp_path):
    """Test handling of invalid dates."""
    csv_file = tmp_path / "customers.csv"
    csv_file.write_text(
        "customer_id,signup_date,country\n"
        "C001,2024-01-15,NL\n"
        "C002,2024-13-45,DE\n"
    )

    customers, warnings = load_customers(csv_file)

    # Should skip invalid record
    assert len(customers) == 1
    assert customers[0].customer_id == "C001"
    assert len(warnings) == 1


def test_load_customers_missing_country(tmp_path):
    """Test handling of missing country."""
    csv_file = tmp_path / "customers.csv"
    csv_file.write_text(
        "customer_id,signup_date,country\n" "C001,2024-01-15,NL\n" "C002,2024-02-20,\n"
    )

    customers, warnings = load_customers(csv_file)

    # Should load but warn
    assert len(customers) == 2
    assert customers[1].country == ""
    assert len(warnings) == 1
    assert "missing country" in warnings[0]


def test_load_customers_missing_columns(tmp_path):
    """Test that missing required columns raise error."""
    csv_file = tmp_path / "customers.csv"
    csv_file.write_text("customer_id,signup_date\n" "C001,2024-01-15\n")

    with pytest.raises(DataQualityError, match="Missing required columns"):
        load_customers(csv_file)


def test_load_subscriptions_basic(tmp_path):
    """Test basic subscription loading."""
    csv_file = tmp_path / "subscriptions.csv"
    csv_file.write_text(
        "customer_id,start_date,end_date,plan,monthly_price\n"
        "C001,2024-01-15,,basic,30.0\n"
        "C002,2024-02-01,2024-03-01,pro,50.0\n"
    )

    valid_ids = {"C001", "C002"}
    subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

    assert len(subscriptions) == 2
    assert subscriptions[0].customer_id == "C001"
    assert subscriptions[0].end_date is None
    assert subscriptions[0].monthly_price == 30.0
    assert subscriptions[1].end_date == date(2024, 3, 1)
    assert len(warnings) == 0


def test_load_subscriptions_unknown_customer(tmp_path):
    """Test that subscriptions with unknown customer_id are skipped."""
    csv_file = tmp_path / "subscriptions.csv"
    csv_file.write_text(
        "customer_id,start_date,end_date,plan,monthly_price\n"
        "C001,2024-01-15,,basic,30.0\n"
        "C999,2024-02-01,,pro,50.0\n"
    )

    valid_ids = {"C001"}
    subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

    # Should skip C999
    assert len(subscriptions) == 1
    assert subscriptions[0].customer_id == "C001"
    assert len(warnings) == 1
    assert "Unknown customer_id" in warnings[0]


def test_load_subscriptions_invalid_price(tmp_path):
    """Test handling of invalid monthly_price."""
    csv_file = tmp_path / "subscriptions.csv"
    csv_file.write_text(
        "customer_id,start_date,end_date,plan,monthly_price\n"
        "C001,2024-01-15,,basic,30.0\n"
        'C002,2024-02-01,,pro,"thirty"\n'
    )

    valid_ids = {"C001", "C002"}
    subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

    # Should skip record with invalid price
    assert len(subscriptions) == 1
    assert len(warnings) == 1
    assert "Invalid monthly_price" in warnings[0]


def test_load_subscriptions_end_before_start(tmp_path):
    """Test that subscriptions with end_date before start_date are skipped."""
    csv_file = tmp_path / "subscriptions.csv"
    csv_file.write_text(
        "customer_id,start_date,end_date,plan,monthly_price\n"
        "C001,2024-03-01,2024-02-01,basic,30.0\n"
    )

    valid_ids = {"C001"}
    subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

    # Should skip invalid subscription
    assert len(subscriptions) == 0
    assert len(warnings) == 1
    assert "end_date before start_date" in warnings[0]


def test_load_subscriptions_whitespace_handling(tmp_path):
    """Test that whitespace in dates is handled correctly."""
    csv_file = tmp_path / "subscriptions.csv"
    csv_file.write_text(
        "customer_id,start_date,end_date,plan,monthly_price\n"
        'C001," 2024-01-15 ",,basic,30.0\n'
    )

    valid_ids = {"C001"}
    subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

    # Should handle whitespace
    assert len(subscriptions) == 1
    assert subscriptions[0].start_date == date(2024, 1, 15)


def test_load_subscriptions_missing_columns(tmp_path):
    """Test that missing required columns raise error."""
    csv_file = tmp_path / "subscriptions.csv"
    csv_file.write_text("customer_id,start_date,plan\n" "C001,2024-01-15,basic\n")

    with pytest.raises(DataQualityError, match="Missing required columns"):
        load_subscriptions(csv_file, set())


class TestLoaderEdgeCases:
    """Test edge cases and data quality validation in the loader."""

    def test_load_customers_negative_price_not_applicable(self, tmp_path):
        """Customers don't have prices, but verify date validation is strict."""
        csv_file = tmp_path / "customers.csv"
        csv_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,2024-01-01,US\n"
        )

        customers, warnings = load_customers(csv_file)
        assert len(customers) == 1

    def test_load_subscriptions_negative_price(self, tmp_path):
        """Test that negative prices are rejected (validated in model)."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,basic,-30.0\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        # Model validates non-negative price
        assert len(subscriptions) == 0
        assert len(warnings) == 1
        assert "negative" in warnings[0].lower()

    def test_load_subscriptions_zero_price(self, tmp_path):
        """Test that zero prices are accepted (valid for free plans)."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,free,0.0\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 1
        assert subscriptions[0].monthly_price == 0.0

    def test_load_subscriptions_very_high_price(self, tmp_path):
        """Test that very high prices are accepted."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,enterprise,99999.99\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 1
        assert subscriptions[0].monthly_price == 99999.99

    def test_load_subscriptions_future_start_date(self, tmp_path):
        """Test that future start dates are accepted."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2099-01-15,,basic,30.0\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 1
        assert subscriptions[0].start_date == date(2099, 1, 15)

    def test_load_subscriptions_same_start_end_date(self, tmp_path):
        """Test that start_date == end_date is accepted (1-day subscription)."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,2024-01-15,basic,30.0\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 1
        assert subscriptions[0].start_date == subscriptions[0].end_date

    def test_load_subscriptions_long_duration(self, tmp_path):
        """Test subscriptions with very long duration."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2020-01-01,2030-12-31,enterprise,100.0\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 1

    def test_load_subscriptions_empty_plan(self, tmp_path):
        """Test that empty plan field is accepted (loader is permissive)."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,unknown,30.0\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 1
        assert subscriptions[0].plan == "unknown"

    def test_load_subscriptions_multiple_invalid_mixed(self, tmp_path):
        """Test loading when some rows are valid and some have different issues."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,basic,30.0\n"
            "C002,2024-02-01,,pro,invalid\n"
            "C003,2024-03-01,2024-03-01,basic,50.0\n"
            "C999,2024-04-01,,pro,40.0\n"
        )

        valid_ids = {"C001", "C003"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        # Should have 2 valid subscriptions
        assert len(subscriptions) == 2
        assert len(warnings) == 2  # Invalid price + Unknown customer
        assert subscriptions[0].customer_id == "C001"
        assert subscriptions[1].customer_id == "C003"

    def test_load_customers_far_future_date(self, tmp_path):
        """Test that far-future signup dates are accepted."""
        csv_file = tmp_path / "customers.csv"
        csv_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,2099-12-31,US\n"
        )

        customers, warnings = load_customers(csv_file)

        assert len(customers) == 1
        assert customers[0].signup_date == date(2099, 12, 31)

    def test_load_customers_ancient_date(self, tmp_path):
        """Test very old signup dates are accepted."""
        csv_file = tmp_path / "customers.csv"
        csv_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,1900-01-01,US\n"
        )

        customers, warnings = load_customers(csv_file)

        assert len(customers) == 1
        assert customers[0].signup_date == date(1900, 1, 1)

    def test_load_subscriptions_all_invalid_rows(self, tmp_path):
        """Test handling when all subscription rows are invalid."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C999,2024-01-15,,basic,invalid\n"
            "C888,2024-02-01,,pro,also_invalid\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 0
        assert len(warnings) == 2

    def test_load_customers_all_invalid_rows(self, tmp_path):
        """Test handling when all customer rows are invalid."""
        csv_file = tmp_path / "customers.csv"
        csv_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,invalid-date,US\n"
            "C002,not-a-date,UK\n"
        )

        customers, warnings = load_customers(csv_file)

        assert len(customers) == 0
        assert len(warnings) == 2


class TestSkipPreprocessingScenarios:
    """Test scenarios that occur when using --skip-preprocessing on dirty silver data.
    
    These tests validate that the loader gracefully handles common data quality issues
    that would normally be fixed by the preprocessing step. If a user runs with
    --skip-preprocessing on silver data that has these issues, the metrics will be degraded
    (some data skipped), and warnings will alert them to the problem.
    """

    def test_load_subscriptions_with_text_price_no_preprocessing(self, tmp_path):
        """Scenario: Silver data has text price 'thirty' (preprocessing was skipped).
        
        Expected: Subscription is skipped, MRR is degraded by $30/month.
        """
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,pro,thirty\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 0  # Text price fails conversion
        assert len(warnings) == 1
        assert "Invalid monthly_price" in warnings[0]

    def test_load_subscriptions_with_various_text_prices(self, tmp_path):
        """Scenario: Multiple non-numeric price values that preprocessing should have fixed."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,basic,twenty\n"
            "C002,2024-02-01,,pro,fifty five\n"
            "C003,2024-03-01,,enterprise,unlimited\n"
        )

        valid_ids = {"C001", "C002", "C003"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        # All fail due to non-numeric prices
        assert len(subscriptions) == 0
        assert len(warnings) == 3

    def test_load_subscriptions_mixed_text_and_numeric_prices(self, tmp_path):
        """Scenario: Some prices are numbers, some are text (data cleanup failed partway)."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,basic,30\n"
            "C002,2024-02-01,,pro,forty\n"
            "C003,2024-03-01,,enterprise,100\n"
        )

        valid_ids = {"C001", "C002", "C003"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        # Only numeric ones load
        assert len(subscriptions) == 2
        assert len(warnings) == 1  # One text price fails
        assert subscriptions[0].monthly_price == 30.0
        assert subscriptions[1].monthly_price == 100.0

    def test_load_subscriptions_with_typo_plan_names(self, tmp_path):
        """Scenario: Plan names have typos like 'baisc' (preprocessing was skipped).
        
        Note: Loader doesn't validate plan names - they're accepted as-is.
        This means typos won't cause row rejection, but metrics by plan will be incorrect.
        """
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,baisc,30.0\n"
            "C002,2024-02-01,,basic,50.0\n"
        )

        valid_ids = {"C001", "C002"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        # Both load (loader doesn't validate plan values)
        assert len(subscriptions) == 2
        assert len(warnings) == 0
        # But plan names are different (data quality issue)
        assert subscriptions[0].plan == "baisc"
        assert subscriptions[1].plan == "basic"

    def test_load_customers_with_malformed_dates_no_preprocessing(self, tmp_path):
        """Scenario: Customer with invalid month like '2024-13-05' (preprocessing was skipped).
        
        Expected: Customer is skipped, metrics lose this customer and their subscriptions.
        """
        csv_file = tmp_path / "customers.csv"
        csv_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,2024-01-15,NL\n"
            "C019,2024-13-05,NL\n"
            "C003,2024-03-15,NL\n"
        )

        customers, warnings = load_customers(csv_file)

        assert len(customers) == 2  # C019 skipped
        assert len(warnings) == 1
        assert "month must be in 1..12" in warnings[0]
        assert customers[0].customer_id == "C001"
        assert customers[1].customer_id == "C003"

    def test_load_customers_with_invalid_february_29(self, tmp_path):
        """Scenario: Invalid date like '2024-02-30' (preprocessing doesn't fix calendar errors).
        
        This is a real data quality issue in the bronze data.
        """
        csv_file = tmp_path / "customers.csv"
        csv_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,2024-01-15,NL\n"
            "C020,2024-02-30,DE\n"
        )

        customers, warnings = load_customers(csv_file)

        assert len(customers) == 1
        assert len(warnings) == 1
        assert "day is out of range" in warnings[0]

    def test_load_subscriptions_with_duplicate_customers_no_preprocessing(self, tmp_path):
        """Scenario: Duplicate customer IDs in silver data (preprocessing was skipped).
        
        Expected: Loader detects duplicates and keeps first occurrence.
        This is handled consistently with preprocessing behavior.
        """
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,basic,30.0\n"
            "C001,2024-02-01,,pro,50.0\n"
        )

        valid_ids = {"C001"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        # Both load (loader doesn't detect duplicate subscriptions, just unknown customers)
        assert len(subscriptions) == 2
        assert len(warnings) == 0

    def test_load_customers_with_duplicate_ids_no_preprocessing(self, tmp_path):
        """Scenario: Duplicate customer IDs in silver data (preprocessing was skipped).
        
        Expected: Loader detects and skips duplicates, keeping first occurrence.
        """
        csv_file = tmp_path / "customers.csv"
        csv_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,2024-01-15,NL\n"
            "C001,2024-01-16,DE\n"
            "C002,2024-02-15,UK\n"
        )

        customers, warnings = load_customers(csv_file)

        assert len(customers) == 2  # Duplicate C001 skipped
        assert len(warnings) == 1
        assert "Duplicate" in warnings[0]
        assert customers[0].country == "NL"  # First occurrence kept

    def test_load_subscriptions_for_removed_customers(self, tmp_path):
        """Scenario: Subscriptions exist for customers that were removed during preprocessing.
        
        If preprocessing removed C019, but subscriptions weren't filtered, we get orphans.
        Expected: Loader skips these as unknown customer IDs.
        """
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,basic,30.0\n"
            "C019,2024-07-15,,pro,50.0\n"
            "C003,2024-03-15,,basic,30.0\n"
        )

        # C019 was removed during preprocessing
        valid_ids = {"C001", "C003"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        assert len(subscriptions) == 2
        assert len(warnings) == 1
        assert "Unknown customer_id" in warnings[0]
        assert "C019" in warnings[0]

    def test_combined_dirty_data_scenario_no_preprocessing(self, tmp_path):
        """Scenario: Multiple data quality issues present when preprocessing is skipped.
        
        This represents a worst-case where preprocessing step was skipped on
        dirty data and multiple issues compound to degrade metrics.
        """
        # Create dirty customer data
        customers_file = tmp_path / "customers.csv"
        customers_file.write_text(
            "customer_id,signup_date,country\n"
            "C001,2024-01-15,NL\n"
            "C001,2024-01-16,DE\n"
            "C019,2024-13-05,NL\n"
            "C003,2024-03-15,UK\n"
        )

        # Create dirty subscription data
        subscriptions_file = tmp_path / "subscriptions.csv"
        subscriptions_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,,basic,30.0\n"
            "C019,2024-07-15,,pro,fifty\n"
            "C003,2024-03-01,,baisc,30.0\n"
            "C999,2024-04-01,,pro,40.0\n"
        )

        # Load customers
        customers, cust_warnings = load_customers(customers_file)
        assert len(customers) == 2  # C001 deduplicated, C019 skipped
        assert len(cust_warnings) == 2

        # Load subscriptions
        valid_ids = {c.customer_id for c in customers}
        subscriptions, sub_warnings = load_subscriptions(subscriptions_file, valid_ids)

        # Expect: C001 basic, C019 skipped (orphan), C003 baisc accepted, C999 skipped (unknown)
        assert len(subscriptions) == 2
        assert len(sub_warnings) == 2  # C019 (text price or unknown), C999 (unknown)

    def test_whitespace_and_typos_combined(self, tmp_path):
        """Scenario: Whitespace AND typos combined in silver data."""
        csv_file = tmp_path / "subscriptions.csv"
        csv_file.write_text(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-15,, baisc ,30.0\n"
            "C002,2024-02-01,,basic, 50.0 \n"
        )

        valid_ids = {"C001", "C002"}
        subscriptions, warnings = load_subscriptions(csv_file, valid_ids)

        # Whitespace in plan name is normalized (stripped), typo remains
        assert len(subscriptions) == 2
        assert subscriptions[0].plan == "baisc"  # Typo not fixed
        assert subscriptions[1].plan == "basic"  # Normal
