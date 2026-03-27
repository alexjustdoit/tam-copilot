import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
import config  # noqa: F401
from app.components.sidebar import render_sidebar

from data.models import Customer, SupportTicket
from data.taxonomy import load_taxonomy

st.set_page_config(page_title="Management Insights — TAM Copilot", layout="wide")
render_sidebar()
st.title("Management Insights")
st.caption("Department-level view across all TAMs and segments. Use this page to identify portfolio-wide patterns, coverage gaps, and team performance.")

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

col1, col2 = st.columns(2)
with col1:
    tam_filter = st.multiselect("TAM", all_tams, default=all_tams, placeholder="All TAMs")
with col2:
    status_filter = st.radio("Ticket Status", ["Open Only", "All Tickets"], horizontal=True)

scoped_tam_ids = tam_filter if tam_filter else all_tams
scoped_customers = {c.id: c for c in customers if c.tam_owner in scoped_tam_ids}

if status_filter == "Open Only":
    scoped_tickets = [t for t in tickets if t.customer_id in scoped_customers and t.status in ("open", "in_progress")]
else:
    scoped_tickets = [t for t in tickets if t.customer_id in scoped_customers]

triaged_tickets = [t for t in scoped_tickets if t.tags]

# ── Top-line metrics ──────────────────────────────────────────────────────────

st.divider()
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("TAMs in Scope", len(set(c.tam_owner for c in scoped_customers.values())))
with col2:
    st.metric("Accounts", len(scoped_customers))
with col3:
    st.metric("Total Tickets", len(scoped_tickets))
with col4:
    st.metric("Triaged (Tagged)", len(triaged_tickets))
with col5:
    coverage = round(len(triaged_tickets) / len(scoped_tickets) * 100) if scoped_tickets else 0
    st.metric("Triage Coverage", f"{coverage}%")

st.divider()

# ── Triage coverage by TAM ────────────────────────────────────────────────────

st.subheader("Triage Coverage by TAM")
st.caption("How actively each TAM is using the triage workflow.")

coverage_rows = []
for tam in scoped_tam_ids:
    tam_customer_ids = {c.id for c in customers if c.tam_owner == tam}
    tam_tickets = [t for t in scoped_tickets if t.customer_id in tam_customer_ids]
    tam_triaged = [t for t in tam_tickets if t.tags]
    tam_coverage = round(len(tam_triaged) / len(tam_tickets) * 100) if tam_tickets else 0
    coverage_rows.append({
        "TAM": tam,
        "Accounts": len(tam_customer_ids & scoped_customers.keys()),
        "Tickets": len(tam_tickets),
        "Triaged": len(tam_triaged),
        "Coverage %": tam_coverage,
    })

coverage_df = pd.DataFrame(coverage_rows).sort_values("Coverage %", ascending=False)
st.dataframe(
    coverage_df.style.background_gradient(subset=["Coverage %"], cmap="RdYlGn"),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Segment comparison: ticket volume and priority ────────────────────────────

st.subheader("Ticket Volume by Segment")
st.caption("All tickets in scope.")

seg_rows = []
for tier in ["Enterprise", "Mid-Market", "SMB"]:
    tier_ids = {c.id for c in scoped_customers.values() if c.tier == tier}
    tier_tickets = [t for t in scoped_tickets if t.customer_id in tier_ids]
    for priority in ["P1", "P2", "P3", "P4"]:
        seg_rows.append({
            "Segment": tier,
            "Priority": priority,
            "Count": sum(1 for t in tier_tickets if t.priority == priority),
        })

seg_df = pd.DataFrame(seg_rows)
priority_colors = {"P1": "#d62728", "P2": "#ff7f0e", "P3": "#1f77b4", "P4": "#7f7f7f"}
fig_seg = px.bar(
    seg_df,
    x="Segment",
    y="Count",
    color="Priority",
    color_discrete_map=priority_colors,
    barmode="stack",
    text_auto=True,
)
fig_seg.update_layout(height=350, margin=dict(t=20))
st.plotly_chart(fig_seg, use_container_width=True)

st.divider()

# ── Tag heatmap: segment × tag ────────────────────────────────────────────────

st.subheader("Tag Frequency by Segment")
st.caption("Triaged tickets only. Reveals what each segment is most commonly experiencing.")

if not triaged_tickets:
    st.warning("No triaged tickets yet. Use the Ticket Triage page to triage and tag tickets.")
else:
    heatmap_rows = []
    for t in triaged_tickets:
        c = scoped_customers.get(t.customer_id)
        if not c:
            continue
        for tag in t.tags:
            heatmap_rows.append({"Segment": c.tier, "Tag": tag})

    if heatmap_rows:
        heatmap_df = pd.DataFrame(heatmap_rows)
        pivot = heatmap_df.groupby(["Tag", "Segment"]).size().unstack(fill_value=0)
        for seg in ["Enterprise", "Mid-Market", "SMB"]:
            if seg not in pivot.columns:
                pivot[seg] = 0
        pivot = pivot[["Enterprise", "Mid-Market", "SMB"]].sort_values("Enterprise", ascending=False)

        st.dataframe(
            pivot.style.background_gradient(cmap="Blues", axis=None),
            use_container_width=True,
        )
    else:
        st.info("Triaged tickets exist but none have tags applied yet.")

st.divider()

# ── Tag frequency across all TAMs ─────────────────────────────────────────────

st.subheader("Top Tags — Portfolio Wide")
st.caption("Triaged tickets only.")

if triaged_tickets:
    all_tags = [tag for t in triaged_tickets for tag in t.tags]
    if all_tags:
        tag_df = pd.Series(all_tags).value_counts().reset_index()
        tag_df.columns = ["Tag", "Count"]
        fig_tags = px.bar(tag_df, x="Count", y="Tag", orientation="h", text="Count")
        fig_tags.update_layout(height=400, margin=dict(t=20), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_tags, use_container_width=True)

st.divider()

# ── AI narrative ──────────────────────────────────────────────────────────────

st.subheader("AI Executive Summary")
st.caption("Department-level narrative summary of the data above. On-demand.")

if st.button("Generate Executive Summary", type="primary"):
    if not triaged_tickets:
        st.warning("No triaged tickets to summarize.")
    else:
        with st.spinner("Generating summary..."):
            try:
                from features.tag_insights import summarize_tag_trends
                tag_count_dict = pd.Series([tag for t in triaged_tickets for tag in t.tags]).value_counts().to_dict()
                summary, resp = summarize_tag_trends(
                    segment=f"all segments (TAMs: {', '.join(scoped_tam_ids)})",
                    tag_counts=tag_count_dict,
                    total_tickets=len(scoped_tickets),
                    triaged_tickets=len(triaged_tickets),
                )
                st.write(summary)
                cost_str = f"${resp.estimated_cost_usd:.4f}" if resp.estimated_cost_usd > 0 else "Free (local)"
                st.caption(f"Provider: {resp.provider.upper()} · Latency: {resp.latency_ms:.0f}ms · Cost: {cost_str}")
            except Exception as e:
                st.error(f"Failed to generate summary: {e}")
                raise
