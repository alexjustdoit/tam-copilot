import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
import config  # noqa: F401

from data.models import Customer, SupportTicket
from data.taxonomy import load_taxonomy

st.title("Ticket Insights")
st.caption("Tag trends, volume patterns, and search across your portfolio.")

FIXTURES_PATH = Path(__file__).parent.parent.parent / "data" / "fixtures"


@st.cache_data
def load_data():
    customers = [Customer(**c) for c in json.loads((FIXTURES_PATH / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((FIXTURES_PATH / "tickets.json").read_text())]
    return customers, tickets


customers, tickets = load_data()
taxonomy = load_taxonomy()

customer_map = {c.id: c for c in customers}
all_tams = sorted(set(c.tam_owner for c in customers))

# ── Filters ───────────────────────────────────────────────────────────────────

_all_segments = ["Enterprise", "Mid-Market", "SMB"]
if "filter_segments" not in st.session_state:
    st.session_state["filter_segments"] = _all_segments
if "filter_tams" not in st.session_state:
    st.session_state["filter_tams"] = all_tams
else:
    st.session_state["filter_tams"] = [t for t in st.session_state["filter_tams"] if t in all_tams]

col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
with col1:
    sel_segments = st.multiselect("Segment", _all_segments, default=st.session_state["filter_segments"])
    st.session_state["filter_segments"] = sel_segments
with col2:
    sel_tams = st.multiselect("TAM Owner", all_tams, default=st.session_state["filter_tams"])
    st.session_state["filter_tams"] = sel_tams
with col3:
    status_filter = st.radio(
        "Ticket Status",
        ["Open Only", "All Tickets"],
        horizontal=True,
    )
with col4:
    tag_filter = st.multiselect(
        "Filter by Tag",
        options=taxonomy["tags"],
        placeholder="All tags",
    )

# Apply filters
scoped_customers = {c.id for c in customers if c.tier in sel_segments and c.tam_owner in (sel_tams if sel_tams else all_tams)}

if status_filter == "Open Only":
    scoped_tickets = [t for t in tickets if t.customer_id in scoped_customers and t.status in ("open", "in_progress")]
else:
    scoped_tickets = [t for t in tickets if t.customer_id in scoped_customers]

triaged_tickets = [t for t in scoped_tickets if t.tags]

if tag_filter:
    triaged_tickets = [t for t in triaged_tickets if any(tag in t.tags for tag in tag_filter)]

# ── Coverage metrics ──────────────────────────────────────────────────────────

st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Tickets", len(scoped_tickets))
with col2:
    st.metric("Triaged (Tagged)", len(triaged_tickets))
with col3:
    coverage = round(len(triaged_tickets) / len(scoped_tickets) * 100) if scoped_tickets else 0
    st.metric("Triage Coverage", f"{coverage}%")
with col4:
    p1p2_open = sum(1 for t in scoped_tickets if t.priority in ("P1", "P2") and t.status in ("open", "in_progress"))
    st.metric("Open P1/P2", p1p2_open)

if coverage < 20:
    st.info("Tag-based charts below reflect triaged tickets only. Triage more tickets on the Ticket Triage page to build richer insights.")

st.divider()

# ── Volume by priority (all tickets) ─────────────────────────────────────────

st.subheader("Ticket Volume by Priority")
st.caption("All tickets in scope — no triage required.")

priority_counts = pd.Series([t.priority for t in scoped_tickets]).value_counts().reindex(["P1", "P2", "P3", "P4"], fill_value=0).reset_index()
priority_counts.columns = ["Priority", "Count"]
priority_colors = {"P1": "#d62728", "P2": "#ff7f0e", "P3": "#1f77b4", "P4": "#7f7f7f"}

fig_priority = px.bar(
    priority_counts,
    x="Priority",
    y="Count",
    color="Priority",
    color_discrete_map=priority_colors,
    text="Count",
)
fig_priority.update_layout(showlegend=False, height=300, margin=dict(t=20))
st.plotly_chart(fig_priority, use_container_width=True)

# Volume by category
st.subheader("Ticket Volume by Category")
cat_counts = pd.Series([t.category for t in scoped_tickets]).value_counts().reset_index()
cat_counts.columns = ["Category", "Count"]
fig_cat = px.bar(cat_counts, x="Count", y="Category", orientation="h", text="Count")
fig_cat.update_layout(height=350, margin=dict(t=20), yaxis=dict(autorange="reversed"))
st.plotly_chart(fig_cat, use_container_width=True)

st.divider()

# ── Tag frequency (triaged tickets only) ─────────────────────────────────────

st.subheader("Tag Frequency")
st.caption("Triaged tickets only.")

if not triaged_tickets:
    st.warning("No triaged tickets in the current scope. Use the Ticket Triage page to triage and tag tickets.")
else:
    all_tags_flat = [tag for t in triaged_tickets for tag in t.tags]
    if all_tags_flat:
        tag_counts = pd.Series(all_tags_flat).value_counts().reset_index()
        tag_counts.columns = ["Tag", "Count"]
        fig_tags = px.bar(tag_counts, x="Count", y="Tag", orientation="h", text="Count")
        fig_tags.update_layout(height=400, margin=dict(t=20), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_tags, use_container_width=True)
    else:
        st.info("Triaged tickets exist but none have tags applied yet.")

# ── Trend over time (triaged tickets by month) ────────────────────────────────

st.subheader("Ticket Volume Over Time")
st.caption("All tickets by month created.")

if scoped_tickets:
    trend_df = pd.DataFrame([{
        "month": t.created_at.strftime("%Y-%m"),
        "priority": t.priority,
    } for t in scoped_tickets])
    monthly = trend_df.groupby(["month", "priority"]).size().reset_index(name="count")
    fig_trend = px.line(
        monthly,
        x="month",
        y="count",
        color="priority",
        color_discrete_map=priority_colors,
        markers=True,
    )
    fig_trend.update_layout(height=350, margin=dict(t=20), xaxis_title="Month", yaxis_title="Tickets")
    st.plotly_chart(fig_trend, use_container_width=True)

# Tag trend over time (triaged only)
if triaged_tickets and all_tags_flat:
    st.subheader("Tag Trend Over Time")
    st.caption("Triaged tickets only — shows how tag frequency changes month over month.")

    tag_trend_rows = [
        {"month": t.created_at.strftime("%Y-%m"), "tag": tag}
        for t in triaged_tickets
        for tag in t.tags
    ]
    if tag_trend_rows:
        tag_trend_df = pd.DataFrame(tag_trend_rows)
        tag_monthly = tag_trend_df.groupby(["month", "tag"]).size().reset_index(name="count")
        fig_tag_trend = px.line(tag_monthly, x="month", y="count", color="tag", markers=True)
        fig_tag_trend.update_layout(height=400, margin=dict(t=20), xaxis_title="Month", yaxis_title="Tagged Tickets")
        st.plotly_chart(fig_tag_trend, use_container_width=True)

st.divider()

# ── AI Narrative ──────────────────────────────────────────────────────────────

st.subheader("AI Insights Summary")
st.caption("On-demand narrative summary of the tag data above.")

if st.button("Generate Insights Summary", type="primary"):
    if not triaged_tickets:
        st.warning("No triaged tickets to summarize. Triage some tickets first.")
    else:
        with st.spinner("Generating summary..."):
            try:
                from features.tag_insights import summarize_tag_trends
                tag_count_dict = pd.Series([tag for t in triaged_tickets for tag in t.tags]).value_counts().to_dict()
                segment_label = ", ".join(sel_segments) if len(sel_segments) < 3 else "All Segments"
                summary, resp = summarize_tag_trends(
                    segment=segment_label,
                    tag_counts=tag_count_dict,
                    total_tickets=len(scoped_tickets),
                    triaged_tickets=len(triaged_tickets),
                )
                st.write(summary)
                st.caption(f"Provider: {resp.provider.upper()} · Latency: {resp.latency_ms:.0f}ms · Cost: ${resp.estimated_cost_usd:.4f}" if resp.estimated_cost_usd > 0 else f"Provider: {resp.provider.upper()} · Latency: {resp.latency_ms:.0f}ms · Cost: Free (local)")
            except Exception as e:
                st.error(f"Failed to generate summary: {e}")
                raise

st.divider()

# ── Search ────────────────────────────────────────────────────────────────────

st.subheader("Search Tickets")

query = st.text_input("Search by title, description, or tag", placeholder="e.g. API timeout, SLA Risk...")

if query:
    query_lower = query.lower().strip()
    results = [
        t for t in scoped_tickets
        if query_lower in t.title.lower()
        or query_lower in t.description.lower()
        or any(query_lower in tag.lower() for tag in t.tags)
    ]

    st.caption(f"{len(results)} result(s) found")

    if results:
        rows = []
        for t in results:
            c = customer_map.get(t.customer_id)
            rows.append({
                "Company": c.company_name if c else "—",
                "Tier": c.tier if c else "—",
                "Priority": t.priority,
                "Category": t.category,
                "Tags": ", ".join(t.tags) if t.tags else "—",
                "Status": t.status,
                "Title": t.title[:80],
                "Created": t.created_at.strftime("%Y-%m-%d"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No tickets matched your search.")
