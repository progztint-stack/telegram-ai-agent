import pytest

from src.providers.base import InvalidRequestError, RateLimitError, TransientProviderError
from src.providers.failover import FailoverPolicy
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
async def test_retry_limit():
    manager = ProviderManager([FailingProvider(), FailingProvider()], FailoverPolicy(max_retries=1))
    with pytest.raises(TransientProviderError):
        await manager.generate("سؤال")


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

