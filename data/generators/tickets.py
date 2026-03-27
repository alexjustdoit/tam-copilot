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

# Each template is (title, description). Templates are designed to cover diverse
# situational signals so AI triage can naturally suggest varied tags.
TICKET_TEMPLATES = {
    "API": [
        (
            "API rate limits causing 429 errors in production",
            "Our application is hitting rate limits during peak hours. We're seeing 429 responses which is causing downstream failures for end users. We have no viable workaround at this volume.",
        ),
        (
            "Authentication tokens expiring before documented TTL",
            "Bearer tokens are expiring well before the documented 60-minute TTL. Our automated workflows are failing and users are being logged out mid-session. We have a manual re-auth script running as a stopgap but it's not sustainable.",
        ),
        (
            "Webhook payloads silently dropped — no deliveries in 72 hours",
            "We configured webhooks three days ago and have received zero payloads despite confirmed events. Our endpoint returns 200 OK. Without webhooks our real-time pipeline is completely stalled.",
        ),
        (
            "API v2 migration breaking change not in release notes",
            "The v2 migration introduced a breaking change to the /events endpoint response schema that was not documented. Our integration broke in production. We need either a rollback path or a hotfix within our maintenance window per our SLA.",
        ),
        (
            "API response times spiking above SLA threshold",
            "P99 response times on the /data endpoint have been above 2,000ms for the past 48 hours. Our contract specifies a 500ms SLA. We are now tracking this as a potential breach and have alerted our VP of Engineering.",
        ),
        (
            "Undocumented field removed from API response breaking our parser",
            "A field that has been in the API response for 18 months was silently removed. Our data pipeline parser failed because of this. There is no mention of this in the changelog. We need guidance on which fields are considered stable contract.",
        ),
    ],
    "Billing": [
        (
            "Invoice shows charges for 15 seats we don't have",
            "Our Q2 invoice shows charges for 50 seats but our contract is for 35. The discrepancy is $1,800. Please review and issue a credit note.",
        ),
        (
            "Billing portal returning 500 error — card expires in 4 days",
            "The billing portal gives a server error when updating our payment method. Our card on file expires Friday. If payment fails we risk a service interruption which would violate our SLA commitments to our own customers.",
        ),
        (
            "Overage charges with no prior warning — CFO escalating",
            "We were invoiced $4,200 in overage fees without any threshold alert. We were never notified we were approaching limits. Our CFO is asking us to justify this charge and is questioning the renewal. We need a full account review.",
        ),
        (
            "Multi-year contract pricing not reflected in invoices",
            "We signed a 3-year agreement with locked pricing in January but our last two invoices show list price. The delta is $6,500. This was supposed to be handled at contract close. We have our QBR next month and this needs to be resolved before then.",
        ),
        (
            "Tax exemption certificate not applied for 6 months",
            "We submitted our tax exemption certificate in October. Six months of invoices have all included sales tax that should have been exempt. This is a significant overpayment that needs to be corrected and credited.",
        ),
    ],
    "Feature Request": [
        (
            "SAML 2.0 SSO required for enterprise compliance rollout",
            "We need SAML 2.0 SSO integration with our Okta instance. This is a hard requirement from our security team and is blocking our enterprise-wide rollout. We have 200 users waiting on this.",
        ),
        (
            "Bulk audit log export needed for compliance audit",
            "We need to export 12 months of audit logs for an external compliance audit due in 3 weeks. The UI only allows 30-day windows. Currently manually stitching together 12 exports as a workaround — this is error-prone.",
        ),
        (
            "Granular RBAC required — junior staff accessing sensitive config",
            "We need field-level and section-level access controls. Currently we cannot prevent junior staff from viewing sensitive billing and configuration data. This is a policy violation. We are using a separate shared account as a workaround.",
        ),
        (
            "Custom webhook event types not configurable",
            "We need to subscribe to a subset of event types but the current webhook config sends all events. We are filtering on our end which is creating a significant processing overhead. This should be a platform-level capability.",
        ),
        (
            "No API for bulk record operations — blocking automation initiative",
            "Your API only supports single-record writes. We need to update 10,000 records monthly and are currently scripting individual API calls overnight. This is fragile and slow. A bulk write endpoint is essential for our automation roadmap.",
        ),
        (
            "Advanced custom dashboards required for executive reporting",
            "Leadership needs configurable dashboards with our own KPIs for monthly business reviews. The current reporting module is not flexible enough. We are exporting to spreadsheets and building charts manually every month — this is a significant overhead we need to eliminate.",
        ),
    ],
    "Onboarding": [
        (
            "Data migration job failing at 70% — go-live in 10 days",
            "We have been trying to migrate 85,000 records for a week. The job times out at around 70% every time. Our contractual go-live date is in 10 days. If we miss this we will be in breach of our customer commitments.",
        ),
        (
            "Onboarding training rescheduled three times by vendor",
            "Our implementation training has been rescheduled twice by your team and is now 3 weeks behind schedule. Our go-live is in two weeks and our 40-person team is untrained. This is a direct risk to our launch.",
        ),
        (
            "v3 API documentation missing for key endpoints",
            "The v3 docs do not cover the new /analytics and /reports endpoints announced in the changelog. Our developers cannot integrate these features. We have submitted two support tickets previously with no resolution.",
        ),
        (
            "Platform adoption stalled — only 18% of licensed seats active after 60 days",
            "We are 60 days post-launch with only 18% seat activation. Our team finds the interface unintuitive and we lack training resources for the advanced features. Our renewal is in 5 months and we need to demonstrate value to leadership by then.",
        ),
        (
            "Critical go-live dependency blocked on vendor-side configuration",
            "Our go-live is blocked on a vendor-side IP allowlist configuration that was submitted 2 weeks ago. Our CTO has been notified. Every day of delay is costing us approximately $3,000 in operational overhead.",
        ),
    ],
    "Performance": [
        (
            "Dashboard load times degraded from 2s to 25s",
            "Since last Tuesday, our main dashboard takes 15–25 seconds to load. It used to be under 2 seconds. This is affecting all 80 of our active users and significantly impacting productivity.",
        ),
        (
            "Month-end reports timing out — finance team blocked",
            "Any report covering more than 90 days times out with a 504 error. Our month-end close process requires 6-month and 12-month reports. Our finance team is completely blocked and this has happened for the second consecutive month-end.",
        ),
        (
            "Search returning results that are 30 minutes stale",
            "Search results are consistently 20–30 minutes behind real-time data. For our operations use case we need near-real-time search. We have a manual refresh workaround but it is impractical at scale.",
        ),
        (
            "API latency spiking during business hours — SLA at risk",
            "Our monitoring shows P95 API latency spiking to 3–5 seconds during 9am–5pm EST. Our SLA requires sub-500ms P95. We have notified our internal stakeholders and are tracking this as a potential breach.",
        ),
        (
            "Third performance degradation event this month",
            "This is the third time this month we have experienced platform-wide slowdowns. Each incident has lasted 2–4 hours. We have lost confidence in the platform's reliability. Our leadership team is now involved and we need a root cause analysis and remediation plan.",
        ),
    ],
    "Security": [
        (
            "Unauthorized logins from unrecognized IPs — possible breach",
            "Our audit logs show 14 successful logins from IP ranges in Southeast Asia over the past 48 hours. We have no staff in that region. We need immediate account lockdown, a full session audit, and a breach assessment. Our CISO has been notified.",
        ),
        (
            "4-hour audit log gap on March 15 — compliance at risk",
            "Our compliance team identified a 4-hour gap in audit log records on March 15. We have a SOC 2 audit in 6 weeks and cannot have unexplained log gaps. We need a complete explanation of what occurred and written confirmation for our auditors.",
        ),
        (
            "Legal flagged data residency outside contracted region",
            "Our DPA restricts data processing to EU regions. Our legal team has identified evidence that data may be processed in US-East. We need written confirmation of data residency and a remediation plan within 5 business days or we will need to escalate to our DPO.",
        ),
        (
            "Critical vulnerability in your SDK — security team escalating",
            "A CVE was published yesterday affecting your SDK versions 2.1–2.8. We are running 2.6 in production. We need an emergency patch and guidance on mitigation steps. Our security team is treating this as P0 and our CTO is aware.",
        ),
        (
            "User sessions not expiring after configured timeout",
            "We have configured a 30-minute session timeout but sessions are persisting for several hours. This violates our internal security policy and was flagged in our last internal security audit. We need this corrected before our next audit cycle.",
        ),
        (
            "Security questionnaire reveals gaps in your vendor controls",
            "Our annual vendor security review has identified gaps in your SOC 2 report related to access control and incident response. Our security team requires written responses to 12 specific control questions before we can proceed with our renewal.",
        ),
    ],
    "Integration": [
        (
            "Salesforce sync failing after OAuth token refresh",
            "Our Salesforce integration broke after your platform's OAuth token refresh last Thursday. CRM data is now 5 days out of sync. Our sales team is working from stale data. This has happened twice before after platform updates.",
        ),
        (
            "Slack notifications stopped triggering without any config change",
            "Slack integration worked reliably for 3 months then stopped last week. We made no configuration changes on our end. We have a manual notification workflow as a fallback but it requires someone to check the platform every hour.",
        ),
        (
            "New custom fields not appearing in Zapier integration",
            "Custom fields added to our account 2 weeks ago are not showing up in the Zapier integration field list. This is blocking 4 active automations that our operations team depends on daily.",
        ),
        (
            "Nightly data sync producing duplicate records in our data warehouse",
            "Our nightly sync job has been creating duplicate records in our data warehouse for 3 weeks. We have approximately 12,000 duplicates that need to be cleaned up. We identified a workaround involving a deduplication script but it runs for 2 hours each morning.",
        ),
        (
            "OAuth token exchange intermittently failing — affecting 1 in 20 logins",
            "Approximately 5% of SSO login attempts fail with an OAuth token exchange error. Users have to retry login 1–3 times to get through. This has been reported by users across 4 different departments. We have seen this behavior before after platform releases.",
        ),
    ],
    "Bug": [
        (
            "Date filter using UTC — data off by one day for EST users",
            "The 'last 30 days' date filter appears to be applying UTC boundaries. Our account is configured for EST. Reports are consistently missing the most recent day's data for our US team.",
        ),
        (
            "CSV export contains records deleted over 6 months ago",
            "Exported CSVs still contain records we deleted in Q3 last year. This is corrupting our downstream data pipelines and causing failures in our ETL process. We have verified the records show as deleted in the UI.",
        ),
        (
            "Mobile app crashes on launch for all iOS 17 users",
            "The mobile app crashes immediately on launch for all users on iOS 17. This started after your 2.4.1 release last week. 35 of our field team members are affected and cannot access the platform from mobile. They are sharing one iPad running iOS 16 as a workaround.",
        ),
        (
            "Role change not propagating — users retaining old permissions",
            "When we change a user's role, they retain their old permissions for an indeterminate period. In one case a demoted user retained admin access for over 48 hours. This is a security concern and was flagged by our internal audit team.",
        ),
        (
            "Export produces corrupted files intermittently",
            "Approximately 1 in 5 PDF exports produces a corrupted file that cannot be opened. There is no error message — the file downloads normally but fails to open. We cannot predict when it will happen. We are running the export multiple times and checking each file manually.",
        ),
        (
            "Search returning records from other account — possible data isolation issue",
            "A user on our account ran a search and received results that appear to belong to a different organization. Customer names, emails and account IDs are visible that we have no relationship with. We have immediately restricted access pending investigation. Our CISO is aware.",
        ),
    ],
}

# Context modifiers — appended to base descriptions to add situational variety
# Each pool maps to signals that would naturally invoke certain tags during triage
FRUSTRATION_SIGNALS = [
    "This has been going on for over a week with no resolution.",
    "I've opened multiple tickets about this. This is unacceptable for an enterprise customer.",
    "Our team is blocked and we're losing money every hour this is unresolved.",
    "We are actively evaluating alternatives if this isn't resolved by end of week.",
    "Your support has been unresponsive for 5 days. This needs to be escalated.",
]

EXEC_SIGNALS = [
    "Our VP of Engineering has been notified and is asking for daily status updates.",
    "Our CEO is aware of this issue and has asked me to escalate formally.",
    "This has been raised in our leadership standup. We need a named owner on your side.",
    "Our board has visibility on this due to the customer impact.",
    "Our CTO is tracking this and expects a written status update by EOD.",
]

SLA_SIGNALS = [
    "Our SLA requires resolution within 4 hours for severity 1 issues.",
    "Per our contract, we are entitled to service credits if this is not resolved within the agreed window.",
    "We are approaching the SLA breach threshold. Please confirm receipt and ETA.",
    "Our MSA includes uptime guarantees that are now at risk.",
]

RECURRING_SIGNALS = [
    "This is the third time we have experienced this exact issue in 90 days.",
    "We raised the same problem in ticket #1089 last month. That resolution did not hold.",
    "This is a recurring pattern that we have documented across at least 4 incidents.",
    "We have seen this before — same symptoms, same timing. A permanent fix is needed.",
]

WORKAROUND_SIGNALS = [
    "We have a manual workaround in place but it is not sustainable at our scale.",
    "Our team has been working around this for weeks — it's creating significant overhead.",
    "We've built an internal script to compensate but this should be handled by the platform.",
]

BLOCKER_SIGNALS = [
    "We are completely blocked on this and cannot proceed with our planned work.",
    "This is a hard blocker for our Q3 initiative. Every day of delay has a cost.",
    "Our team has nothing else they can move forward on until this is resolved.",
]


def _pick_modifier() -> str:
    """Randomly return a context modifier or empty string. Most tickets get 0-1 modifiers."""
    roll = random.random()
    if roll < 0.45:
        return ""  # 45% — no modifier
    pool = random.choices(
        [FRUSTRATION_SIGNALS, EXEC_SIGNALS, SLA_SIGNALS, RECURRING_SIGNALS, WORKAROUND_SIGNALS, BLOCKER_SIGNALS],
        weights=[0.30, 0.15, 0.15, 0.15, 0.15, 0.10],
    )[0]
    return " " + random.choice(pool)


def generate_tickets(customer_ids: List[str], n: int = 500) -> List[SupportTicket]:
    tickets = []
    for i in range(n):
        customer_id = random.choice(customer_ids)
        category = random.choice(CATEGORIES)
        priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]

        templates = TICKET_TEMPLATES.get(category, TICKET_TEMPLATES["Bug"])
        title, base_description = random.choice(templates)

        description = base_description + _pick_modifier()
        created_at = datetime.now() - timedelta(days=random.randint(0, 365))

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
