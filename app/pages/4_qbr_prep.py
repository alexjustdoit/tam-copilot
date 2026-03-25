import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from data.models import Customer, Subscription, SupportTicket, UsageMetrics

st.set_page_config(page_title="QBR Prep — TAM Copilot", layout="wide")
st.title("QBR Preparation")
st.caption("Auto-generate executive-ready Quarterly Business Review talking points from customer data.")


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

# Customer selection (prioritize Enterprise for demos)
sorted_customers = sorted(customers, key=lambda c: ({"Enterprise": 0, "Mid-Market": 1, "SMB": 2}[c.tier], -c.arr))
customer_names = {c.id: f"{c.company_name} ({c.tier}) — ${c.arr:,.0f} ARR" for c in sorted_customers}
selected_id = st.selectbox("Select Customer", options=[c.id for c in sorted_customers], format_func=lambda x: customer_names[x])

selected = next(c for c in customers if c.id == selected_id)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Company", selected.company_name)
with col2:
    st.metric("ARR", f"${selected.arr:,.0f}")
with col3:
    from datetime import date
    days = (selected.renewal_date - date.today()).days
    st.metric("Days to Renewal", days)
with col4:
    st.metric("TAM", selected.tam_owner)

st.divider()

if st.button("Generate QBR", type="primary", use_container_width=True):
    with st.spinner("Generating QBR talking points..."):
        try:
            from features.qbr_prep import generate_qbr

            qbr, resp = generate_qbr(
                customer=selected,
                usage_records=usage_map.get(selected_id, []),
                tickets=ticket_map.get(selected_id, []),
                subscription=sub_map.get(selected_id),
            )

            st.success(f"QBR generated in {resp.latency_ms:.0f}ms via {resp.provider.upper()}")

            # Executive Summary
            st.subheader("Executive Summary")
            st.info(qbr.executive_summary)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Business Wins")
                for win in qbr.business_wins:
                    st.markdown(f"- {win}")

                st.subheader("Usage Highlights")
                for highlight in qbr.usage_highlights:
                    st.markdown(f"- {highlight}")

                st.subheader("Renewal Talking Points")
                for point in qbr.renewal_talking_points:
                    st.markdown(f"- {point}")

            with col2:
                st.subheader("Open Risks (Address Honestly)")
                for risk in qbr.open_risks:
                    st.markdown(f"- {risk}")

                st.subheader("Strategic Asks")
                for ask in qbr.strategic_asks:
                    st.markdown(f"- {ask}")

                st.subheader("Follow-Up Actions")
                for action in qbr.follow_up_actions:
                    st.markdown(f"- {action}")

            st.divider()
            st.subheader("Suggested Agenda")
            for item in qbr.suggested_agenda:
                st.markdown(f"- {item}")

            st.divider()

            # Export
            qbr_text = f"""QBR Preparation: {selected.company_name}
Generated: {date.today()}
TAM: {selected.tam_owner}

EXECUTIVE SUMMARY
{qbr.executive_summary}

BUSINESS WINS
{chr(10).join(f'- {w}' for w in qbr.business_wins)}

USAGE HIGHLIGHTS
{chr(10).join(f'- {h}' for h in qbr.usage_highlights)}

OPEN RISKS
{chr(10).join(f'- {r}' for r in qbr.open_risks)}

STRATEGIC ASKS
{chr(10).join(f'- {a}' for a in qbr.strategic_asks)}

RENEWAL TALKING POINTS
{chr(10).join(f'- {p}' for p in qbr.renewal_talking_points)}

SUGGESTED AGENDA
{chr(10).join(f'- {i}' for i in qbr.suggested_agenda)}

FOLLOW-UP ACTIONS
{chr(10).join(f'- {a}' for a in qbr.follow_up_actions)}
"""
            st.download_button(
                label="Download QBR Notes",
                data=qbr_text,
                file_name=f"qbr_{selected.company_name.replace(' ', '_')}_{date.today()}.txt",
                mime="text/plain",
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Provider", resp.provider.upper())
            with col2:
                st.metric("Latency", f"{resp.latency_ms:.0f}ms")
            with col3:
                cost_str = f"${resp.estimated_cost_usd:.4f}" if resp.estimated_cost_usd > 0 else "Free (local)"
                st.metric("Cost", cost_str)

        except ConnectionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"QBR generation failed: {e}")
            raise
