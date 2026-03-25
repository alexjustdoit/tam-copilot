import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from data.models import Customer, SupportTicket

st.set_page_config(page_title="Ticket Triage — TAM Copilot", layout="wide")
st.title("AI Ticket Triage")
st.caption("Classify priority, detect sentiment, assess escalation risk, and draft responses — instantly.")


@st.cache_data
def load_data():
    fixtures = Path(__file__).parent.parent.parent / "data" / "fixtures"
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((fixtures / "tickets.json").read_text())]
    return customers, tickets


customers, tickets = load_data()
customer_map = {c.id: c for c in customers}

# Select customer
customer_names = {c.id: f"{c.company_name} ({c.tier})" for c in sorted(customers, key=lambda x: x.arr, reverse=True)}
selected_id = st.selectbox("Select Customer", options=list(customer_names.keys()), format_func=lambda x: customer_names[x])

customer = customer_map[selected_id]
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Company", customer.company_name)
with col2:
    st.metric("ARR", f"${customer.arr:,.0f}")
with col3:
    st.metric("Tier", customer.tier)

st.divider()

# Show customer tickets
customer_tickets = [t for t in tickets if t.customer_id == selected_id]
open_tickets = [t for t in customer_tickets if t.status in ("open", "in_progress")]

st.subheader(f"Open Tickets ({len(open_tickets)})")

if not open_tickets:
    st.info("No open tickets for this customer.")
    st.stop()

# Ticket selection
ticket_options = {t.id: f"[{t.priority}] {t.title[:70]}" for t in open_tickets}
selected_ticket_id = st.selectbox("Select Ticket to Triage", options=list(ticket_options.keys()), format_func=lambda x: ticket_options[x])

ticket = next(t for t in open_tickets if t.id == selected_ticket_id)

# Show ticket details
with st.expander("Ticket Details", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Priority:** {ticket.priority}")
    with col2:
        st.write(f"**Category:** {ticket.category}")
    with col3:
        st.write(f"**Status:** {ticket.status}")
    st.write(f"**Title:** {ticket.title}")
    st.write(f"**Description:**")
    st.write(ticket.description)
    st.caption(f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M')} | ID: {ticket.id}")

st.divider()

# Triage button
if st.button("Triage with AI", type="primary", use_container_width=True):
    with st.spinner("Analyzing ticket..."):
        try:
            from features.ticket_triage import triage_ticket
            result, resp = triage_ticket(ticket)

            # Display results
            st.subheader("Triage Result")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                priority_color = {"P1": "red", "P2": "orange", "P3": "blue", "P4": "gray"}[result.priority_recommendation]
                st.metric("Recommended Priority", result.priority_recommendation)
                if result.priority_recommendation != ticket.priority:
                    st.warning(f"Priority changed from {ticket.priority} → {result.priority_recommendation}")
            with col2:
                sentiment_emoji = {"positive": "😊", "neutral": "😐", "frustrated": "😤", "angry": "😡"}[result.sentiment]
                st.metric("Sentiment", f"{sentiment_emoji} {result.sentiment.title()}")
            with col3:
                risk_color = {"low": "green", "medium": "orange", "high": "red", "critical": "🚨"}
                st.metric("Escalation Risk", result.escalation_risk.upper())
            with col4:
                st.metric("Category", result.category)

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Reasoning")
                st.write(result.reasoning)

            with col2:
                st.subheader("Suggested Response")
                st.text_area("Draft Response (click to copy)", result.suggested_response, height=200, key="response_draft")

            st.divider()

            # Provider info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Provider", resp.provider.upper())
            with col2:
                st.metric("Latency", f"{resp.latency_ms:.0f}ms")
            with col3:
                cost_str = f"${resp.estimated_cost_usd:.4f}" if resp.estimated_cost_usd > 0 else "Free (local)"
                st.metric("Cost", cost_str)

        except ConnectionError as e:
            st.error(f"Cannot connect to Ollama: {e}")
        except Exception as e:
            st.error(f"Triage failed: {e}")
            raise

st.divider()

# Batch triage option
st.subheader("Batch Triage All Open Tickets")
st.caption("Triage all open tickets for this customer at once")

if st.button("Batch Triage All Open Tickets", use_container_width=True):
    progress = st.progress(0, text="Triaging tickets...")
    results_container = st.container()

    try:
        from features.ticket_triage import triage_tickets_batch
        results = []
        for i, t in enumerate(open_tickets):
            try:
                result, resp = __import__("features.ticket_triage", fromlist=["triage_ticket"]).triage_ticket(t)
                results.append((t, result, resp))
            except Exception as e:
                st.warning(f"Failed to triage {t.id}: {e}")
            progress.progress((i + 1) / len(open_tickets), text=f"Triaged {i+1}/{len(open_tickets)}")

        progress.empty()

        with results_container:
            import pandas as pd
            rows = []
            for t, r, resp in results:
                rows.append({
                    "Ticket": t.title[:50],
                    "Original Priority": t.priority,
                    "Recommended Priority": r.priority_recommendation,
                    "Sentiment": r.sentiment,
                    "Escalation Risk": r.escalation_risk,
                    "Category": r.category,
                    "Latency (ms)": round(resp.latency_ms),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            total_cost = sum(resp.estimated_cost_usd for _, _, resp in results)
            st.caption(f"Total cost: ${total_cost:.4f} | Provider: {results[0][2].provider if results else 'N/A'}")

    except ConnectionError as e:
        st.error(str(e))
