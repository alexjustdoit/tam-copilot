import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st
st.markdown("<style>[data-testid='stSidebarNav'],[data-testid='stSidebarNavItems'],[data-testid='stSidebarNavLink']{display:none!important}</style>", unsafe_allow_html=True)
import config  # noqa: F401

from data.taxonomy import load_taxonomy
from llm.router import LLMRouter

st.title("Technical Info")
st.caption("Developer reference — provider config, routing rules, environment, and data stats.")

router = LLMRouter()
use_local = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"

# ── LLM Provider Architecture ──────────────────────────────────────────────────

st.subheader("LLM Provider Architecture")

provider_data = {
    "Provider": ["Ollama (local)", "GPT-5.4-nano", "Claude Haiku 4.5"],
    "Cost": ["Free", "~$0.001/call", "~$0.003/call"],
    "Speed": ["Varies by GPU", "~1.5s", "~1.5s"],
    "Use Case": ["Development / demo", "Production (cheap)", "Quality tasks (P1 triage, QBR)"],
}
st.dataframe(pd.DataFrame(provider_data), use_container_width=True, hide_index=True)

st.divider()

# ── Active Provider Config ─────────────────────────────────────────────────────

st.subheader("Active Provider Config")

col1, col2, col3 = st.columns(3)
with col1:
    mode = "Local (Ollama)" if use_local else "API"
    st.metric("Mode", mode)
with col2:
    if use_local:
        st.metric("Standard Tasks", router.DEFAULT_LOCAL_MODEL)
    else:
        st.metric("Standard Tasks", router.DEFAULT_CHEAP_API)
with col3:
    if use_local:
        st.metric("Quality Tasks", router.DEFAULT_LOCAL_MODEL)
    elif os.getenv("ANTHROPIC_API_KEY"):
        st.metric("Quality Tasks", router.DEFAULT_QUALITY_API)
    else:
        st.metric("Quality Tasks", f"{router.DEFAULT_CHEAP_API} (fallback — no Anthropic key)")

# ── Ollama Status ──────────────────────────────────────────────────────────────

st.divider()
st.subheader("Ollama")

ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Base URL", ollama_url)
with col2:
    st.metric("Model", router.DEFAULT_LOCAL_MODEL)

try:
    import httpx
    resp = httpx.get(f"{ollama_url}/api/tags", timeout=3.0)
    if resp.status_code == 200:
        tags = resp.json().get("models", [])
        pulled = [m["name"] for m in tags]
        if router.DEFAULT_LOCAL_MODEL in pulled or any(router.DEFAULT_LOCAL_MODEL in m for m in pulled):
            st.success(f"Ollama reachable · {router.DEFAULT_LOCAL_MODEL} is available")
        else:
            st.warning(
                f"Ollama reachable but **{router.DEFAULT_LOCAL_MODEL}** is not pulled. "
                f"Run: `ollama pull {router.DEFAULT_LOCAL_MODEL}`"
            )
        if pulled:
            with st.expander(f"All pulled models ({len(pulled)})"):
                st.write("  \n".join(f"• {m}" for m in pulled))
    else:
        st.error(f"Ollama responded with HTTP {resp.status_code}")
except Exception:
    st.error(f"Ollama not reachable at `{ollama_url}` — start Ollama or set OLLAMA_BASE_URL in .env")

# ── Environment Variables ──────────────────────────────────────────────────────

st.divider()
st.subheader("Environment Variables")

def _mask(val: str | None) -> str:
    if not val:
        return "—"
    if len(val) <= 8:
        return "***"
    return val[:4] + "***" + val[-4:]

import pandas as pd

env_rows = [
    {
        "Variable": "USE_LOCAL_LLM",
        "Current Value": os.getenv("USE_LOCAL_LLM", "true"),
        "Default": "true",
        "Description": "true → Ollama (free); false → OpenAI / Claude",
    },
    {
        "Variable": "OLLAMA_BASE_URL",
        "Current Value": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "Default": "http://localhost:11434",
        "Description": "Ollama API endpoint (override for WSL2 / remote host)",
    },
    {
        "Variable": "OPENAI_API_KEY",
        "Current Value": _mask(os.getenv("OPENAI_API_KEY")),
        "Default": "—",
        "Description": "Required when USE_LOCAL_LLM=false",
    },
    {
        "Variable": "ANTHROPIC_API_KEY",
        "Current Value": _mask(os.getenv("ANTHROPIC_API_KEY")),
        "Default": "—",
        "Description": "Optional — enables quality routing for P1 triage, QBR, tag insights",
    },
    {
        "Variable": "OPENAI_MODEL",
        "Current Value": os.getenv("OPENAI_MODEL", "gpt-5.4-nano"),
        "Default": "gpt-5.4-nano",
        "Description": "Override the default OpenAI model",
    },
]
st.dataframe(pd.DataFrame(env_rows), use_container_width=True, hide_index=True)

# ── Quality Routing Rules ──────────────────────────────────────────────────────

st.divider()
st.subheader("Quality Routing Rules")
st.caption(
    "When USE_LOCAL_LLM=false, features flagged quality_required=True route to Claude Haiku "
    "if ANTHROPIC_API_KEY is set, otherwise fall back to the OpenAI model."
)

routing_rows = [
    {"Feature": "Ticket Triage (P1)", "quality_required": "True", "Reason": "P1 tickets are customer-critical"},
    {"Feature": "Ticket Triage (P2–P4)", "quality_required": "False", "Reason": "Cheaper model is sufficient"},
    {"Feature": "Churn Risk (< 90 days to renewal)", "quality_required": "True", "Reason": "Urgent — near-term renewal"},
    {"Feature": "Churn Risk (> 90 days)", "quality_required": "False", "Reason": "Routine assessment"},
    {"Feature": "QBR Preparation", "quality_required": "True", "Reason": "Executive-facing output"},
    {"Feature": "Tag Insights / AI Narrative", "quality_required": "True", "Reason": "Nuanced CS analysis"},
    {"Feature": "Health Score", "quality_required": "False", "Reason": "Structured scoring, not prose"},
    {"Feature": "Expansion Intelligence", "quality_required": "False", "Reason": "Signal-based, structured output"},
]
st.dataframe(pd.DataFrame(routing_rows), use_container_width=True, hide_index=True)

# ── Data Stats ─────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Fixture Data")

fixtures = Path(__file__).parent.parent.parent / "data" / "fixtures"
try:
    customers = json.loads((fixtures / "customers.json").read_text())
    tickets = json.loads((fixtures / "tickets.json").read_text())
    usage = json.loads((fixtures / "usage.json").read_text())
    subscriptions = json.loads((fixtures / "subscriptions.json").read_text())
    taxonomy = load_taxonomy()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Customers", len(customers))
    with col2:
        st.metric("Tickets", len(tickets))
    with col3:
        st.metric("Usage Records", len(usage))
    with col4:
        st.metric("Taxonomy Tags", len(taxonomy["tags"]))
    with col5:
        st.metric("Taxonomy Categories", len(taxonomy["categories"]))

    open_tickets = sum(1 for t in tickets if t["status"] in ("open", "in_progress"))
    tagged = sum(1 for t in tickets if t.get("tags"))
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Open / In-Progress Tickets", open_tickets)
    with col2:
        st.metric("Tagged Tickets", tagged)
    with col3:
        st.metric("Triage Coverage", f"{round(tagged / len(tickets) * 100)}%" if tickets else "—")
except FileNotFoundError:
    st.error("Fixture files not found. Run `python data/seed.py` to generate them.")

# ── Eval Framework ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("Eval Framework")

eval_dataset = Path(__file__).parent.parent.parent / "eval" / "datasets" / "ticket_triage_eval.jsonl"
eval_results = Path(__file__).parent.parent.parent / "eval" / "results.json"

col1, col2 = st.columns(2)
with col1:
    if eval_dataset.exists():
        cases = [l for l in eval_dataset.read_text().splitlines() if l.strip()]
        st.metric("Eval Dataset", f"{len(cases)} labeled cases")
    else:
        st.metric("Eval Dataset", "Not found")
with col2:
    if eval_results.exists():
        results = json.loads(eval_results.read_text())
        providers_run = ", ".join(r["provider"] for r in results)
        st.metric("Last Eval Run", providers_run)
    else:
        st.metric("Last Eval Run", "No results yet")

st.markdown("**Run from CLI:**")
st.code("python eval/evaluator.py --providers openai,claude", language="bash")
st.code("python eval/evaluator.py --providers local", language="bash")

# ── Stack Versions ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("Stack")

import streamlit
import pydantic

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
with col2:
    st.metric("Streamlit", streamlit.__version__)
with col3:
    st.metric("Pydantic", pydantic.__version__)

# ── Links ──────────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Links")
st.markdown("""
- [GitHub Repository](https://github.com/alexjustdoit/tam-copilot)
- [Releases](https://github.com/alexjustdoit/tam-copilot/releases)
- [Streamlit Docs — st.navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation)
- [Ollama Model Library](https://ollama.com/library)
""")
