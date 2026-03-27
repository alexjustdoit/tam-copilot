import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
import config  # noqa: F401
from app.components.sidebar import render_sidebar

st.set_page_config(page_title="Eval Dashboard — TAM Copilot", layout="wide")
render_sidebar()
st.title("Provider Evaluation Dashboard")
st.caption("Compare Ollama, GPT-4o-mini, and Claude Haiku on accuracy, latency, and cost.")

DATASET_PATH = Path(__file__).parent.parent.parent / "eval" / "datasets" / "ticket_triage_eval.jsonl"
RESULTS_PATH = Path(__file__).parent.parent.parent / "eval" / "results.json"


def load_dataset():
    cases = []
    with open(DATASET_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


# Sidebar: provider selection
st.sidebar.subheader("Run Eval")
providers_to_run = st.sidebar.multiselect(
    "Providers",
    ["local", "openai", "claude"],
    default=["openai"],
    help="'local' requires Ollama running"
)

run_eval = st.sidebar.button("Run Eval", type="primary")

# Load existing results if available
existing_results = []
if RESULTS_PATH.exists():
    existing_results = json.loads(RESULTS_PATH.read_text())

if run_eval and providers_to_run:
    dataset = load_dataset()
    st.info(f"Running eval on {len(dataset)} cases with: {', '.join(providers_to_run)}")

    from eval.evaluator import run_eval as _run_eval

    reports = []
    progress = st.progress(0)
    for i, pname in enumerate(providers_to_run):
        with st.spinner(f"Running {pname}..."):
            try:
                report = _run_eval(pname, dataset)
                reports.append(report)
                existing_results = [r for r in existing_results if r.get("provider") != pname]
                existing_results.append(report.summary())
            except Exception as e:
                st.error(f"Error running {pname}: {e}")
        progress.progress((i + 1) / len(providers_to_run))

    RESULTS_PATH.write_text(json.dumps(existing_results, indent=2))
    st.success("Eval complete!")

# Display results
if existing_results:
    st.subheader("Summary Comparison")

    df = pd.DataFrame(existing_results)
    df["avg_accuracy_pct"] = (df["avg_accuracy"] * 100).round(1)

    col1, col2, col3 = st.columns(3)

    with col1:
        fig = px.bar(df, x="provider", y="avg_accuracy_pct", title="Accuracy (%)",
                     color="provider", text="avg_accuracy_pct",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(showlegend=False, yaxis_range=[0, 105])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(df, x="provider", y="avg_latency_ms", title="Avg Latency (ms)",
                     color="provider", text="avg_latency_ms",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(texttemplate="%{text:.0f}ms", textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        fig = px.bar(df, x="provider", y="cost_per_case_usd", title="Cost per Case (USD)",
                     color="provider", text="cost_per_case_usd",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(texttemplate="$%{text:.5f}", textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Detailed Results Table")

    display_df = df[["provider", "model", "cases", "avg_accuracy_pct", "avg_latency_ms", "total_cost_usd", "cost_per_case_usd"]].copy()
    display_df.columns = ["Provider", "Model", "Cases", "Accuracy %", "Avg Latency (ms)", "Total Cost $", "Cost/Case $"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("No eval results yet. Select providers in the sidebar and click 'Run Eval'.")
    st.markdown("""
**How it works:**
1. Select one or more providers (local requires Ollama)
2. Click Run Eval
3. Each provider runs against 20 labeled ticket triage cases
4. Results are scored on priority, sentiment, escalation risk, and category accuracy
5. Compare accuracy vs latency vs cost trade-offs
""")

    # Show the eval dataset preview
    st.subheader("Eval Dataset Preview (20 Cases)")
    dataset = load_dataset()
    rows = [{"ID": c["id"], "Title": c["ticket"]["title"][:60], "Expected Priority": c["expected"]["priority_recommendation"], "Expected Sentiment": c["expected"]["sentiment"], "Expected Risk": c["expected"]["escalation_risk"]} for c in dataset]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
