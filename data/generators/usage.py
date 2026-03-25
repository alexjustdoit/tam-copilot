import random
from datetime import date
from typing import List

from data.models import UsageMetrics

random.seed(42)

ALL_FEATURES = [
    "dashboard", "reports", "api_access", "webhooks", "sso", "audit_logs",
    "bulk_export", "custom_fields", "automations", "integrations",
    "mobile_app", "advanced_analytics", "data_retention", "rbac",
]

TIER_BASE_DAU = {
    "Enterprise": (500, 5000),
    "Mid-Market": (50, 499),
    "SMB": (5, 49),
}

TREND_TYPES = ["growing", "stable", "declining"]
TREND_WEIGHTS = [0.35, 0.45, 0.20]


def generate_usage(customers: list, months: int = 12) -> List[UsageMetrics]:
    records = []
    today = date.today()

    for customer in customers:
        tier = customer.tier
        dau_min, dau_max = TIER_BASE_DAU[tier]
        base_dau = random.randint(dau_min, dau_max)

        trend = random.choices(TREND_TYPES, weights=TREND_WEIGHTS)[0]
        features_count = {"Enterprise": 8, "Mid-Market": 5, "SMB": 3}[tier]
        adopted = random.sample(ALL_FEATURES, k=min(features_count, len(ALL_FEATURES)))

        for m in range(months):
            # Month offset: m=0 is 11 months ago, m=11 is current month
            month_offset = months - 1 - m
            month = date(today.year, today.month, 1)
            # Move back by month_offset months
            for _ in range(month_offset):
                if month.month == 1:
                    month = date(month.year - 1, 12, 1)
                else:
                    month = date(month.year, month.month - 1, 1)

            if trend == "growing":
                multiplier = 0.7 + (m / months) * 0.6 + random.uniform(-0.05, 0.05)
            elif trend == "declining":
                multiplier = 1.2 - (m / months) * 0.5 + random.uniform(-0.05, 0.05)
            else:
                multiplier = 1.0 + random.uniform(-0.1, 0.1)

            multiplier = max(0.1, multiplier)
            dau = max(1, int(base_dau * multiplier))
            mau = max(dau, int(dau * random.uniform(3.0, 6.0)))
            api_calls = dau * random.randint(10, 100)
            login_freq = round(random.uniform(0.5, 5.0), 2)

            # Occasionally add a new feature adoption
            current_features = list(adopted)
            if trend == "growing" and m > months // 2 and random.random() < 0.3:
                extras = [f for f in ALL_FEATURES if f not in current_features]
                if extras:
                    current_features.append(random.choice(extras))

            records.append(UsageMetrics(
                customer_id=customer.id,
                month=month,
                dau=dau,
                mau=mau,
                api_calls=api_calls,
                features_adopted=current_features,
                login_frequency=login_freq,
            ))
    return records
