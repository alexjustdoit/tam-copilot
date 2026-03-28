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

st.title("Customers")


@st.cache_data
def load_data():
    fixtures = Path(__file__).parent.parent.parent / "data" / "fixtures"
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((fixtures / "tickets.json").read_text())]
    subscriptions = [Subscription(**s) for s in json.loads((fixtures / "subscriptions.json").read_text())]
    usage = [UsageMetrics(**u) for u in json.loads((fixtures / "usage.json").read_text())]
    return customers, tickets, subscriptions, usage


customers, tickets, subscriptions, usage = load_data()
sub_map = {s.customer_id: s for s in subscriptions}
usage_map: dict[str, list] = {}
for u in usage:
    usage_map.setdefault(u.customer_id, []).append(u)
ticket_map: dict[str, list] = {}
for t in tickets:
    ticket_map.setdefault(t.customer_id, []).append(t)

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
        "Segment": c.tier,
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

# Persistent filters — keys shared across pages so selections survive navigation
_all_segments = ["Enterprise", "Mid-Market", "SMB"]
_all_tams = sorted(df["TAM Owner"].unique())
if "filter_segments" not in st.session_state:
    st.session_state["filter_segments"] = _all_segments
if "filter_tams" not in st.session_state:
    st.session_state["filter_tams"] = _all_tams
else:
    st.session_state["filter_tams"] = [t for t in st.session_state["filter_tams"] if t in _all_tams]

col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    sel_segments = st.multiselect("Segment", _all_segments, default=st.session_state["filter_segments"])
    st.session_state["filter_segments"] = sel_segments
with col2:
    sel_tams = st.multiselect("TAM Owner", _all_tams, default=st.session_state["filter_tams"])
    st.session_state["filter_tams"] = sel_tams
with col3:
    risk_only = st.checkbox("Show At-Risk Only (flags present)")

filtered = df[df["Segment"].isin(sel_segments) & df["TAM Owner"].isin(sel_tams)]
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

display_cols = ["Company", "Segment", "Industry", "ARR", "TAM Owner", "Renewal Date", "Days to Renewal", "Open Tickets", "P1/P2 Open", "Seat Util %", "Risk Flags"]
st.dataframe(
    filtered[display_cols].style.format({"ARR": "${:,.0f}", "Seat Util %": "{:.0f}%"}),
    use_container_width=True,
    height=500,
)

st.caption("🔴 P1/P2 = critical open tickets  |  🟠 RENEWAL = renewing within 60 days  |  🟡 LOW-UTIL = seat utilization below 50%")

st.divider()

# ---------- Customer Detail ----------
st.subheader("Customer Detail")
all_sorted = sorted(customers, key=lambda c: c.company_name)
selected_id = st.selectbox(
    "Select account to drill into",
    options=[c.id for c in all_sorted],
    format_func=lambda x: next(c.company_name for c in all_sorted if c.id == x),
)
c = next(c for c in customers if c.id == selected_id)
sub = sub_map.get(c.id)
cust_tickets = ticket_map.get(c.id, [])
cust_usage = sorted(usage_map.get(c.id, []), key=lambda r: r.month)

days_to_renewal = (c.renewal_date - date.today()).days
seat_util = (sub.seats_used / sub.seats_purchased) if sub and sub.seats_purchased > 0 else None

# Header metrics
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("ARR", f"${c.arr:,.0f}")
with col2:
    st.metric("Employees", f"{c.employees:,}")
with col3:
    st.metric("Days to Renewal", days_to_renewal)
with col4:
    st.metric("Seat Utilization", f"{seat_util:.0%}" if seat_util is not None else "—")
with col5:
    st.metric("Plan", sub.plan if sub else "—")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Industry", c.industry)
with col2:
    st.metric("TAM Owner", c.tam_owner)
with col3:
    st.metric("MRR", f"${sub.mrr:,.0f}" if sub else "—")
with col4:
    st.metric("Auto-Renew", "Yes" if sub and sub.auto_renew else "No")

st.divider()

# Usage trend chart
col_left, col_right = st.columns([2, 1])
with col_left:
    st.markdown("**Usage Trend (DAU)**")
    if cust_usage:
        usage_df = pd.DataFrame([
            {"Month": r.month.strftime("%b %Y"), "DAU": r.dau, "MAU": r.mau, "API Calls": r.api_calls}
            for r in cust_usage
        ])
        fig = px.line(
            usage_df, x="Month", y=["DAU", "MAU"],
            markers=True, height=260,
        )
        fig.update_layout(margin=dict(t=10, b=10, l=0, r=0), legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No usage data available.")

with col_right:
    st.markdown("**Features Adopted**")
    if cust_usage:
        adopted = sorted(cust_usage[-1].features_adopted)
        from features.expansion import ALL_FEATURES
        unadopted = sorted(f for f in ALL_FEATURES if f not in adopted)
        st.markdown("✅ " + "  \n✅ ".join(adopted) if adopted else "_None_")
        if unadopted:
            with st.expander(f"Not yet adopted ({len(unadopted)})"):
                st.markdown("  \n".join(f"• {f}" for f in unadopted))
    else:
        st.caption("No feature data available.")

st.divider()

# Open tickets
open_tickets = [t for t in cust_tickets if t.status in ("open", "in_progress")]
st.markdown(f"**Open Tickets ({len(open_tickets)})**")
if open_tickets:
    ticket_rows = [
        {
            "Priority": t.priority,
            "Title": t.title,
            "Category": t.category,
            "Status": t.status,
            "Tags": ", ".join(t.tags) if t.tags else "",
            "Created": t.created_at.strftime("%Y-%m-%d"),
        }
        for t in sorted(open_tickets, key=lambda t: t.priority)
    ]
    st.dataframe(pd.DataFrame(ticket_rows), use_container_width=True, hide_index=True)
else:
    st.success("No open tickets.")

st.divider()

# AI Health Score
st.markdown("**AI Health Score**")
if st.button("Run Health Assessment", type="primary"):
    with st.spinner("Scoring customer health..."):
        try:
            from features.health_score import compute_health_score

            result, resp = compute_health_score(
                customer=c,
                usage_records=cust_usage,
                tickets=cust_tickets,
                subscription=sub,
            )

            tier_icons = {"Healthy": "✅", "Neutral": "🟡", "At Risk": "🟠", "Critical": "🔴"}
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Score", f"{result.total_score}/100")
            with col2:
                st.metric("Health Tier", f"{tier_icons.get(result.health_tier, '')} {result.health_tier}")
            with col3:
                st.metric("Usage", f"{result.usage_score}/25")
            with col4:
                st.metric("Engagement", f"{result.engagement_score}/25")
            with col5:
                st.metric("Support", f"{result.support_score}/25")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Strengths**")
                for s in result.top_strengths:
                    st.markdown(f"- {s}")
            with col2:
                st.markdown("**Risks**")
                for r in result.top_risks:
                    st.markdown(f"- {r}")

            st.markdown("**Recommended Actions**")
            for i, action in enumerate(result.recommended_actions, 1):
                st.markdown(f"**{i}.** {action}")

            with st.expander("Narrative"):
                st.write(result.narrative)

            st.caption(f"Provider: {resp.provider.upper()} | Latency: {resp.latency_ms:.0f}ms")

        except ConnectionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Health assessment failed: {e}")
            raise
