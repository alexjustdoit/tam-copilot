import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
st.markdown("<style>[data-testid='stSidebarNav'],[data-testid='stSidebarNavItems'],[data-testid='stSidebarNavLink']{display:none!important}</style>", unsafe_allow_html=True)
import config  # noqa: F401

st.title("Provider Evaluation Dashboard")
st.caption("Compare Ollama, GPT-5.4-nano, and Claude Haiku on accuracy, latency, and cost across multiple features.")

TRIAGE_DATASET_PATH = Path(__file__).parent.parent.parent / "eval" / "datasets" / "ticket_triage_eval.jsonl"
QBR_DATASET_PATH = Path(__file__).parent.parent.parent / "eval" / "datasets" / "qbr_eval.jsonl"
CHURN_DATASET_PATH = Path(__file__).parent.parent.parent / "eval" / "datasets" / "churn_eval.jsonl"
RESULTS_PATH = Path(__file__).parent.parent.parent / "eval" / "results.json"


def load_dataset(path):
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


# Sidebar: evaluation type and provider selection
st.sidebar.divider()
st.sidebar.subheader("Run Eval")

eval_type = st.sidebar.radio(
    "Select feature to evaluate",
    ["Ticket Triage", "QBR Prep", "Churn Risk"],
    horizontal=True
)

dataset_paths = {
    "Ticket Triage": TRIAGE_DATASET_PATH,
    "QBR Prep": QBR_DATASET_PATH,
    "Churn Risk": CHURN_DATASET_PATH,
}

providers_to_run = st.sidebar.multiselect(
    "Providers",
    ["local", "openai", "claude"],
    default=["openai"],
    help="'local' requires Ollama running"
)

run_eval_btn = st.sidebar.button("Run Eval", type="primary")

# Load existing results if available
existing_results = []
if RESULTS_PATH.exists():
    existing_results = json.loads(RESULTS_PATH.read_text())

if run_eval_btn and providers_to_run:
    dataset_path = dataset_paths[eval_type]
    dataset = load_dataset(dataset_path)
    st.info(f"Running {eval_type} eval on {len(dataset)} cases with: {', '.join(providers_to_run)}")

    reports = []
    progress = st.progress(0)
    for i, pname in enumerate(providers_to_run):
        with st.spinner(f"Running {pname}..."):
            try:
                if eval_type == "Ticket Triage":
                    from eval.evaluator import run_eval as _run_eval
                    report = _run_eval(pname, dataset)
                elif eval_type == "QBR Prep":
                    from eval.evaluator import run_qbr_eval
                    report = run_qbr_eval(pname, dataset)
                else:  # Churn Risk
                    from eval.evaluator import run_churn_eval
                    report = run_churn_eval(pname, dataset)

                reports.append(report)
                existing_results = [r for r in existing_results if not (r.get("provider") == pname and r.get("feature") == eval_type)]
                result_summary = report.summary()
                result_summary["feature"] = eval_type
                existing_results.append(result_summary)
            except Exception as e:
                st.error(f"Error running {pname}: {e}")
        progress.progress((i + 1) / len(providers_to_run))

    RESULTS_PATH.write_text(json.dumps(existing_results, indent=2))
    st.success("Eval complete!")

# Display results filtered by eval type
if existing_results:
    # Filter results by selected eval type
    filtered_results = [r for r in existing_results if r.get("feature") == eval_type]

    if filtered_results:
        st.subheader(f"Summary Comparison — {eval_type}")

        df = pd.DataFrame(filtered_results)
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
        st.info(f"No results for {eval_type} yet. Run eval to see results.")

else:
    st.info(f"No eval results yet. Select providers in the sidebar and click 'Run Eval'.")
    st.markdown(f"""
**How it works:**
1. Select a feature to evaluate: Ticket Triage, QBR Prep, or Churn Risk
2. Select one or more providers (local requires Ollama)
3. Click Run Eval
4. Each provider runs against test cases for the selected feature
5. Results are scored on accuracy, latency, and cost
6. Compare trade-offs across providers
""")

    # Show the eval dataset preview for selected eval type
    st.subheader(f"Eval Dataset Preview — {eval_type}")
    dataset = load_dataset(dataset_paths[eval_type])

    if eval_type == "Ticket Triage":
        rows = [{"ID": c["id"], "Title": c["ticket"]["title"][:60], "Expected Priority": c["expected"]["priority_recommendation"]} for c in dataset]
    elif eval_type == "QBR Prep":
        rows = [{"ID": c["id"], "Company": c["customer"]["company_name"], "Tier": c["customer"]["tier"], "ARR": f"${c['customer']['arr']:,}"} for c in dataset]
    else:  # Churn Risk
        rows = [{"ID": c["id"], "Company": c["customer"]["company_name"], "Tier": c["customer"]["tier"], "Days to Renewal": (c["customer"]["renewal_date"] - pd.Timestamp.now().date()).days} for c in dataset]

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
