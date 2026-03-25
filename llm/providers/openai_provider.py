from __future__ import annotations

import os
import time
from typing import Type

from openai import OpenAI
from pydantic import BaseModel

from llm.providers.base import LLMProvider, LLMResponse

# Cost per 1M tokens (USD) for gpt-4o-mini
GPT4O_MINI_INPUT_COST = 0.150 / 1_000_000
GPT4O_MINI_OUTPUT_COST = 0.600 / 1_000_000


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * GPT4O_MINI_INPUT_COST
            + completion_tokens * GPT4O_MINI_OUTPUT_COST
        )

    def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        start = time.monotonic()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
        )
        latency_ms = (time.monotonic() - start) * 1000
        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content,
            provider="openai",
            model=self.model,
            latency_ms=latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            estimated_cost_usd=self._cost(usage.prompt_tokens, usage.completion_tokens),
        )

    def complete_structured(
        self,
        system: str,
        user: str,
        schema: Type[BaseModel],
        temperature: float = 0.1,
    ) -> tuple[BaseModel, LLMResponse]:
        start = time.monotonic()
        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format=schema,
            temperature=temperature,
        )
        latency_ms = (time.monotonic() - start) * 1000
        usage = response.usage
        parsed = response.choices[0].message.parsed
        resp = LLMResponse(
            content=response.choices[0].message.content or "",
            provider="openai",
            model=self.model,
            latency_ms=latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            estimated_cost_usd=self._cost(usage.prompt_tokens, usage.completion_tokens),
        )
        return parsed, resp
