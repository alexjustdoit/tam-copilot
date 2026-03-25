import random
from datetime import date, timedelta
from typing import List

from faker import Faker

from data.models import Customer

fake = Faker()
Faker.seed(42)
random.seed(42)

INDUSTRIES = ["SaaS", "FinTech", "Healthcare", "Retail", "Manufacturing", "Logistics", "EdTech", "Media"]
TIERS = ["Enterprise", "Mid-Market", "SMB"]
TIER_WEIGHTS = [0.2, 0.4, 0.4]
TAM_OWNERS = ["Sarah Chen", "Marcus Johnson", "Priya Patel", "Tom Kowalski", "Elena Vasquez"]

TIER_ARR = {
    "Enterprise": (100_000, 500_000),
    "Mid-Market": (20_000, 99_999),
    "SMB": (5_000, 19_999),
}

TIER_EMPLOYEES = {
    "Enterprise": (500, 10_000),
    "Mid-Market": (100, 499),
    "SMB": (10, 99),
}


def generate_customers(n: int = 50) -> List[Customer]:
    customers = []
    for i in range(n):
        tier = random.choices(TIERS, weights=TIER_WEIGHTS)[0]
        arr_min, arr_max = TIER_ARR[tier]
        emp_min, emp_max = TIER_EMPLOYEES[tier]

        # Contract start: 1–3 years ago
        contract_start = date.today() - timedelta(days=random.randint(30, 1095))
        # Renewal: 1–18 months from now (some near-term for churn risk demos)
        renewal_date = date.today() + timedelta(days=random.randint(14, 540))

        customers.append(Customer(
            id=f"cust_{i+1:03d}",
            company_name=fake.company(),
            industry=random.choice(INDUSTRIES),
            tier=tier,
            arr=round(random.uniform(arr_min, arr_max), 2),
            employees=random.randint(emp_min, emp_max),
            tam_owner=random.choice(TAM_OWNERS),
            contract_start=contract_start,
            renewal_date=renewal_date,
        ))
    return customers
