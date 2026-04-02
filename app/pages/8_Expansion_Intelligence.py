import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st
st.markdown("<style>[data-testid='stSidebarNav'],[data-testid='stSidebarNavItems'],[data-testid='stSidebarNavLink']{display:none!important}</style>", unsafe_allow_html=True)
import config  # noqa: F401

from data.models import Customer, Subscription, UsageMetrics
from data.session_store import get_fixtures_dir
from features.expansion import ALL_FEATURES, INDUSTRY_FEATURE_BENCHMARKS

st.title("Expansion Intelligence")
st.caption("AI-powered upsell and cross-sell opportunity finder using usage patterns and industry benchmarks.")


@st.cache_data
def load_data(fixtures_dir: str):
    fixtures = Path(fixtures_dir)
    customers = [Customer(**c) for c in json.loads((fixtures / "customers.json").read_text())]
    usage = [UsageMetrics(**u) for u in json.loads((fixtures / "usage.json").read_text())]
    subscriptions = [Subscription(**s) for s in json.loads((fixtures / "subscriptions.json").read_text())]
    return customers, usage, subscriptions


customers, usage, subscriptions = load_data(str(get_fixtures_dir()))
sub_map = {s.customer_id: s for s in subscriptions}
usage_map: dict[str, list] = {}
for u in usage:
    usage_map.setdefault(u.customer_id, []).append(u)


def compute_expansion_score(c: Customer) -> int:
    """Heuristic expansion signal score for pre-ranking without LLM."""
    score = 0
    sub = sub_map.get(c.id)
    records = sorted(usage_map.get(c.id, []), key=lambda r: r.month)

    # Seat utilization near ceiling → seat expansion signal
    if sub and sub.seats_purchased > 0:
        util = sub.seats_used / sub.seats_purchased
        if util >= 0.9:
            score += 4
        elif util >= 0.75:
            score += 2

    # High engagement (DAU/MAU) → receptive to upsell
    if records:
        latest = records[-1]
        dau_mau = latest.dau / latest.mau if latest.mau > 0 else 0
        if dau_mau >= 0.4:
            score += 3
        elif dau_mau >= 0.25:
            score += 1

    # Feature gaps vs. industry peers
    adopted = set(records[-1].features_adopted) if records else set()
    peer_features = INDUSTRY_FEATURE_BENCHMARKS.get(c.industry, [])
    missing_peer = sum(1 for f in peer_features if f not in adopted)
    score += missing_peer

    # Unadopted features overall (more gaps = more opportunities)
    unadopted_count = len([f for f in ALL_FEATURES if f not in adopted])
    if unadopted_count >= 8:
        score += 2
    elif unadopted_count >= 5:
        score += 1

    # Not on top tier → tier upgrade possible
    if c.tier in ("SMB", "Mid-Market"):
        score += 1

    return score


ranked = sorted(customers, key=lambda c: compute_expansion_score(c), reverse=True)

all_tams = sorted(set(c.tam_owner for c in customers))

# --- Filters ---
_all_segments = ["Enterprise", "Mid-Market", "SMB"]
if "filter_segments" not in st.session_state:
    st.session_state["filter_segments"] = _all_segments
if "filter_tams" not in st.session_state:
    st.session_state["filter_tams"] = all_tams
else:
    st.session_state["filter_tams"] = [t for t in st.session_state["filter_tams"] if t in all_tams]

st.subheader("Expansion Opportunity Overview")
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

# --- Summary table ---
rows = []
for c in filtered:
    sub = sub_map.get(c.id)
    records = sorted(usage_map.get(c.id, []), key=lambda r: r.month)
    adopted = set(records[-1].features_adopted) if records else set()
    seat_util = (sub.seats_used / sub.seats_purchased) if sub and sub.seats_purchased > 0 else None
    peer_features = INDUSTRY_FEATURE_BENCHMARKS.get(c.industry, [])
    missing_peer = sum(1 for f in peer_features if f not in adopted)
    dau_mau = 0.0
    if records:
        latest = records[-1]
        dau_mau = latest.dau / latest.mau if latest.mau > 0 else 0

    rows.append({
        "Company": c.company_name,
        "Segment": c.tier,
        "ARR": c.arr,
        "Industry": c.industry,
        "Seat Util %": round(seat_util * 100) if seat_util is not None else 0,
        "DAU/MAU %": round(dau_mau * 100),
        "Features Adopted": f"{len(adopted)}/{len(ALL_FEATURES)}",
        "Missing Peer Features": missing_peer,
        "Expansion Score": compute_expansion_score(c),
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, height=400)

st.divider()

# --- Deep-dive ---
st.subheader("AI Expansion Analysis")
account_names = {c.id: f"{c.company_name} ({c.tier})" for c in filtered}
selected_id = st.selectbox(
    "Select Account",
    options=[c.id for c in filtered],
    format_func=lambda x: account_names[x],
)
selected_customer = next(c for c in customers if c.id == selected_id)

if st.button("Find Expansion Opportunities", type="primary", use_container_width=True):
    with st.spinner("Analyzing expansion signals..."):
        try:
            from features.expansion import find_expansion_opportunities

            result, resp = find_expansion_opportunities(
                customer=selected_customer,
                usage_records=usage_map.get(selected_id, []),
                subscription=sub_map.get(selected_id),
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Expansion Potential", result.total_expansion_potential)
            with col2:
                st.metric("Opportunities Found", len(result.opportunities))
            with col3:
                st.metric("Provider / Latency", f"{resp.provider.upper()} / {resp.latency_ms:.0f}ms")

            st.divider()

            st.subheader("Opportunities")
            confidence_icons = {"Low": "🟡", "Medium": "🟠", "High": "🟢"}
            type_icons = {
                "Seat Expansion": "👥",
                "Tier Upgrade": "⬆️",
                "Add-on": "➕",
                "Cross-sell": "🔀",
            }

            for opp in result.opportunities:
                icon = type_icons.get(opp.opportunity_type, "•")
                conf_icon = confidence_icons.get(opp.confidence, "")
                with st.expander(
                    f"{icon} {opp.opportunity_type} — {opp.feature_or_product}  |  {conf_icon} {opp.confidence} confidence  |  {opp.estimated_arr_uplift}"
                ):
                    st.markdown(f"**Rationale:** {opp.rationale}")
                    st.info(f"**Suggested pitch:** {opp.suggested_pitch}")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Best Opportunity")
                st.write(result.best_opportunity_summary)
            with col2:
                st.subheader("Recommended Next Step")
                st.write(result.recommended_next_step)

        except ConnectionError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            raise
