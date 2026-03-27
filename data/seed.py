"""
Run once to generate fixture data:
    python data/seed.py
"""
import json
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generators.customers import generate_customers
from data.generators.tickets import generate_tickets
from data.generators.usage import generate_usage
from data.generators.subscriptions import generate_subscriptions

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def seed():
    FIXTURES_DIR.mkdir(exist_ok=True)

    print("Generating customers...")
    customers = generate_customers(50)
    customer_ids = [c.id for c in customers]

    print("Generating tickets...")
    tickets = generate_tickets(customer_ids, 500)

    print("Generating usage metrics...")
    usage = generate_usage(customers, 12)

    print("Generating subscriptions...")
    subscriptions = generate_subscriptions(customers)

    print("Writing fixtures...")
    (FIXTURES_DIR / "customers.json").write_text(
        json.dumps([c.model_dump(mode="json") for c in customers], indent=2)
    )
    (FIXTURES_DIR / "tickets.json").write_text(
        json.dumps([t.model_dump(mode="json") for t in tickets], indent=2)
    )
    (FIXTURES_DIR / "usage.json").write_text(
        json.dumps([u.model_dump(mode="json") for u in usage], indent=2)
    )
    (FIXTURES_DIR / "subscriptions.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in subscriptions], indent=2)
    )

    print(f"Done. Generated:")
    print(f"  {len(customers)} customers")
    print(f"  {len(tickets)} tickets")
    print(f"  {len(usage)} usage records")
    print(f"  {len(subscriptions)} subscriptions")
    print(f"  Fixtures saved to {FIXTURES_DIR}/")


if __name__ == "__main__":
    seed()
