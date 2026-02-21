"""Business logic for SaaS metrics calculation."""

import logging
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from models import (
    CohortRetention,
    Customer,
    MonthlyChurn,
    MonthlyMRR,
    Subscription,
)

logger = logging.getLogger(__name__)


def calculate_monthly_mrr(subscriptions: list[Subscription]) -> list[MonthlyMRR]:
    """
    Calculate Monthly Recurring Revenue for each calendar month.

    For each month, sums monthly_price of all subscriptions that are active
    during that month. A subscription is active if:
    - start_date <= month
    - end_date is None OR end_date >= month

    Args:
        subscriptions: List of subscription records

    Returns:
        List of MonthlyMRR objects sorted by month
    """
    if not subscriptions:
        return []

    # Find date range
    all_dates = [s.start_date for s in subscriptions]
    all_dates.extend([s.end_date for s in subscriptions if s.end_date])

    min_date = min(all_dates)
    max_date = max(all_dates)

    # Generate all months in range
    current = date(min_date.year, min_date.month, 1)
    end = date(max_date.year, max_date.month, 1)

    monthly_mrr_data = []

    while current <= end:
        # Get last day of current month
        last_day = date(current.year, current.month, monthrange(current.year, current.month)[1])

        # Sum MRR for active subscriptions
        mrr = 0.0
        for sub in subscriptions:
            # Check if subscription is active during this month
            if sub.start_date <= last_day and (
                sub.end_date is None or sub.end_date >= current
            ):
                mrr += sub.monthly_price

        monthly_mrr_data.append(
            MonthlyMRR(month=current.strftime("%Y-%m"), mrr=round(mrr, 2))
        )

        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return monthly_mrr_data


def calculate_monthly_churn(
    customers: list[Customer], subscriptions: list[Subscription]
) -> list[MonthlyChurn]:
    """
    Calculate monthly churned customer count.

    A customer is considered churned in a month if:
    1. They have a subscription that ends in that month (end_date set)
    2. They do NOT start a new subscription within 30 days after end_date

    Args:
        customers: List of customer records
        subscriptions: List of subscription records

    Returns:
        List of MonthlyChurn objects sorted by month
    """
    if not subscriptions:
        return []

    # Group subscriptions by customer
    subs_by_customer = defaultdict(list)
    for sub in subscriptions:
        subs_by_customer[sub.customer_id].append(sub)

    # Sort each customer's subscriptions by start_date
    for customer_id in subs_by_customer:
        subs_by_customer[customer_id].sort(key=lambda s: s.start_date)

    # Track churn events by month
    churn_by_month = defaultdict(int)

    for customer_id, subs in subs_by_customer.items():
        for i, sub in enumerate(subs):
            if sub.end_date is None:
                # Active subscription, no churn
                continue

            # Check if there's a resubscription within 30 days
            resubscribed = False
            for next_sub in subs[i + 1 :]:
                days_gap = (next_sub.start_date - sub.end_date).days
                if days_gap <= 30:
                    resubscribed = True
                    break

            if not resubscribed:
                # Customer churned - record in the month of end_date
                churn_month = sub.end_date.strftime("%Y-%m")
                churn_by_month[churn_month] += 1

    # Find date range from subscriptions
    all_dates = [s.start_date for s in subscriptions]
    all_dates.extend([s.end_date for s in subscriptions if s.end_date])

    if not all_dates:
        return []

    min_date = min(all_dates)
    max_date = max(all_dates)

    # Generate all months with churn data (including zeros)
    current = date(min_date.year, min_date.month, 1)
    end = date(max_date.year, max_date.month, 1)

    monthly_churn_data = []

    while current <= end:
        month_str = current.strftime("%Y-%m")
        churned_count = churn_by_month.get(month_str, 0)

        monthly_churn_data.append(
            MonthlyChurn(month=month_str, churned_count=churned_count)
        )

        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return monthly_churn_data


def calculate_cohort_retention(
    customers: list[Customer], subscriptions: list[Subscription]
) -> list[CohortRetention]:
    """
    Calculate 3-month retention for signup cohorts.

    Groups customers by signup month and calculates:
    - cohort_size: number of customers in cohort
    - active_after_3_months: customers with active subscription 3 months after signup
    - retention_rate_3m: active_after_3_months / cohort_size

    A customer is "active after 3 months" if they have any subscription active
    on or after the date 3 months from their signup date.

    Args:
        customers: List of customer records
        subscriptions: List of subscription records

    Returns:
        List of CohortRetention objects sorted by cohort_month
    """
    if not customers:
        return []

    # Group customers by signup month
    cohorts = defaultdict(list)
    for customer in customers:
        cohort_month = customer.signup_date.strftime("%Y-%m")
        cohorts[cohort_month].append(customer)

    # Group subscriptions by customer
    subs_by_customer = defaultdict(list)
    for sub in subscriptions:
        subs_by_customer[sub.customer_id].append(sub)

    cohort_data = []

    for cohort_month, cohort_customers in sorted(cohorts.items()):
        cohort_size = len(cohort_customers)
        active_after_3m = 0

        for customer in cohort_customers:
            # Calculate date 3 months after signup
            signup = customer.signup_date
            month_3 = signup.month + 3
            year_3 = signup.year + (month_3 - 1) // 12
            month_3 = ((month_3 - 1) % 12) + 1

            # Use last day of the 3rd month
            try:
                day_3 = min(signup.day, monthrange(year_3, month_3)[1])
                target_date = date(year_3, month_3, day_3)
            except ValueError:
                # Handle edge cases
                target_date = date(year_3, month_3, monthrange(year_3, month_3)[1])

            # Check if customer has active subscription on target_date
            customer_subs = subs_by_customer.get(customer.customer_id, [])
            for sub in customer_subs:
                if sub.start_date <= target_date and (
                    sub.end_date is None or sub.end_date >= target_date
                ):
                    active_after_3m += 1
                    break  # Count customer only once

        retention_rate = (
            active_after_3m / cohort_size if cohort_size > 0 else 0.0
        )

        cohort_data.append(
            CohortRetention(
                cohort_month=cohort_month,
                cohort_size=cohort_size,
                active_after_3_months=active_after_3m,
                retention_rate_3m=round(retention_rate, 4),
            )
        )

    return cohort_data


def detect_overlapping_subscriptions(subscriptions: list[Subscription]) -> list[str]:
    """
    Detect overlapping subscriptions for the same customer.

    Returns list of warning messages for overlaps.
    """
    warnings = []

    # Group by customer
    subs_by_customer = defaultdict(list)
    for sub in subscriptions:
        subs_by_customer[sub.customer_id].append(sub)

    for customer_id, subs in subs_by_customer.items():
        if len(subs) < 2:
            continue

        # Sort by start_date
        sorted_subs = sorted(subs, key=lambda s: s.start_date)

        for i in range(len(sorted_subs) - 1):
            current = sorted_subs[i]
            next_sub = sorted_subs[i + 1]

            # Check for overlap
            if current.end_date and next_sub.start_date <= current.end_date:
                warnings.append(
                    f"Customer '{customer_id}' has overlapping subscriptions: "
                    f"{current.start_date} to {current.end_date} overlaps with "
                    f"{next_sub.start_date} to {next_sub.end_date or 'active'}"
                )

    return warnings
