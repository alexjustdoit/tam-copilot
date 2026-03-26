"""
TAM Copilot — Main Dashboard
Run with: streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os

import streamlit as st

import config  # noqa: F401 — loads .env via load_dotenv()
from data.models import Customer, Subscription, SupportTicket, UsageMetrics

st.set_page_config(
    page_title="TAM Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Data loading (cached) ----------

@st.cache_data
def load_all_data():
    fixtures = Path(__file__).parent.parent / "data" / "fixtures"
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((fixtures / "tickets.json").read_text())]
    usage = [UsageMetrics(**u) for u in json.loads((fixtures / "usage.json").read_text())]
    subscriptions = [Subscription(**s) for s in json.loads((fixtures / "subscriptions.json").read_text())]
    return customers, tickets, usage, subscriptions


# ---------- Sidebar ----------

with st.sidebar:
    st.title("TAM Copilot")
    st.caption("AI-Powered Technical Account Management")

    st.divider()
    st.subheader("LLM Provider")
    use_local = st.toggle(
        "Use Local LLM (Ollama)",
        value=os.getenv("USE_LOCAL_LLM", "true").lower() == "true",
        help="Toggle between free local Ollama and API providers",
    )
    os.environ["USE_LOCAL_LLM"] = "true" if use_local else "false"

    if use_local:
        st.info("Local mode: Free, requires Ollama running")
    else:
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
        if has_openai:
            st.success("OpenAI API key configured")
        else:
            st.warning("Set OPENAI_API_KEY in .env")
        if has_anthropic:
            st.success("Anthropic API key configured")

    st.divider()
    st.caption("Stack: Python · Streamlit · Ollama · OpenAI · Anthropic")


# ---------- Home Page ----------

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

**Provider Comparison Eval**
Side-by-side accuracy, latency, and cost benchmarks across Ollama, GPT-4o-mini, and Claude Haiku.
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
import pandas as pd
st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

st.caption("Navigate using the sidebar pages →")
