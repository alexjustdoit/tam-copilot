import random
from typing import List

from data.models import Subscription

random.seed(42)

PLANS = {
    "Enterprise": ["Enterprise", "Enterprise Plus", "Enterprise Premier"],
    "Mid-Market": ["Professional", "Professional Plus", "Business"],
    "SMB": ["Starter", "Growth", "Essentials"],
}


def generate_subscriptions(customers: list) -> List[Subscription]:
    subscriptions = []
    for customer in customers:
        tier = customer.tier
        plan = random.choice(PLANS[tier])

        # Seat utilization: healthy = 70-95%, at-risk = <50% or >100%
        seats_purchased = max(10, int(customer.employees * random.uniform(0.3, 0.9)))

        utilization_scenario = random.choices(
            ["healthy", "under_utilized", "over_utilized"],
            weights=[0.55, 0.30, 0.15],
        )[0]

        if utilization_scenario == "healthy":
            seats_used = int(seats_purchased * random.uniform(0.65, 0.95))
        elif utilization_scenario == "under_utilized":
            seats_used = int(seats_purchased * random.uniform(0.2, 0.49))
        else:
            seats_used = int(seats_purchased * random.uniform(1.01, 1.25))

        mrr = round(customer.arr / 12, 2)
        auto_renew = random.random() < 0.65

        subscriptions.append(Subscription(
            customer_id=customer.id,
            plan=plan,
            seats_purchased=seats_purchased,
            seats_used=seats_used,
            mrr=mrr,
            renewal_date=customer.renewal_date,
            auto_renew=auto_renew,
        ))
    return subscriptions
