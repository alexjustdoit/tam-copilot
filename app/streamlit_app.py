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
    try:
        customers, tickets, usage, subscriptions = load_all_data()
        data_loaded = True
    except FileNotFoundError:
        data_loaded = False

    st.title("TAM Copilot")
    st.subheader("AI-Powered Technical Account Management Dashboard")

    if not data_loaded:
        st.error("Fixture data not found. Run `python data/seed.py` to generate demo data.")
        st.code("python data/seed.py", language="bash")
        st.stop()

    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Customers", len(customers))
    with col2:
        open_tickets = sum(1 for t in tickets if t.status in ("open", "in_progress"))
        st.metric("Open Tickets", open_tickets)
    with col3:
        total_arr = sum(c.arr for c in customers)
        st.metric("Total ARR", f"${total_arr:,.0f}")
    with col4:
        enterprise_count = sum(1 for c in customers if c.tier == "Enterprise")
        st.metric("Enterprise Accounts", enterprise_count)

    st.divider()

    # Feature overview
    st.subheader("What TAM Copilot Does")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**AI-Powered Ticket Triage**
Classifies priority, detects sentiment, assesses escalation risk, and drafts responses for every support ticket.

**Customer Health Scoring**
Composite 0–100 score combining usage trends, support history, and commercial signals.

**Churn Risk Detection**
Identifies at-risk accounts with specific risk factors and TAM action recommendations.
""")
    with col2:
        st.markdown("""
**QBR Preparation**
Auto-generates executive-ready Quarterly Business Review talking points from 12 months of data.

**Expansion Intelligence**
Finds upsell and cross-sell opportunities by analyzing feature gaps vs. industry benchmarks.
""")

    st.divider()

    # Provider capabilities
    st.subheader("LLM Provider Architecture")
    data = {
        "Provider": ["Ollama (local)", "GPT-5.4-nano", "Claude Haiku 4.5"],
        "Cost": ["Free", "~$0.001/call", "~$0.003/call"],
        "Speed": ["Varies by GPU", "~1.5s", "~1.5s"],
        "Use Case": ["Development / demo", "Production (cheap)", "Quality tasks (P1 triage, QBR)"],
    }
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)



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
    st.Page("pages/4_QBR_Prep.py", title="QBR Prep"),
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
