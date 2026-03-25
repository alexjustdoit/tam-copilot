from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Literal, Tuple

from pydantic import BaseModel

from data.models import SupportTicket
from llm.providers.base import LLMResponse
from llm.router import router

SYSTEM_PROMPT = """You are an expert Technical Account Manager (TAM) assistant.
Your job is to triage customer support tickets and provide actionable assessments.
Be concise, professional, and prioritize customer impact.

Analyze each ticket for:
- Correct priority (P1=system down/data loss, P2=major impact, P3=partial degradation, P4=general inquiry)
- Sentiment and frustration level
- Escalation risk
- A professional suggested response draft
"""


class TicketTriageResult(BaseModel):
    priority_recommendation: Literal["P1", "P2", "P3", "P4"]
    category: str
    sentiment: Literal["positive", "neutral", "frustrated", "angry"]
    escalation_risk: Literal["low", "medium", "high", "critical"]
    suggested_response: str
    reasoning: str


def triage_ticket(ticket: SupportTicket) -> Tuple[TicketTriageResult, LLMResponse]:
    """Triage a single ticket. P1s route to quality provider."""
    quality_required = ticket.priority == "P1"
    provider = router.get_provider(quality_required=quality_required)

    user_prompt = f"""Triage this support ticket:

Title: {ticket.title}
Category: {ticket.category}
Current Priority: {ticket.priority}
Status: {ticket.status}

Description:
{ticket.description}

Provide your structured assessment."""

    return provider.complete_structured(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        schema=TicketTriageResult,
        temperature=0.1,
    )


def triage_tickets_batch(
    tickets: List[SupportTicket],
    max_workers: int = 5,
) -> List[Tuple[SupportTicket, TicketTriageResult, LLMResponse]]:
    """Triage multiple tickets concurrently using a thread pool."""
    results = []

    def _triage(ticket):
        result, resp = triage_ticket(ticket)
        return ticket, result, resp

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_triage, t): t for t in tickets}
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                ticket = futures[future]
                print(f"Error triaging {ticket.id}: {e}")

    return results
