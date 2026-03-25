from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        """Return a plain-text completion."""

    @abstractmethod
    def complete_structured(
        self,
        system: str,
        user: str,
        schema: Type[BaseModel],
        temperature: float = 0.1,
    ) -> tuple[BaseModel, LLMResponse]:
        """Return a Pydantic model instance parsed from structured output."""

    @staticmethod
    def _timed(fn):
        """Helper: time a call and return (result, latency_ms)."""
        start = time.monotonic()
        result = fn()
        latency_ms = (time.monotonic() - start) * 1000
        return result, latency_ms
