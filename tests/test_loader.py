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
