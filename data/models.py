from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Customer(BaseModel):
    id: str
    company_name: str
    industry: str  # SaaS, FinTech, Healthcare, Retail, etc.
    tier: Literal["Enterprise", "Mid-Market", "SMB"]
    arr: float  # Annual Recurring Revenue
    employees: int
    tam_owner: str
    contract_start: date
    renewal_date: date


class SupportTicket(BaseModel):
    id: str
    customer_id: str
    title: str
    description: str
    priority: Literal["P1", "P2", "P3", "P4"]
    category: str  # "API", "Billing", "Feature Request", "Onboarding", etc.
    status: Literal["open", "in_progress", "resolved", "closed"]
    created_at: datetime


class UsageMetrics(BaseModel):
    customer_id: str
    month: date
    dau: int
    mau: int
    api_calls: int
    features_adopted: List[str]
    login_frequency: float  # avg logins/user/week


class Subscription(BaseModel):
    customer_id: str
    plan: str
    seats_purchased: int
    seats_used: int  # seat utilization = churn signal
    mrr: float
    renewal_date: date
    auto_renew: bool
