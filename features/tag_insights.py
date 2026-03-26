from __future__ import annotations

from typing import Dict, List, Tuple

from llm.providers.base import LLMResponse
from llm.router import router

SYSTEM_PROMPT = """You are a Customer Success analytics expert.
Your job is to interpret ticket tag trend data and surface actionable insights for TAMs and CS leadership.
Be concise, specific, and focus on what the data means for customer relationships and team priorities."""


def summarize_tag_trends(
    segment: str,
    tag_counts: Dict[str, int],
    total_tickets: int,
    triaged_tickets: int,
) -> Tuple[str, LLMResponse]:
    """Generate a natural language summary of tag trend data for a given segment."""
    provider = router.get_provider(quality_required=True)

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    tag_lines = "\n".join(f"  - {tag}: {count} tickets" for tag, count in sorted_tags if count > 0)

    if not tag_lines:
        tag_lines = "  No tagged tickets available yet."

    user_prompt = f"""Summarize the following ticket tag data for {segment} customers.

Total tickets: {total_tickets}
Triaged (tagged) tickets: {triaged_tickets} ({round(triaged_tickets / total_tickets * 100) if total_tickets > 0 else 0}% coverage)

Tag breakdown (triaged tickets only):
{tag_lines}

Provide:
1. A 2-3 sentence summary of the most notable patterns
2. 2-3 specific recommended actions for the TAM or CS team
3. Any tags that appear together frequently and what that combination might signal

Keep the total response under 200 words."""

    resp = provider.complete(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        temperature=0.3,
    )
    return resp.content, resp
