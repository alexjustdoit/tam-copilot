import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st
import config  # noqa: F401

from data.models import Customer, SupportTicket
from data.taxonomy import load_taxonomy, save_taxonomy

st.title("AI Ticket Triage")
st.caption("Classify priority, detect sentiment, assess escalation risk, and draft responses — instantly.")

FIXTURES_PATH = Path(__file__).parent.parent.parent / "data" / "fixtures"


@st.cache_data
def load_data():
    customers = [Customer(**c) for c in json.loads((FIXTURES_PATH / "customers.json").read_text())]
    tickets = [SupportTicket(**t) for t in json.loads((FIXTURES_PATH / "tickets.json").read_text())]
    return customers, tickets


def save_ticket(updated_ticket: SupportTicket):
    """Write updated ticket back to fixtures/tickets.json and clear cache."""
    tickets_path = FIXTURES_PATH / "tickets.json"
    all_tickets = json.loads(tickets_path.read_text())
    for i, t in enumerate(all_tickets):
        if t["id"] == updated_ticket.id:
            all_tickets[i] = json.loads(updated_ticket.model_dump_json())
            break
    tickets_path.write_text(json.dumps(all_tickets, indent=2, default=str))
    st.cache_data.clear()


def save_tickets_batch(updated_tickets: list[SupportTicket]):
    """Write multiple updated tickets back to fixtures/tickets.json in a single pass."""
    tickets_path = FIXTURES_PATH / "tickets.json"
    all_tickets = json.loads(tickets_path.read_text())
    updated_map = {t.id: t for t in updated_tickets}
    for i, t in enumerate(all_tickets):
        if t["id"] in updated_map:
            all_tickets[i] = json.loads(updated_map[t["id"]].model_dump_json())
    tickets_path.write_text(json.dumps(all_tickets, indent=2, default=str))
    st.cache_data.clear()


def find_similar(value: str, existing: list, threshold: float = 0.65) -> list:
    """Return existing items that are suspiciously similar to value."""
    value_lower = value.lower().strip()
    results = []
    for item in existing:
        item_lower = item.lower().strip()
        ratio = SequenceMatcher(None, value_lower, item_lower).ratio()
        if ratio >= threshold or value_lower in item_lower or item_lower in value_lower:
            if item not in results:
                results.append(item)
    return results


# ── Data loading ──────────────────────────────────────────────────────────────

customers, tickets = load_data()
customer_map = {c.id: c for c in customers}

# ── Customer selector ─────────────────────────────────────────────────────────

customer_names = {
    c.id: f"{c.company_name} ({c.tier})"
    for c in sorted(customers, key=lambda x: x.arr, reverse=True)
}
selected_id = st.selectbox(
    "Select Customer",
    options=list(customer_names.keys()),
    format_func=lambda x: customer_names[x],
)

customer = customer_map[selected_id]
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Company", customer.company_name)
with col2:
    st.metric("ARR", f"${customer.arr:,.0f}")
with col3:
    st.metric("Tier", customer.tier)

st.divider()

# ── Ticket selector ───────────────────────────────────────────────────────────

customer_tickets = [t for t in tickets if t.customer_id == selected_id]
open_tickets = [t for t in customer_tickets if t.status in ("open", "in_progress")]

st.subheader(f"Open Tickets ({len(open_tickets)})")

if not open_tickets:
    st.info("No open tickets for this customer.")
    st.stop()

ticket_options = {t.id: f"[{t.priority}] {t.title[:70]}" for t in open_tickets}
selected_ticket_id = st.selectbox(
    "Select Ticket to Triage",
    options=list(ticket_options.keys()),
    format_func=lambda x: ticket_options[x],
)

# Reset triage state when ticket changes
if st.session_state.get("triaged_ticket_id") != selected_ticket_id:
    for key in ["triage_result", "triage_resp", "triaged_ticket_id", "triage_action"]:
        st.session_state.pop(key, None)

ticket = next(t for t in open_tickets if t.id == selected_ticket_id)

# ── Ticket details ────────────────────────────────────────────────────────────

with st.expander("Ticket Details", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Priority:** {ticket.priority}")
    with col2:
        st.write(f"**Category:** {ticket.category}")
    with col3:
        st.write(f"**Status:** {ticket.status}")
    tags_display = ", ".join(ticket.tags) if ticket.tags else "_None_"
    st.write(f"**Tags:** {tags_display}")
    st.write(f"**Title:** {ticket.title}")
    st.write("**Description:**")
    st.write(ticket.description)
    st.caption(f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M')} | ID: {ticket.id}")

st.divider()

# ── Triage button ─────────────────────────────────────────────────────────────

already_triaged = "triage_result" in st.session_state
if st.button(
    "Triage with AI",
    type="primary",
    use_container_width=True,
    disabled=already_triaged,
    help="Run again by selecting a different ticket" if already_triaged else None,
):
    with st.spinner("Analyzing ticket..."):
        try:
            from features.ticket_triage import triage_ticket
            result, resp = triage_ticket(ticket)
            st.session_state.triage_result = result
            st.session_state.triage_resp = resp
            st.session_state.triaged_ticket_id = selected_ticket_id
        except ConnectionError as e:
            st.error(f"Cannot connect to Ollama: {e}")
        except Exception as e:
            st.error(f"Triage failed: {e}")
            raise

# ── Triage results ────────────────────────────────────────────────────────────

if "triage_result" in st.session_state and st.session_state.get("triaged_ticket_id") == selected_ticket_id:
    result = st.session_state.triage_result
    resp = st.session_state.triage_resp
    action = st.session_state.get("triage_action")

    # Analysis summary
    st.subheader("AI Analysis")
    col1, col2, col3 = st.columns(3)
    with col1:
        sentiment_emoji = {"positive": "😊", "neutral": "😐", "frustrated": "😤", "angry": "😡"}[result.sentiment]
        st.metric("Sentiment", f"{sentiment_emoji} {result.sentiment.title()}")
    with col2:
        st.metric("Escalation Risk", result.escalation_risk.upper())
    with col3:
        cost_str = f"${resp.estimated_cost_usd:.4f}" if resp.estimated_cost_usd > 0 else "Free (local)"
        st.metric("Cost", cost_str)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Reasoning")
        st.write(result.reasoning)
    with col2:
        st.subheader("Suggested Response")
        st.text_area("Draft Response", result.suggested_response, height=200, key="response_draft")

    st.divider()

    # Suggested changes diff
    st.subheader("Suggested Changes to Ticket")

    priority_changed = result.priority_recommendation != ticket.priority
    category_changed = result.category != ticket.category
    tags_changed = sorted(result.suggested_tags) != sorted(ticket.tags)
    has_new_tag = bool(result.suggested_new_tag)
    has_new_category = bool(result.suggested_new_category)
    any_changes = priority_changed or category_changed or tags_changed or has_new_tag or has_new_category

    if any_changes:
        if priority_changed:
            st.markdown(f"• **Priority:** {ticket.priority} → **{result.priority_recommendation}**")
        if category_changed:
            st.markdown(f"• **Category:** {ticket.category} → **{result.category}**")
        if has_new_category:
            st.warning(f"AI is proposing a new category not in the taxonomy: **{result.suggested_new_category}**")
        if tags_changed or has_new_tag:
            current_tags = ", ".join(ticket.tags) if ticket.tags else "None"
            new_tags = ", ".join(result.suggested_tags) if result.suggested_tags else "None"
            st.markdown(f"• **Tags:** {current_tags} → **{new_tags}**")
        if has_new_tag:
            st.warning(f"AI is proposing a new tag not in the taxonomy: **{result.suggested_new_tag}**")
    else:
        st.info("No changes recommended — current values look correct.")

    # Accept / Manual edit flows
    if action:
        if action == "accepted":
            st.success("✅ AI suggestions accepted and saved.")
        elif action == "manual_saved":
            st.success("✅ Manual changes saved.")
    else:
        st.divider()
        st.markdown("**Apply changes:** choose one of the two options below.")
        col_accept, col_spacer, col_manual = st.columns([5, 1, 6])

        # ── Accept flow ───────────────────────────────────────────────────────
        with col_accept:
            st.markdown("##### ✅ Accept AI Suggestions")
            st.caption("Apply all suggested changes as shown above.")

            if st.button("Accept", type="primary", use_container_width=True, key="btn_accept"):
                taxonomy = load_taxonomy()

                # Build new tags list
                new_tags = list(ticket.tags)
                for tag in result.suggested_tags:
                    if tag not in new_tags:
                        new_tags.append(tag)
                if result.suggested_new_tag and result.suggested_new_tag not in new_tags:
                    new_tags.append(result.suggested_new_tag)
                    if result.suggested_new_tag not in taxonomy["tags"]:
                        taxonomy["tags"].append(result.suggested_new_tag)
                        save_taxonomy(taxonomy)

                # Resolve final category
                final_category = result.suggested_new_category or result.category
                if final_category not in taxonomy["categories"]:
                    taxonomy["categories"].append(final_category)
                    save_taxonomy(taxonomy)

                updated = ticket.model_copy(update={
                    "priority": result.priority_recommendation,
                    "category": final_category,
                    "tags": new_tags,
                })
                save_ticket(updated)
                st.session_state.triage_action = "accepted"
                st.rerun()

        # ── Manual edit flow ──────────────────────────────────────────────────
        with col_manual:
            st.markdown("##### ✏️ Edit Manually")
            st.caption("Pre-populated with current ticket values — not the AI suggestions.")

            taxonomy = load_taxonomy()

            manual_priority = st.selectbox(
                "Priority",
                options=["P1", "P2", "P3", "P4"],
                index=["P1", "P2", "P3", "P4"].index(ticket.priority),
                key="manual_priority",
            )

            cat_options = taxonomy["categories"]
            cat_index = cat_options.index(ticket.category) if ticket.category in cat_options else 0
            manual_category = st.selectbox(
                "Category",
                options=cat_options,
                index=cat_index,
                key="manual_category",
            )

            new_cat_input = st.text_input(
                "Add new category (optional)",
                key="new_category_input",
                placeholder="Only if none of the above fit...",
            )
            if new_cat_input.strip():
                similar_cats = find_similar(new_cat_input.strip(), taxonomy["categories"])
                if similar_cats:
                    st.warning(f"Similar category already exists: **{', '.join(similar_cats)}** — consider using that instead.")

            manual_tags = st.multiselect(
                "Tags",
                options=taxonomy["tags"],
                default=[t for t in ticket.tags if t in taxonomy["tags"]],
                key="manual_tags",
            )

            new_tag_input = st.text_input(
                "Add new tag (optional)",
                key="new_tag_input",
                placeholder="Only if none of the above fit...",
            )
            if new_tag_input.strip():
                similar_tags = find_similar(new_tag_input.strip(), taxonomy["tags"])
                if similar_tags:
                    st.warning(f"Similar tag already exists: **{', '.join(similar_tags)}** — consider using that instead.")

            if st.button("Save Manual Changes", use_container_width=True, key="btn_manual_save"):
                taxonomy = load_taxonomy()

                final_category = new_cat_input.strip() if new_cat_input.strip() else manual_category
                if new_cat_input.strip() and final_category not in taxonomy["categories"]:
                    taxonomy["categories"].append(final_category)
                    save_taxonomy(taxonomy)

                final_tags = list(manual_tags)
                if new_tag_input.strip() and new_tag_input.strip() not in final_tags:
                    final_tags.append(new_tag_input.strip())
                    if new_tag_input.strip() not in taxonomy["tags"]:
                        taxonomy["tags"].append(new_tag_input.strip())
                        save_taxonomy(taxonomy)

                updated = ticket.model_copy(update={
                    "priority": manual_priority,
                    "category": final_category,
                    "tags": final_tags,
                })
                save_ticket(updated)
                st.session_state.triage_action = "manual_saved"
                st.rerun()

    st.divider()

    # Provider metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Provider", resp.provider.upper())
    with col2:
        st.metric("Latency", f"{resp.latency_ms:.0f}ms")
    with col3:
        cost_str = f"${resp.estimated_cost_usd:.4f}" if resp.estimated_cost_usd > 0 else "Free (local)"
        st.metric("Cost", cost_str)

st.divider()

# ── Batch triage ──────────────────────────────────────────────────────────────

st.subheader("Batch Triage")
st.caption("Triage un-triaged open tickets in bulk. Scoped by customer, TAM, or full portfolio.")

all_tams = sorted(set(c.tam_owner for c in customers))

scope = st.radio(
    "Scope",
    ["Current customer", "By TAM", "All customers"],
    horizontal=True,
    key="batch_scope",
)

selected_tam = None
if scope == "By TAM":
    selected_tam = st.selectbox("TAM", all_tams, key="batch_tam_select")

# Un-triaged = open/in_progress with no tags applied yet
if scope == "Current customer":
    batch_tickets = [t for t in open_tickets if not t.tags]
elif scope == "By TAM":
    tam_ids = {c.id for c in customers if c.tam_owner == selected_tam}
    batch_tickets = [
        t for t in tickets
        if t.customer_id in tam_ids and t.status in ("open", "in_progress") and not t.tags
    ]
else:
    batch_tickets = [
        t for t in tickets
        if t.status in ("open", "in_progress") and not t.tags
    ]

# Reset results when scope changes
scope_key = (scope, selected_tam)
if st.session_state.get("_batch_scope_key") != scope_key:
    st.session_state.pop("batch_results", None)
    st.session_state["_batch_scope_key"] = scope_key

if not batch_tickets:
    st.success("No un-triaged tickets in scope — all caught up.")
else:
    st.info(f"{len(batch_tickets)} un-triaged ticket{'s' if len(batch_tickets) != 1 else ''} in scope.")

    if st.button("Run Batch Triage", type="primary", use_container_width=True, key="btn_batch_run"):
        progress = st.progress(0, text="Triaging...")
        try:
            from features.ticket_triage import triage_ticket
            results = []
            for i, t in enumerate(batch_tickets):
                try:
                    result, resp = triage_ticket(t)
                    results.append((t, result, resp))
                except Exception as e:
                    st.warning(f"Failed {t.id}: {e}")
                progress.progress((i + 1) / len(batch_tickets), text=f"Triaged {i + 1}/{len(batch_tickets)}")
            progress.empty()
            st.session_state.batch_results = results
        except ConnectionError as e:
            st.error(str(e))

if st.session_state.get("batch_results"):
    results = st.session_state.batch_results
    include_company = scope != "Current customer"

    rows = []
    for t, r, resp in results:
        c = customer_map.get(t.customer_id)
        row = {}
        if include_company:
            row["Company"] = c.company_name if c else "—"
            row["TAM"] = c.tam_owner if c else "—"
        priority_str = f"{t.priority} → {r.priority_recommendation}" if r.priority_recommendation != t.priority else t.priority
        row.update({
            "Ticket": t.title[:50],
            "Priority": priority_str,
            "Category": r.category,
            "Sentiment": r.sentiment,
            "Escalation": r.escalation_risk,
            "Suggested Tags": ", ".join(r.suggested_tags) if r.suggested_tags else "—",
            "Latency (ms)": round(resp.latency_ms),
        })
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    total_cost = sum(r.estimated_cost_usd for _, _, r in results)
    cost_str = f"${total_cost:.4f}" if total_cost > 0 else "Free (local)"
    st.caption(f"{len(results)} tickets · Provider: {results[0][2].provider.upper()} · Cost: {cost_str}")

    st.divider()
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("**Save All AI Suggestions** — applies recommended priority, category, and tags to every ticket above.")
    with col2:
        if st.button("Save All", type="primary", use_container_width=True, key="btn_batch_save"):
            from data.taxonomy import load_taxonomy, save_taxonomy
            taxonomy = load_taxonomy()
            updated = []
            for t, r, _ in results:
                new_tags = list(t.tags)
                for tag in r.suggested_tags:
                    if tag not in new_tags:
                        new_tags.append(tag)
                    if tag not in taxonomy["tags"]:
                        taxonomy["tags"].append(tag)
                if r.suggested_new_tag and r.suggested_new_tag not in new_tags:
                    new_tags.append(r.suggested_new_tag)
                    if r.suggested_new_tag not in taxonomy["tags"]:
                        taxonomy["tags"].append(r.suggested_new_tag)
                final_category = r.suggested_new_category or r.category
                if final_category not in taxonomy["categories"]:
                    taxonomy["categories"].append(final_category)
                updated.append(t.model_copy(update={
                    "priority": r.priority_recommendation,
                    "category": final_category,
                    "tags": new_tags,
                }))
            save_taxonomy(taxonomy)
            save_tickets_batch(updated)
            st.session_state.pop("batch_results", None)
            st.success(f"✅ {len(updated)} tickets saved.")
            st.rerun()
