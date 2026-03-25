import random
from datetime import datetime, timedelta
from typing import List

from faker import Faker

from data.models import SupportTicket

fake = Faker()
Faker.seed(42)
random.seed(42)

CATEGORIES = ["API", "Billing", "Feature Request", "Onboarding", "Performance", "Security", "Integration", "Bug"]
PRIORITIES = ["P1", "P2", "P3", "P4"]
PRIORITY_WEIGHTS = [0.05, 0.15, 0.45, 0.35]
STATUSES = ["open", "in_progress", "resolved", "closed"]
STATUS_WEIGHTS = [0.2, 0.15, 0.3, 0.35]

TICKET_TEMPLATES = {
    "API": [
        ("API rate limits causing 429 errors in production", "Our application is hitting rate limits during peak hours. We're seeing 429 responses which is causing downstream failures. This is a critical issue affecting our end users."),
        ("Authentication tokens expiring unexpectedly", "Bearer tokens are expiring before the documented TTL. This is breaking our automated workflows and causing user logouts."),
        ("Webhook payloads not being delivered", "We set up webhooks 3 days ago but have not received a single payload. Our endpoint is returning 200 OK. Please investigate."),
    ],
    "Billing": [
        ("Invoice discrepancy for Q1", "Our invoice shows charges for 50 seats but we only have 35 active users. Please review and issue a credit."),
        ("Unable to update payment method", "The billing portal gives a 500 error when I try to update our credit card. Our card expires next week."),
        ("Unexpected overage charges", "We were charged $2,400 in overage fees but were never warned we were approaching limits. We need this escalated to our account team."),
    ],
    "Feature Request": [
        ("SAML SSO support for enterprise IdP", "We need SAML 2.0 SSO integration with our Okta instance for compliance reasons. This is blocking our enterprise rollout."),
        ("Bulk export of audit logs", "We need to export 12 months of audit logs for a compliance audit. Current UI only allows 30-day exports."),
        ("Role-based access controls for teams", "We need granular RBAC to prevent junior staff from accessing sensitive configuration. This is required by our security policy."),
    ],
    "Onboarding": [
        ("Migration from legacy system not completing", "We've been trying to migrate 50k records for 4 days. The job keeps timing out at around 70%. Need help."),
        ("Training session rescheduled 3 times", "Our onboarding training has been rescheduled twice by your team. Our go-live is in 2 weeks and team is not trained."),
        ("Documentation missing for new API endpoints", "The v3 API docs don't cover the new /reports endpoints that were announced in the changelog. How do we use them?"),
    ],
    "Performance": [
        ("Dashboard load times degraded significantly", "Since last Tuesday, our main dashboard takes 15–25 seconds to load. It used to be under 3 seconds. Affecting all users."),
        ("Reports timing out for large datasets", "Any report covering more than 90 days times out. This is critical for our month-end close process."),
        ("Search returning stale results", "Search results appear to be 20–30 minutes behind. For our use case, we need near-real-time results."),
    ],
    "Security": [
        ("Possible unauthorized access to our account", "We noticed logins from unusual IP addresses in Asia. We don't have any staff in that region. Please investigate and lock down the account."),
        ("Audit log gap detected", "Our compliance team noticed a 4-hour gap in audit logs on March 15. We need to understand what happened."),
        ("Data residency concern flagged by legal", "Our legal team has flagged that customer data may be processed in regions outside our DPA. Need written confirmation of data residency."),
    ],
    "Integration": [
        ("Salesforce sync failing after OAuth refresh", "Our Salesforce integration broke after your OAuth token refresh. CRM data is now out of sync."),
        ("Slack notifications not triggering", "Slack integration worked for 2 months then stopped last week. No changes on our end."),
        ("Zapier integration missing new fields", "New custom fields added to our account are not appearing in the Zapier integration. Blocking several automations."),
    ],
    "Bug": [
        ("Date filter returns incorrect results", "The 'last 30 days' filter appears to be using UTC but our account is set to EST. Data is off by one day."),
        ("CSV export includes deleted records", "Exported CSVs still contain records we deleted 6 months ago. This is causing issues in our data pipelines."),
        ("Mobile app crashes on iOS 17", "The mobile app crashes immediately on launch for all users on iOS 17. This started after your 2.4.1 release."),
    ],
}

FRUSTRATED_DESCRIPTIONS = [
    "This has been going on for over a week with no resolution.",
    "I've opened 3 tickets about this already. This is unacceptable for a paying customer.",
    "Our team is blocked and we're losing money every hour this is down.",
    "We are seriously considering alternatives if this isn't resolved today.",
    "Your support has been completely unresponsive for 5 days.",
]


def generate_tickets(customer_ids: List[str], n: int = 200) -> List[SupportTicket]:
    tickets = []
    for i in range(n):
        customer_id = random.choice(customer_ids)
        category = random.choice(CATEGORIES)
        priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]

        templates = TICKET_TEMPLATES.get(category, TICKET_TEMPLATES["Bug"])
        title, base_description = random.choice(templates)

        # Add frustration signals to ~20% of tickets
        description = base_description
        if random.random() < 0.2:
            description += " " + random.choice(FRUSTRATED_DESCRIPTIONS)

        created_at = datetime.now() - timedelta(days=random.randint(0, 180))

        tickets.append(SupportTicket(
            id=f"tick_{i+1:04d}",
            customer_id=customer_id,
            title=title,
            description=description,
            priority=priority,
            category=category,
            status=status,
            created_at=created_at,
        ))
    return tickets
