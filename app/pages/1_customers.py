import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st
import config  # noqa: F401

from app.components.sidebar import render_sidebar
from data.models import Customer, Subscription, SupportTicket

st.set_page_config(page_title="Customers — TAM Copilot", layout="wide")
render_sidebar()
st.title("Customer Portfolio")


@st.cache_data
def load_data():
    fixtures = Path(__file__).parent.parent.parent / "data" / "fixtures"
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((fixtures / "tickets.json").read_text())]
    subscriptions = [Subscription(**s) for s in json.loads((fixtures / "subscriptions.json").read_text())]
    return customers, tickets, subscriptions


customers, tickets, subscriptions = load_data()
sub_map = {s.customer_id: s for s in subscriptions}

# Build DataFrame
rows = []
for c in customers:
    sub = sub_map.get(c.id)
    open_t = sum(1 for t in tickets if t.customer_id == c.id and t.status in ("open", "in_progress"))
    p1_p2 = sum(1 for t in tickets if t.customer_id == c.id and t.priority in ("P1", "P2") and t.status in ("open", "in_progress"))
    days_to_renewal = (c.renewal_date - date.today()).days
    seat_util = (sub.seats_used / sub.seats_purchased) if sub and sub.seats_purchased > 0 else None

    risk_flag = ""
    if p1_p2 > 0:
        risk_flag += "🔴 P1/P2  "
    if days_to_renewal < 60:
        risk_flag += "🟠 RENEWAL  "
    if seat_util is not None and seat_util < 0.5:
        risk_flag += "🟡 LOW-UTIL"

    rows.append({
        "ID": c.id,
        "Company": c.company_name,
        "Industry": c.industry,
        "Tier": c.tier,
        "ARR": c.arr,
        "Employees": c.employees,
        "TAM Owner": c.tam_owner,
        "Renewal Date": c.renewal_date.isoformat(),
        "Days to Renewal": days_to_renewal,
        "Open Tickets": open_t,
        "P1/P2 Open": p1_p2,
        "Seat Util %": round(seat_util * 100, 0) if seat_util else None,
        "Risk Flags": risk_flag.strip(),
    })

df = pd.DataFrame(rows)

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    tier_filter = st.multiselect("Tier", ["Enterprise", "Mid-Market", "SMB"], default=["Enterprise", "Mid-Market", "SMB"])
with col2:
    tam_filter = st.multiselect("TAM Owner", sorted(df["TAM Owner"].unique()), default=list(df["TAM Owner"].unique()))
with col3:
    risk_only = st.checkbox("Show At-Risk Only (flags present)")

filtered = df[df["Tier"].isin(tier_filter) & df["TAM Owner"].isin(tam_filter)]
if risk_only:
    filtered = filtered[filtered["Risk Flags"] != ""]

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Accounts Shown", len(filtered))
with col2:
    st.metric("Total ARR", f"${filtered['ARR'].sum():,.0f}")
with col3:
    at_risk = (filtered["Risk Flags"] != "").sum()
    st.metric("At-Risk Accounts", at_risk)
with col4:
    renewal_90 = (filtered["Days to Renewal"] < 90).sum()
    st.metric("Renewing in 90 Days", renewal_90)

st.divider()

display_cols = ["Company", "Tier", "Industry", "ARR", "TAM Owner", "Renewal Date", "Days to Renewal", "Open Tickets", "P1/P2 Open", "Seat Util %", "Risk Flags"]
st.dataframe(
    filtered[display_cols].style.format({"ARR": "${:,.0f}", "Seat Util %": "{:.0f}%"}),
    use_container_width=True,
    height=500,
)

st.caption("🔴 P1/P2 = critical open tickets  |  🟠 RENEWAL = renewing within 60 days  |  🟡 LOW-UTIL = seat utilization below 50%")
