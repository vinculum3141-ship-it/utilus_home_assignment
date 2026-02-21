"""Data models for SaaS analytics."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Customer(BaseModel):
    """Customer record."""

    customer_id: str
    signup_date: date
    country: str

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Normalize country codes to uppercase."""
        return v.strip().upper() if v else v


class Subscription(BaseModel):
    """Subscription record."""

    customer_id: str
    start_date: date
    end_date: Optional[date] = None
    plan: str
    monthly_price: float

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        """Normalize plan names."""
        return v.strip().lower()

    @field_validator("monthly_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Ensure price is non-negative."""
        if v < 0:
            raise ValueError("Monthly price cannot be negative")
        return v

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active (no end_date)."""
        return self.end_date is None


class MonthlyMRR(BaseModel):
    """Monthly recurring revenue metric."""

    month: str = Field(description="YYYY-MM format")
    mrr: float


class MonthlyChurn(BaseModel):
    """Monthly churn count."""

    month: str = Field(description="YYYY-MM format")
    churned_count: int


class CohortRetention(BaseModel):
    """Cohort retention metric."""

    cohort_month: str = Field(description="YYYY-MM format")
    cohort_size: int
    active_after_3_months: int
    retention_rate_3m: float


class AnalyticsReport(BaseModel):
    """Complete analytics report output."""

    metadata: dict
    monthly_mrr: list[MonthlyMRR]
    monthly_churn: list[MonthlyChurn]
    cohort_retention: list[CohortRetention]
