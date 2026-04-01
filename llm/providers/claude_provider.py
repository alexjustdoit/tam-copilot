from __future__ import annotations

import json
import os
import time
from typing import Type

import anthropic
from pydantic import BaseModel

from llm.providers.base import LLMProvider, LLMResponse

# Claude Haiku 4.5 cost per 1M tokens
HAIKU_INPUT_COST = 0.80 / 1_000_000
HAIKU_OUTPUT_COST = 4.00 / 1_000_000


class ClaudeProvider(LLMProvider):
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.model = model
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _cost(self, input_tokens: int, output_tokens: int) -> float:
        return input_tokens * HAIKU_INPUT_COST + output_tokens * HAIKU_OUTPUT_COST

    def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        start = time.monotonic()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
        )
        latency_ms = (time.monotonic() - start) * 1000
        content = response.content[0].text
        return LLMResponse(
            content=content,
            provider="claude",
            model=self.model,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            estimated_cost_usd=self._cost(
                response.usage.input_tokens, response.usage.output_tokens
            ),
        )

    def complete_structured(
        self,
        system: str,
        user: str,
        schema: Type[BaseModel],
        temperature: float = 0.1,
    ) -> tuple[BaseModel, LLMResponse]:
        tool_def = {
            "name": "structured_output",
            "description": "Output the structured result.",
            "input_schema": schema.model_json_schema(),
        }
        start = time.monotonic()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool_def],
            tool_choice={"type": "tool", "name": "structured_output"},
            temperature=temperature,
        )
        latency_ms = (time.monotonic() - start) * 1000

        tool_block = next(b for b in response.content if b.type == "tool_use")
        parsed = schema.model_validate(tool_block.input)
        content = json.dumps(tool_block.input)

        resp = LLMResponse(
            content=content,
            provider="claude",
            model=self.model,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            estimated_cost_usd=self._cost(
                response.usage.input_tokens, response.usage.output_tokens
            ),
        )
        return parsed, resp
