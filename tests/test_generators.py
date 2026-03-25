import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generators.customers import generate_customers
from data.generators.tickets import generate_tickets
from data.generators.usage import generate_usage
from data.generators.subscriptions import generate_subscriptions
from data.models import Customer, SupportTicket, UsageMetrics, Subscription


def test_generate_customers():
    customers = generate_customers(10)
    assert len(customers) == 10
    assert all(isinstance(c, Customer) for c in customers)
    assert all(c.arr > 0 for c in customers)
    assert all(c.tier in ("Enterprise", "Mid-Market", "SMB") for c in customers)
    assert all(c.renewal_date > c.contract_start for c in customers)


def test_customer_ids_unique():
    customers = generate_customers(50)
    ids = [c.id for c in customers]
    assert len(ids) == len(set(ids))


def test_generate_tickets():
    customers = generate_customers(10)
    ids = [c.id for c in customers]
    tickets = generate_tickets(ids, 50)
    assert len(tickets) == 50
    assert all(isinstance(t, SupportTicket) for t in tickets)
    assert all(t.customer_id in ids for t in tickets)
    assert all(t.priority in ("P1", "P2", "P3", "P4") for t in tickets)


def test_ticket_ids_unique():
    customers = generate_customers(5)
    ids = [c.id for c in customers]
    tickets = generate_tickets(ids, 100)
    ticket_ids = [t.id for t in tickets]
    assert len(ticket_ids) == len(set(ticket_ids))


def test_generate_usage():
    customers = generate_customers(5)
    records = generate_usage(customers, 12)
    assert len(records) == 5 * 12
    assert all(isinstance(u, UsageMetrics) for u in records)
    assert all(u.dau > 0 for u in records)
    assert all(u.mau >= u.dau for u in records)


def test_generate_subscriptions():
    customers = generate_customers(10)
    subs = generate_subscriptions(customers)
    assert len(subs) == 10
    assert all(isinstance(s, Subscription) for s in subs)
    assert all(s.mrr > 0 for s in subs)
    assert all(s.seats_purchased > 0 for s in subs)


def test_referential_integrity():
    """Tickets must reference valid customer IDs."""
    customers = generate_customers(20)
    ids = {c.id for c in customers}
    tickets = generate_tickets(list(ids), 100)
    assert all(t.customer_id in ids for t in tickets)

    subs = generate_subscriptions(customers)
    assert all(s.customer_id in ids for s in subs)
