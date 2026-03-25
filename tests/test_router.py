import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from llm.router import LLMRouter


def test_router_returns_ollama_when_use_local_true():
    with patch.dict(os.environ, {"USE_LOCAL_LLM": "true"}):
        from llm.providers.ollama_provider import OllamaProvider
        router = LLMRouter()
        provider = router.get_provider()
        assert isinstance(provider, OllamaProvider)


def test_router_returns_openai_when_use_local_false_no_anthropic():
    with patch.dict(os.environ, {"USE_LOCAL_LLM": "false", "OPENAI_API_KEY": "sk-test"}, clear=False):
        # Remove anthropic key to force openai path
        env = {**os.environ, "USE_LOCAL_LLM": "false", "OPENAI_API_KEY": "sk-test"}
        env.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            from llm.providers.openai_provider import OpenAIProvider
            router = LLMRouter()
            provider = router.get_provider(quality_required=False)
            assert isinstance(provider, OpenAIProvider)


def test_router_returns_claude_for_quality_with_anthropic_key():
    env = {
        "USE_LOCAL_LLM": "false",
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "OPENAI_API_KEY": "sk-test",
    }
    with patch.dict(os.environ, env, clear=True):
        from llm.providers.claude_provider import ClaudeProvider
        router = LLMRouter()
        provider = router.get_provider(quality_required=True)
        assert isinstance(provider, ClaudeProvider)


def test_router_get_provider_by_name_local():
    from llm.providers.ollama_provider import OllamaProvider
    router = LLMRouter()
    provider = router.get_provider_by_name("local")
    assert isinstance(provider, OllamaProvider)


def test_router_get_provider_by_name_openai():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        from llm.providers.openai_provider import OpenAIProvider
        router = LLMRouter()
        provider = router.get_provider_by_name("openai")
        assert isinstance(provider, OpenAIProvider)


def test_router_get_provider_by_name_claude():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        from llm.providers.claude_provider import ClaudeProvider
        router = LLMRouter()
        provider = router.get_provider_by_name("claude")
        assert isinstance(provider, ClaudeProvider)


def test_router_unknown_provider_raises():
    router = LLMRouter()
    with pytest.raises(ValueError, match="Unknown provider"):
        router.get_provider_by_name("grok")
