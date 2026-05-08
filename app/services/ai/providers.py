"""AI model providers using OpenAI-compatible API.

All three providers (OpenAI, DeepSeek, Gemini) use the openai SDK
with different base URLs and API keys.
"""

import json
import os
from dataclasses import dataclass

import structlog
from openai import AsyncOpenAI

from app.utils.rate_limiter import rate_limiters

logger = structlog.get_logger()


@dataclass
class AIResponse:
    """Standardized response from any AI provider."""

    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    structured_data: dict | None = None

    @property
    def cost_usd(self) -> float:
        """Estimate cost based on provider pricing."""
        pricing = {
            "deepseek": {"input": 0.14, "output": 0.28},
            "gemini": {"input": 0.075, "output": 0.30},
            "openai": {"input": 0.15, "output": 0.60},
        }
        rates = pricing.get(self.provider, {"input": 0.15, "output": 0.60})
        return (
            self.prompt_tokens * rates["input"] / 1_000_000
            + self.completion_tokens * rates["output"] / 1_000_000
        )


class BaseAIProvider:
    """Base class for AI providers using OpenAI-compatible API."""

    provider_name: str = "base"
    rate_limit_name: str = "openai"

    def __init__(self, api_key: str, base_url: str, default_model: str):
        self.api_key = api_key
        self.default_model = default_model
        self._client: AsyncOpenAI | None = None
        self._base_url = base_url

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self._base_url,
            )
        return self._client

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> AIResponse | None:
        """Send a chat completion request."""
        if not self.is_configured():
            logger.warning("ai.provider_not_configured", provider=self.provider_name)
            return None

        await rate_limiters.wait_and_acquire(self.rate_limit_name)

        try:
            client = self._get_client()
            kwargs: dict = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""
            usage = response.usage

            structured = None
            if response_format and response_format.get("type") == "json_object":
                try:
                    structured = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("ai.json_parse_failed", provider=self.provider_name)

            return AIResponse(
                content=content,
                model=response.model,
                provider=self.provider_name,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                structured_data=structured,
            )

        except Exception as e:
            logger.error(
                "ai.chat_failed",
                provider=self.provider_name,
                error=str(e),
            )
            return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek AI provider — best cost/performance ratio for code and analysis."""

    provider_name = "deepseek"
    rate_limit_name = "deepseek"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        super().__init__(
            api_key=key or "",
            base_url="https://api.deepseek.com",
            default_model="deepseek-chat",
        )


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider — good for long context analysis."""

    provider_name = "gemini"
    rate_limit_name = "gemini"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        super().__init__(
            api_key=key or "",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            default_model="gemini-2.0-flash",
        )


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider — GPT-4o-mini for cost-effective analysis."""

    provider_name = "openai"
    rate_limit_name = "openai"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        super().__init__(
            api_key=key or "",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4o-mini",
        )


def get_available_providers() -> list[BaseAIProvider]:
    """Return list of configured AI providers, ordered by priority."""
    providers = [
        DeepSeekProvider(),
        GeminiProvider(),
        OpenAIProvider(),
    ]
    return [p for p in providers if p.is_configured()]


def get_best_provider() -> BaseAIProvider | None:
    """Return the best available AI provider (DeepSeek > Gemini > OpenAI)."""
    available = get_available_providers()
    return available[0] if available else None
