import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
st.markdown("<style>[data-testid='stSidebarNav'],[data-testid='stSidebarNavItems'],[data-testid='stSidebarNavLink']{display:none!important}</style>", unsafe_allow_html=True)
import config  # noqa: F401

from data.models import Customer, Subscription, SupportTicket, UsageMetrics
from data.session_store import get_fixtures_dir
from features.qbr_prep import QBRPrep

st.title("QBR Preparation")
st.caption("Auto-generate executive-ready Quarterly Business Review talking points from customer data.")


@st.cache_data
def load_data(fixtures_dir: str):
    fixtures = Path(fixtures_dir)
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((fixtures / "tickets.json").read_text())]
    usage = [UsageMetrics(**u) for u in json.loads((fixtures / "usage.json").read_text())]
    subscriptions = [Subscription(**s) for s in json.loads((fixtures / "subscriptions.json").read_text())]
    return customers, tickets, usage, subscriptions


customers, tickets, usage, subscriptions = load_data(str(get_fixtures_dir()))
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
    days = (selected.renewal_date - date.today()).days
    st.metric("Days to Renewal", days)
with col4:
    st.metric("TAM", selected.tam_owner)

st.divider()

_QBR_CACHE_FILE = Path(get_fixtures_dir()) / "qbr_cache.json"

if "qbr_cache" not in st.session_state:
    st.session_state["qbr_cache"] = {}

# Populate session cache from file-based cache on first access per customer
if selected_id not in st.session_state["qbr_cache"] and _QBR_CACHE_FILE.exists():
    try:
        file_cache = json.loads(_QBR_CACHE_FILE.read_text())
        if selected_id in file_cache:
            st.session_state["qbr_cache"][selected_id] = QBRPrep.model_validate(file_cache[selected_id])
    except Exception:
        pass

cached = st.session_state["qbr_cache"].get(selected_id)

col_btn, col_dl, col_hint = st.columns([2, 2, 3])
with col_btn:
    run = st.button("Re-run QBR" if cached else "Generate QBR", type="primary", use_container_width=True)
with col_dl:
    if cached:
        _dl_text = f"""# QBR Preparation: {selected.company_name}

**Generated:** {date.today()}
**TAM:** {selected.tam_owner}

---

## TAM Summary *(internal)*

{chr(10).join(f'- {b}' for b in cached.tam_summary)}

## Executive Summary *(talking points)*

{chr(10).join(f'- {p}' for p in cached.executive_summary)}

## Business Wins

{chr(10).join(f'- {w}' for w in cached.business_wins)}

## Usage Highlights

{chr(10).join(f'- {h}' for h in cached.usage_highlights)}

## Open Risks *(address honestly)*

{chr(10).join(f'- {r}' for r in cached.open_risks)}

## Strategic Asks

{chr(10).join(f'- {a}' for a in cached.strategic_asks)}

## Renewal Talking Points

{chr(10).join(f'- {p}' for p in cached.renewal_talking_points)}

## Suggested Agenda

{chr(10).join(f'- {i}' for i in cached.suggested_agenda)}

## Follow-Up Actions

{chr(10).join(f'- {a}' for a in cached.follow_up_actions)}
"""
        st.download_button(
            label="Download QBR Notes",
            data=_dl_text,
            file_name=f"qbr_{selected.company_name.replace(' ', '_')}_{date.today()}.md",
            mime="text/markdown",
            use_container_width=True,
        )
with col_hint:
    if cached:
        st.caption("Showing cached result. Click Re-run to refresh.")

if run:
    with st.spinner("Generating QBR talking points..."):
        try:
            from features.qbr_prep import generate_qbr

            qbr, resp = generate_qbr(
                customer=selected,
                usage_records=usage_map.get(selected_id, []),
                tickets=ticket_map.get(selected_id, []),
                subscription=sub_map.get(selected_id),
            )
            st.session_state["qbr_cache"][selected_id] = qbr
            cached = qbr

            # Persist to file-based cache so it survives page navigation
            try:
                existing = json.loads(_QBR_CACHE_FILE.read_text()) if _QBR_CACHE_FILE.exists() else {}
                existing[selected_id] = qbr.model_dump()
                _QBR_CACHE_FILE.write_text(json.dumps(existing))
            except Exception:
                pass

            st.success(f"QBR generated in {resp.latency_ms:.0f}ms via {resp.provider.upper()}")
            st.rerun()

        except ConnectionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"QBR generation failed: {e}")
            raise

if cached:
    qbr = cached

    st.subheader("TAM Summary")
    st.caption("Internal — your quick pre-call snapshot.")
    for bullet in qbr.tam_summary:
        st.markdown(f"- {bullet}")

    st.divider()

    st.subheader("Executive Summary")
    st.caption("Talking points to adapt when opening the QBR with customer stakeholders.")
    for point in qbr.executive_summary:
        st.markdown(f"- {point}")

    st.divider()

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

