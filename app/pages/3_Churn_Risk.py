import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
import config  # noqa: F401

from data.models import Customer, Subscription, SupportTicket, UsageMetrics

st.title("Churn Risk")
st.caption("AI-powered at-risk account detection with specific risk factors and recommended actions.")


@st.cache_data
def load_data():
    fixtures = Path(__file__).parent.parent.parent / "data" / "fixtures"
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((fixtures / "tickets.json").read_text())]
    usage = [UsageMetrics(**u) for u in json.loads((fixtures / "usage.json").read_text())]
    subscriptions = [Subscription(**s) for s in json.loads((fixtures / "subscriptions.json").read_text())]
    return customers, tickets, usage, subscriptions


customers, tickets, usage, subscriptions = load_data()
sub_map = {s.customer_id: s for s in subscriptions}
usage_map: dict[str, list] = {}
for u in usage:
    usage_map.setdefault(u.customer_id, []).append(u)
ticket_map: dict[str, list] = {}
for t in tickets:
    ticket_map.setdefault(t.customer_id, []).append(t)

# Pre-filter: show likely at-risk customers to focus the analysis
def compute_risk_score(c: Customer) -> int:
    """Quick heuristic score for pre-filtering without LLM."""
    score = 0
    sub = sub_map.get(c.id)
    days_to_renewal = (c.renewal_date - date.today()).days

    if days_to_renewal < 90:
        score += 3
    if days_to_renewal < 30:
        score += 3

    if sub:
        util = sub.seats_used / sub.seats_purchased if sub.seats_purchased > 0 else 0
        if util < 0.5:
            score += 2
        if not sub.auto_renew:
            score += 2

    p1_p2 = sum(1 for t in ticket_map.get(c.id, []) if t.priority in ("P1", "P2") and t.status in ("open", "in_progress"))
    if p1_p2 > 0:
        score += 2

    frustrated = sum(1 for t in ticket_map.get(c.id, [])
                     if any(w in t.description.lower() for w in ["alternative", "cancel", "unacceptable", "losing money"]))
    score += frustrated

    return score


ranked = sorted(customers, key=lambda c: compute_risk_score(c), reverse=True)

st.subheader("At-Risk Account Overview")

_all_segments = ["Enterprise", "Mid-Market", "SMB"]
all_tams = sorted(set(c.tam_owner for c in customers))
if "filter_segments" not in st.session_state:
    st.session_state["filter_segments"] = _all_segments
if "filter_tams" not in st.session_state:
    st.session_state["filter_tams"] = all_tams
else:
    st.session_state["filter_tams"] = [t for t in st.session_state["filter_tams"] if t in all_tams]

col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    sel_segments = st.multiselect("Segment", _all_segments, default=st.session_state["filter_segments"])
    st.session_state["filter_segments"] = sel_segments
with col2:
    sel_tams = st.multiselect("TAM Owner", all_tams, default=st.session_state["filter_tams"])
    st.session_state["filter_tams"] = sel_tams
with col3:
    top_n = st.slider("Show Top N Accounts", 5, 50, 15)

filtered = [c for c in ranked if c.tier in sel_segments and c.tam_owner in (sel_tams if sel_tams else all_tams)][:top_n]

# Quick summary table
rows = []
for c in filtered:
    sub = sub_map.get(c.id)
    days = (c.renewal_date - date.today()).days
    seat_util = (sub.seats_used / sub.seats_purchased) if sub and sub.seats_purchased > 0 else None
    risk_score = compute_risk_score(c)

    rows.append({
        "Company": c.company_name,
        "Segment": c.tier,
        "ARR": c.arr,
        "Days to Renewal": days,
        "Seat Util %": round(seat_util * 100) if seat_util else 0,
        "Auto Renew": sub.auto_renew if sub else True,
        "Open P1/P2": sum(1 for t in ticket_map.get(c.id, []) if t.priority in ("P1", "P2") and t.status in ("open", "in_progress")),
        "Risk Score": risk_score,
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, height=400)

st.divider()

# Deep-dive on single account
st.subheader("Deep AI Churn Risk Assessment")
account_names = {c.id: f"{c.company_name} ({c.tier})" for c in filtered}
selected_id = st.selectbox("Select Account for Deep Assessment", options=[c.id for c in filtered], format_func=lambda x: account_names[x])

selected_customer = next(c for c in customers if c.id == selected_id)

if "churn_assessments" not in st.session_state:
    st.session_state["churn_assessments"] = {}

cached = st.session_state["churn_assessments"].get(selected_id)

col_btn, col_hint = st.columns([2, 5])
with col_btn:
    run_label = "Re-run Assessment" if cached else "Run Churn Risk Assessment"
    run = st.button(run_label, type="primary", use_container_width=True)
with col_hint:
    if cached:
        st.caption(f"Showing cached result. Click Re-run to refresh.")

if run:
    with st.spinner("Analyzing churn risk..."):
        try:
            from features.churn_risk import assess_churn_risk

            result, resp = assess_churn_risk(
                customer=selected_customer,
                usage_records=usage_map.get(selected_id, []),
                tickets=ticket_map.get(selected_id, []),
                subscription=sub_map.get(selected_id),
            )
            st.session_state["churn_assessments"][selected_id] = result
            cached = result

        except ConnectionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Assessment failed: {e}")
            raise

if cached:
    result = cached
    tier_icons = {"Low": "✅", "Medium": "⚠️", "High": "🔴", "Critical": "🚨"}

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Risk Tier", f"{tier_icons[result.risk_tier]} {result.risk_tier}")
    with col2:
        st.metric("Churn Probability", f"{result.churn_probability_pct}%")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Risk Factors")
        for factor in result.top_risk_factors:
            st.markdown(f"- {factor}")

        st.subheader("Positive Signals")
        for signal in result.positive_signals:
            st.markdown(f"- {signal}")

    with col2:
        st.subheader("Recommended Actions")
        for i, action in enumerate(result.recommended_actions, 1):
            st.markdown(f"**{i}.** {action}")

    st.divider()
    st.subheader("Suggested Outreach Message")
    st.text_area("Draft Message", result.suggested_outreach_message, height=150)

    with st.expander("Reasoning"):
        st.write(result.reasoning)
