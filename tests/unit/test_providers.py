import sys
from types import ModuleType, SimpleNamespace

import pytest

from src.providers.base import (
    AIResponse,
    InvalidRequestError,
    ProviderError,
    RateLimitError,
    TransientProviderError,
)
from src.providers.failover import FailoverPolicy
from src.providers.gemini import GeminiProvider
from src.providers.groq import GroqProvider
from src.providers.manager import ProviderManager
from src.providers.mock import MockProvider


class FailingProvider:
    name = "failing"

    async def generate(self, prompt, context=None):
        raise TransientProviderError("temporary")

    async def health_check(self):
        return False


class RateProvider:
    name = "rate"

    async def generate(self, prompt, context=None):
        raise RateLimitError("429")

    async def health_check(self):
        return False


@pytest.mark.asyncio
async def test_mock_provider():
    response = await MockProvider().generate("مرحبا")
    assert response.provider == "mock"
    assert "مرحبا" in response.text


@pytest.mark.asyncio
async def test_gemini_style_mock_response():
    response = await MockProvider("رد Gemini التجريبي").generate("اختبار")
    assert "Gemini" in response.text


@pytest.mark.asyncio
async def test_groq_style_mock_response():
    response = await MockProvider("رد Groq التجريبي").generate("اختبار")
    assert "Groq" in response.text


@pytest.mark.asyncio
async def test_gemini_adapter_uses_async_client(monkeypatch):
    class Models:
        async def generate_content(self, **kwargs):
            assert kwargs["model"] == "test-model"
            return SimpleNamespace(text="رد Gemini")

    client = SimpleNamespace(aio=SimpleNamespace(models=Models()))
    google_module = ModuleType("google")
    google_module.genai = SimpleNamespace(Client=lambda **kwargs: client)
    monkeypatch.setitem(sys.modules, "google", google_module)

    response = await GeminiProvider("test-key", model="test-model").generate("سؤال")

    assert response.provider == "gemini"
    assert response.text == "رد Gemini"


@pytest.mark.asyncio
async def test_groq_adapter_uses_async_client(monkeypatch):
    class Completions:
        async def create(self, **kwargs):
            assert kwargs["model"] == "test-model"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="رد Groq"))]
            )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=Completions()),
        close=lambda: None,
    )
    groq_module = ModuleType("groq")
    groq_module.AsyncGroq = lambda **kwargs: client
    monkeypatch.setitem(sys.modules, "groq", groq_module)

    response = await GroqProvider("test-key", model="test-model").generate("سؤال")

    assert response.provider == "groq"
    assert response.text == "رد Groq"


@pytest.mark.asyncio
async def test_empty_groq_response_triggers_fallback(monkeypatch):
    class Completions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
            )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=Completions()),
        close=lambda: None,
    )
    groq_module = ModuleType("groq")
    groq_module.AsyncGroq = lambda **kwargs: client
    monkeypatch.setitem(sys.modules, "groq", groq_module)

    manager = ProviderManager(
        [GroqProvider("test-key"), MockProvider("الاحتياطي")],
        FailoverPolicy(max_retries=0),
    )

    response = await manager.generate("سؤال")

    assert response.provider == "mock"


@pytest.mark.asyncio
async def test_primary_success():
    manager = ProviderManager([MockProvider("نجح"), FailingProvider()], FailoverPolicy(max_retries=0))
    response = await manager.generate("سؤال")
    assert response.provider == "mock"


@pytest.mark.asyncio
async def test_automatic_fallback():
    manager = ProviderManager([FailingProvider(), MockProvider("الاحتياطي")], FailoverPolicy(max_retries=0))
    response = await manager.generate("سؤال")
    assert response.provider == "mock"
    assert "الاحتياطي" in response.text


@pytest.mark.asyncio
async def test_fallback_is_sequential_and_updates_active_provider():
    calls = []

    class OrderedProvider:
        def __init__(self, name, fails):
            self.name = name
            self.fails = fails

        async def generate(self, prompt, context=None):
            calls.append(self.name)
            if self.fails:
                raise TransientProviderError("temporary")
            return AIResponse(self.name, self.name, "test-model")

        async def health_check(self):
            return True

    manager = ProviderManager(
        [OrderedProvider("gemini", True), OrderedProvider("groq", False)],
        FailoverPolicy(max_retries=0),
    )
    response = await manager.generate("سؤال")
    assert calls == ["gemini", "groq"]
    assert response.provider == "groq"
    assert manager.active_provider == "groq"


@pytest.mark.asyncio
async def test_retry_limit():
    manager = ProviderManager([FailingProvider(), FailingProvider()], FailoverPolicy(max_retries=1))
    with pytest.raises(ProviderError, match="تعذر الحصول على رد"):
        await manager.generate("سؤال")


@pytest.mark.asyncio
async def test_provider_timeout_falls_back():
    class SlowProvider:
        name = "slow"

        async def generate(self, prompt, context=None):
            import asyncio

            await asyncio.sleep(0.1)

        async def health_check(self):
            return True

    manager = ProviderManager(
        [SlowProvider(), MockProvider("بعد المهلة")],
        FailoverPolicy(max_retries=0),
        timeout_seconds=0.01,
    )
    response = await manager.generate("سؤال")
    assert response.provider == "mock"


@pytest.mark.asyncio
async def test_rate_limit_fallback():
    manager = ProviderManager([RateProvider(), MockProvider("بعد الحد")], FailoverPolicy(max_retries=0))
    response = await manager.generate("سؤال")
    assert response.provider == "mock"


@pytest.mark.asyncio
async def test_invalid_request_no_retry():
    class InvalidProvider:
        name = "invalid"

        async def generate(self, prompt, context=None):
            raise InvalidRequestError("bad")

        async def health_check(self):
            return False

    manager = ProviderManager([InvalidProvider(), MockProvider()], FailoverPolicy(max_retries=3))
    with pytest.raises(InvalidRequestError):
        await manager.generate("")

