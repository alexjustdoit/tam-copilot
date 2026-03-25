"""
Run eval comparison across providers.

Usage:
    python eval/evaluator.py --providers openai,claude
    python eval/evaluator.py --providers local --dataset eval/datasets/ticket_triage_eval.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from typing import List

from rich.console import Console
from rich.table import Table

from eval.metrics import EvalReport, EvalResult, score_triage
from features.ticket_triage import TicketTriageResult
from llm.router import LLMRouter

console = Console()
DATASET_PATH = Path(__file__).parent / "datasets" / "ticket_triage_eval.jsonl"


def load_dataset(path: Path) -> List[dict]:
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run_eval(provider_name: str, dataset: List[dict]) -> EvalReport:
    router = LLMRouter()
    provider = router.get_provider_by_name(provider_name)
    results = []

    from features.ticket_triage import SYSTEM_PROMPT

    for case in dataset:
        ticket = case["ticket"]
        expected = case["expected"]

        user_prompt = f"""Triage this support ticket:

Title: {ticket['title']}
Category: {ticket['category']}
Current Priority: {ticket['priority']}
Status: {ticket.get('status', 'open')}

Description:
{ticket['description']}

Provide your structured assessment."""

        try:
            parsed, resp = provider.complete_structured(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=TicketTriageResult,
                temperature=0.1,
            )
            output = parsed.model_dump()
        except Exception as e:
            console.print(f"[red]Error on case {case['id']}: {e}[/red]")
            output = {}

        accuracy, field_scores = score_triage(output, expected)
        results.append(EvalResult(
            case_id=case["id"],
            provider=provider_name,
            model=getattr(provider, "model", "unknown"),
            output=output,
            expected=expected,
            accuracy_score=accuracy,
            latency_ms=resp.latency_ms if "resp" in dir() else 0,
            estimated_cost_usd=resp.estimated_cost_usd if "resp" in dir() else 0,
            field_scores=field_scores,
        ))

    return EvalReport(
        provider=provider_name,
        model=getattr(provider, "model", "unknown"),
        results=results,
    )


def print_comparison(reports: List[EvalReport]):
    table = Table(title="Provider Comparison — Ticket Triage Eval")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Cases")
    table.add_column("Accuracy", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("Total Cost", justify="right")
    table.add_column("Cost/Case", justify="right")

    for report in reports:
        s = report.summary()
        table.add_row(
            s["provider"],
            s["model"],
            str(s["cases"]),
            f"{s['avg_accuracy']:.1%}",
            f"{s['avg_latency_ms']:.0f}ms",
            f"${s['total_cost_usd']:.4f}",
            f"${s['cost_per_case_usd']:.5f}",
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="openai", help="Comma-separated: local,openai,claude")
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    console.print(f"Loaded {len(dataset)} eval cases from {args.dataset}")

    provider_names = [p.strip() for p in args.providers.split(",")]
    reports = []

    for pname in provider_names:
        console.print(f"\nRunning eval with provider: [bold]{pname}[/bold]")
        report = run_eval(pname, dataset)
        reports.append(report)
        console.print(f"  Accuracy: {report.avg_accuracy:.1%}, Latency: {report.avg_latency_ms:.0f}ms, Cost: ${report.total_cost_usd:.4f}")

    print_comparison(reports)

    # Save results
    output_path = Path(__file__).parent / "results.json"
    output_path.write_text(json.dumps([r.summary() for r in reports], indent=2))
    console.print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
