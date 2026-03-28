"""
TAM Copilot — Entry Point
Run with: streamlit run app/streamlit_app.py

NOTE FOR DEVELOPERS: Adding a new page is a two-step process:
  1. Create the page file in app/pages/
  2. Register it in the st.navigation() list at the bottom of this file
Streamlit will NOT auto-discover pages when st.navigation() is in use.
"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

import pandas as pd
import streamlit as st

import config  # noqa: F401 — loads .env via load_dotenv()
from app.components.sidebar import render_sidebar_header, render_sidebar_footer
from data.models import Customer, Subscription, SupportTicket, UsageMetrics

st.set_page_config(
    page_title="TAM Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# On the first render of a fresh session (e.g. after server restart), the
# position="hidden" sidebar layout can produce a broken frame before
# Streamlit's frontend fully initialises. Triggering an immediate rerun
# discards that first execution's output entirely — the frontend never sees
# the broken state — and the second pass renders the full sidebar correctly.
if not st.session_state.get("_initialized"):
    st.session_state["_initialized"] = True
    st.rerun()

st.markdown("""
<style>
/* Reduce default top padding on every page's main content area */
.main .block-container,
.stMainBlockContainer,
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"] {
    padding-top: 1.5rem !important;
}

/* Sidebar: hide the logo spacer that creates unwanted top padding */
[data-testid="stLogoSpacer"] {
    display: none !important;
}

/* Sidebar: flex chain — must propagate through every ancestor level
   for the spacer's flex:1 to push the footer to the bottom */
[data-testid="stSidebarContent"] {
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stSidebarUserContent"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    padding-top: 0.5rem !important;
}
[data-testid="stSidebarUserContent"] > div:first-child {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stSidebarUserContent"] > div:first-child > [data-testid="stVerticalBlock"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}

/* Spacer element grows to fill remaining space, pushing LLM footer down */
.element-container:has(.sidebar-footer-spacer) {
    flex: 1 !important;
}
</style>""", unsafe_allow_html=True)

render_sidebar_header()


# ---------- Data loading (cached) ----------

@st.cache_data
def load_all_data():
    fixtures = Path(__file__).parent.parent / "data" / "fixtures"
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((fixtures / "tickets.json").read_text())]
    usage = [UsageMetrics(**u) for u in json.loads((fixtures / "usage.json").read_text())]
    subscriptions = [Subscription(**s) for s in json.loads((fixtures / "subscriptions.json").read_text())]
    return customers, tickets, usage, subscriptions


# ---------- Overview Page ----------

def overview():
    from datetime import date as _date

    try:
        customers, tickets, usage, subscriptions = load_all_data()
        data_loaded = True
    except FileNotFoundError:
        data_loaded = False

    st.title("TAM Copilot")
    st.markdown("""
<style>
[data-testid="stDivider"] { margin-top: -0.5rem; margin-bottom: -0.5rem; }
</style>""", unsafe_allow_html=True)

    if not data_loaded:
        st.error("Fixture data not found. Run `python data/seed.py` to generate demo data.")
        st.code("python data/seed.py", language="bash")
        st.stop()

    sub_map = {s.customer_id: s for s in subscriptions}
    ticket_map: dict[str, list] = {}
    for t in tickets:
        ticket_map.setdefault(t.customer_id, []).append(t)

    open_tickets = [t for t in tickets if t.status in ("open", "in_progress")]
    tagged_open = [t for t in open_tickets if t.tags]
    triage_coverage = round(len(tagged_open) / len(open_tickets) * 100) if open_tickets else 0
    total_arr = sum(c.arr for c in customers)
    renewal_90 = [c for c in customers if 0 <= (_date.today() - c.renewal_date).days * -1 <= 90
                  or 0 <= (c.renewal_date - _date.today()).days <= 90]
    arr_at_renewal = sum(c.arr for c in renewal_90)

    # ── Top-line stats ─────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Customers", len(customers))
    with col2:
        enterprise_count = sum(1 for c in customers if c.tier == "Enterprise")
        st.metric("Enterprise", enterprise_count)
    with col3:
        st.metric("Total ARR", f"${total_arr / 1_000_000:.1f}M")
    with col4:
        st.metric("Open Tickets", len(open_tickets))
    with col5:
        st.metric("Triage Coverage", f"{triage_coverage}%")
    with col6:
        st.metric("ARR Renewing (90d)", f"${arr_at_renewal / 1_000_000:.1f}M")

    st.divider()

    # ── Needs Attention ────────────────────────────────────────────────────────
    st.subheader("Needs Attention")

    _all_segments = ["Enterprise", "Mid-Market", "SMB"]
    _all_tams = sorted(set(c.tam_owner for c in customers))
    if "filter_segments" not in st.session_state:
        st.session_state["filter_segments"] = _all_segments
    if "filter_tams" not in st.session_state:
        st.session_state["filter_tams"] = _all_tams
    else:
        st.session_state["filter_tams"] = [t for t in st.session_state["filter_tams"] if t in _all_tams]

    col1, col2 = st.columns([1, 3])
    with col1:
        sel_segments = st.multiselect("Segment", _all_segments, default=st.session_state["filter_segments"])
        st.session_state["filter_segments"] = sel_segments
    with col2:
        sel_tams = st.multiselect("TAM Owner", _all_tams, default=st.session_state["filter_tams"])
        st.session_state["filter_tams"] = sel_tams

    attention_rows = []
    for c in customers:
        if c.tier not in sel_segments:
            continue
        if c.tam_owner not in (sel_tams if sel_tams else _all_tams):
            continue
        cust_tickets = ticket_map.get(c.id, [])
        sub = sub_map.get(c.id)
        days_to_renewal = (c.renewal_date - _date.today()).days
        p1p2_open = [t for t in cust_tickets if t.priority in ("P1", "P2") and t.status in ("open", "in_progress")]
        seat_util = (sub.seats_used / sub.seats_purchased) if sub and sub.seats_purchased > 0 else None

        flags = []
        if p1p2_open:
            flags.append(f"🔴 {len(p1p2_open)} P1/P2 open")
        if 0 <= days_to_renewal <= 60:
            flags.append(f"🟠 Renewing in {days_to_renewal}d")
        if seat_util is not None and seat_util < 0.5 and days_to_renewal <= 90:
            flags.append("🟡 Low utilization")

        if flags:
            attention_rows.append({
                "Company": c.company_name,
                "Segment": c.tier,
                "TAM": c.tam_owner,
                "ARR": f"${c.arr:,.0f}",
                "Flags": "  ".join(flags),
            })

    if attention_rows:
        attention_rows.sort(key=lambda r: (
            0 if "🔴" in r["Flags"] else (1 if "🟠" in r["Flags"] else 2)
        ))
        st.dataframe(pd.DataFrame(attention_rows), use_container_width=True, hide_index=True, height=400)
    else:
        st.success("No accounts currently flagged — portfolio looks healthy.")

    st.divider()

    # ── Feature overview ───────────────────────────────────────────────────────
    st.subheader("What TAM Copilot Does")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**AI-Powered Ticket Triage:** Classifies priority, detects sentiment, assesses escalation risk, and drafts responses for every support ticket.

**Customer Health Scoring:** Composite 0–100 score combining usage trends, support history, and commercial signals.

**Churn Risk Detection:** Identifies at-risk accounts with specific risk factors and TAM action recommendations.
""")
    with col2:
        st.markdown("""
**QBR Preparation:** Auto-generates executive-ready Quarterly Business Review talking points from 12 months of data.

**Expansion Intelligence:** Finds upsell and cross-sell opportunities by analyzing feature gaps vs. industry benchmarks.
""")



# ---------- Navigation ----------
# NOTE FOR DEVELOPERS: Adding a new page is a two-step process:
#   1. Create the page file in app/pages/
#   2. Add a st.Page() entry to the list below
# Streamlit will NOT auto-discover pages when st.navigation() is in use.

main_pages = [
    st.Page(overview, title="Overview", default=True),
    st.Page("pages/1_Customers.py", title="Customers"),
    st.Page("pages/2_Ticket_Triage.py", title="Ticket Triage"),
    st.Page("pages/3_Churn_Risk.py", title="Churn Risk"),
    st.Page("pages/4_QBR_Prep.py", title="QBR Preparation"),
    st.Page("pages/6_Ticket_Insights.py", title="Ticket Insights"),
    st.Page("pages/7_Management_Insights.py", title="Management Insights"),
    st.Page("pages/8_Expansion_Intelligence.py", title="Expansion Intelligence"),
]

dev_pages = [
    st.Page("pages/5_Eval_Dashboard.py", title="Eval Dashboard"),
    st.Page("pages/9_Technical_Info.py", title="Technical Info"),
]

# position="hidden" suppresses Streamlit's automatic nav injection so we can
# render page links manually after the branding, giving us full layout control.
pg = st.navigation(main_pages + dev_pages, position="hidden")

with st.sidebar:
    for page in main_pages:
        st.page_link(page)
    with st.expander("Developers"):
        for page in dev_pages:
            st.page_link(page)

pg.run()
render_sidebar_footer()
