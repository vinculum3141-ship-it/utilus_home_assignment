"""Tests for metrics calculations."""

from datetime import date

import pytest

from metrics import (
    calculate_cohort_retention,
    calculate_monthly_churn,
    calculate_monthly_mrr,
)
from models import Customer, Subscription


def test_monthly_mrr_basic():
    """Test basic MRR calculation."""
    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 1),
            end_date=None,
            plan="basic",
            monthly_price=30.0,
        ),
        Subscription(
            customer_id="C002",
            start_date=date(2024, 1, 15),
            end_date=None,
            plan="pro",
            monthly_price=50.0,
        ),
    ]

    mrr_data = calculate_monthly_mrr(subscriptions)

    assert len(mrr_data) >= 1
    # Both subscriptions active in Jan 2024
    jan_mrr = next((m for m in mrr_data if m.month == "2024-01"), None)
    assert jan_mrr is not None
    assert jan_mrr.mrr == 80.0


def test_monthly_mrr_ended_subscription():
    """Test MRR calculation with ended subscriptions."""
    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            plan="basic",
            monthly_price=30.0,
        ),
    ]

    mrr_data = calculate_monthly_mrr(subscriptions)

    jan_mrr = next((m for m in mrr_data if m.month == "2024-01"), None)
    assert jan_mrr is not None
    assert jan_mrr.mrr == 30.0

    # Should not contribute to Feb
    feb_mrr = next((m for m in mrr_data if m.month == "2024-02"), None)
    if feb_mrr:
        assert feb_mrr.mrr == 0.0


def test_churn_no_resubscribe():
    """Test churn detection when customer doesn't resubscribe."""
    customers = [
        Customer(customer_id="C001", signup_date=date(2024, 1, 1), country="NL")
    ]

    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 28),
            plan="basic",
            monthly_price=30.0,
        ),
    ]

    churn_data = calculate_monthly_churn(customers, subscriptions)

    # Customer should be marked as churned in February
    feb_churn = next((c for c in churn_data if c.month == "2024-02"), None)
    assert feb_churn is not None
    assert feb_churn.churned_count == 1


def test_churn_with_resubscribe_within_30_days():
    """Test that customer is NOT churned if they resubscribe within 30 days."""
    customers = [
        Customer(customer_id="C001", signup_date=date(2024, 1, 1), country="NL")
    ]

    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 28),
            plan="basic",
            monthly_price=30.0,
        ),
        Subscription(
            customer_id="C001",
            start_date=date(2024, 3, 15),  # 15 days after end_date
            end_date=None,
            plan="pro",
            monthly_price=50.0,
        ),
    ]

    churn_data = calculate_monthly_churn(customers, subscriptions)

    # Customer should NOT be counted as churned
    feb_churn = next((c for c in churn_data if c.month == "2024-02"), None)
    if feb_churn:
        assert feb_churn.churned_count == 0


def test_churn_with_resubscribe_after_30_days():
    """Test that customer IS churned if they resubscribe after 30 days."""
    customers = [
        Customer(customer_id="C001", signup_date=date(2024, 1, 1), country="NL")
    ]

    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 28),
            plan="basic",
            monthly_price=30.0,
        ),
        Subscription(
            customer_id="C001",
            start_date=date(2024, 4, 1),  # 32 days after end_date
            end_date=None,
            plan="pro",
            monthly_price=50.0,
        ),
    ]

    churn_data = calculate_monthly_churn(customers, subscriptions)

    # Customer should be counted as churned in February
    feb_churn = next((c for c in churn_data if c.month == "2024-02"), None)
    assert feb_churn is not None
    assert feb_churn.churned_count == 1


def test_churn_exactly_30_days():
    """Edge case: resubscribe exactly 30 days after end_date."""
    customers = [
        Customer(customer_id="C001", signup_date=date(2024, 1, 1), country="NL")
    ]

    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 28),
            plan="basic",
            monthly_price=30.0,
        ),
        Subscription(
            customer_id="C001",
            start_date=date(2024, 3, 29),  # Exactly 30 days
            end_date=None,
            plan="pro",
            monthly_price=50.0,
        ),
    ]

    churn_data = calculate_monthly_churn(customers, subscriptions)

    # 30 days is within grace period - should NOT churn
    feb_churn = next((c for c in churn_data if c.month == "2024-02"), None)
    if feb_churn:
        assert feb_churn.churned_count == 0


def test_cohort_retention_basic():
    """Test basic 3-month retention calculation."""
    customers = [
        Customer(customer_id="C001", signup_date=date(2024, 1, 15), country="NL"),
        Customer(customer_id="C002", signup_date=date(2024, 1, 20), country="DE"),
    ]

    subscriptions = [
        # C001 - active after 3 months
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 15),
            end_date=None,
            plan="basic",
            monthly_price=30.0,
        ),
        # C002 - churned before 3 months
        Subscription(
            customer_id="C002",
            start_date=date(2024, 1, 20),
            end_date=date(2024, 3, 1),
            plan="basic",
            monthly_price=30.0,
        ),
    ]

    cohort_data = calculate_cohort_retention(customers, subscriptions)

    jan_cohort = next((c for c in cohort_data if c.cohort_month == "2024-01"), None)
    assert jan_cohort is not None
    assert jan_cohort.cohort_size == 2
    assert jan_cohort.active_after_3_months == 1
    assert jan_cohort.retention_rate_3m == 0.5


def test_cohort_retention_multiple_cohorts():
    """Test retention across multiple cohorts."""
    customers = [
        Customer(customer_id="C001", signup_date=date(2024, 1, 15), country="NL"),
        Customer(customer_id="C002", signup_date=date(2024, 2, 10), country="DE"),
    ]

    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 15),
            end_date=None,
            plan="basic",
            monthly_price=30.0,
        ),
        Subscription(
            customer_id="C002",
            start_date=date(2024, 2, 10),
            end_date=None,
            plan="pro",
            monthly_price=50.0,
        ),
    ]

    cohort_data = calculate_cohort_retention(customers, subscriptions)

    assert len(cohort_data) == 2

    jan_cohort = next((c for c in cohort_data if c.cohort_month == "2024-01"), None)
    assert jan_cohort.cohort_size == 1
    assert jan_cohort.retention_rate_3m == 1.0

    feb_cohort = next((c for c in cohort_data if c.cohort_month == "2024-02"), None)
    assert feb_cohort.cohort_size == 1
    assert feb_cohort.retention_rate_3m == 1.0


def test_cohort_retention_boundary_date():
    """Edge case: subscription ends exactly at 3-month mark."""
    customers = [
        Customer(customer_id="C001", signup_date=date(2024, 1, 15), country="NL")
    ]

    subscriptions = [
        Subscription(
            customer_id="C001",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 4, 15),  # Ends exactly 3 months later
            plan="basic",
            monthly_price=30.0,
        ),
    ]

    cohort_data = calculate_cohort_retention(customers, subscriptions)

    jan_cohort = next((c for c in cohort_data if c.cohort_month == "2024-01"), None)
    assert jan_cohort is not None
    # Should still be active on 3-month mark (inclusive)
    assert jan_cohort.active_after_3_months == 1
    assert jan_cohort.retention_rate_3m == 1.0


def test_empty_data():
    """Test with empty input data."""
    assert calculate_monthly_mrr([]) == []
    assert calculate_monthly_churn([], []) == []
    assert calculate_cohort_retention([], []) == []
