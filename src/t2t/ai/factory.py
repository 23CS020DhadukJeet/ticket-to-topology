"""Factory for creating LLMProvider instances from settings."""

from t2t.ai.providers import (
    GeminiProvider,
    LLMProvider,
    NoneProvider,
    OllamaProvider,
    OpenAIProvider,
)
from t2t.clock import Clock
from t2t.config import Settings, load_settings
from t2t.errors import T2TError


def get_provider(
    settings: Settings | None = None,
    clock: Clock | None = None,
) -> LLMProvider:
    """Return configured LLMProvider based on environment settings.

    Supported values of T2T_AI_PROVIDER:
    - 'none' -> NoneProvider
    - 'ollama' -> OllamaProvider
    - 'gemini' -> GeminiProvider
    - 'openai' -> OpenAIProvider
    """
    cfg = settings or load_settings()
    provider_name = cfg.t2t_ai_provider.strip().lower()

    if provider_name == "none" or not provider_name:
        return NoneProvider()

    if provider_name == "ollama":
        return OllamaProvider(
            host=cfg.ollama_host,
            model=cfg.ollama_model,
            clock=clock,
            timeout=float(cfg.t2t_ai_timeout),
        )

    if provider_name == "gemini":
        key = cfg.gemini_api_key.get_secret_value()
        return GeminiProvider(
            api_key=key,
            model=cfg.gemini_model,
            clock=clock,
            timeout=float(cfg.t2t_ai_timeout),
        )

    if provider_name == "openai":
        key = cfg.openai_api_key.get_secret_value()
        return OpenAIProvider(
            api_key=key,
            model=cfg.openai_model,
            clock=clock,
            timeout=float(cfg.t2t_ai_timeout),
        )

    raise T2TError(f"Unknown AI provider: '{cfg.t2t_ai_provider}'")
