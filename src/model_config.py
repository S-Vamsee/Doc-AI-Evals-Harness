"""Read the extraction model's settings from the environment, provider-neutrally."""

from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse


DEFAULT_LABEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
_PLACEHOLDERS = {"", "your_key_here", "your-key-here"}


def _first(env, *names: str) -> str | None:
    for name in names:
        value = (env.get(name) or "").strip()
        if value:
            return value
    return None


def provider_for(base_url: str) -> str:
    host = (urlparse(base_url).hostname or "").casefold()
    if host == "openrouter.ai" or host.endswith(".openrouter.ai"):
        return "openrouter"
    if host == "api.deepseek.com":
        return "deepseek"
    if host.endswith(".azure.com"):
        return "azure"
    return "other"


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    api_key: str
    model: str
    label: str
    provider: str

    @property
    def host(self) -> str:
        return urlparse(self.base_url).hostname or ""


def public_model_label(env=None) -> str:
    """The name written into reports. Never a private deployment name."""
    env = os.environ if env is None else env
    label = _first(env, "HARNESS_MODEL_LABEL")
    if label:
        return label
    base_url = _first(env, "HARNESS_MODEL_BASE_URL", "DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    model = _first(env, "HARNESS_MODEL", "DEEPSEEK_MODEL")
    # Public catalogue names such as OpenRouter's are safe to show; other names may be private.
    return model if provider_for(base_url) == "openrouter" and model else DEFAULT_LABEL


def endpoint_summary(env=None) -> dict:
    """Provider and host for run records; needs no key and reveals no secret."""
    env = os.environ if env is None else env
    base_url = _first(env, "HARNESS_MODEL_BASE_URL", "DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    return {"provider": provider_for(base_url), "provider_host": urlparse(base_url).hostname}


def load_model_config(env=None) -> ModelConfig:
    """New ``HARNESS_MODEL_*`` names win; the older ``DEEPSEEK_*`` names still work."""
    env = os.environ if env is None else env
    base_url = _first(env, "HARNESS_MODEL_BASE_URL", "DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    api_key = _first(env, "HARNESS_MODEL_API_KEY", "DEEPSEEK_API_KEY")
    if not api_key or api_key in _PLACEHOLDERS:
        raise RuntimeError("No model key is set: add HARNESS_MODEL_API_KEY to the ignored .env file")
    provider = provider_for(base_url)
    model = _first(env, "HARNESS_MODEL", "DEEPSEEK_MODEL")
    if not model:
        if provider in {"openrouter", "other"}:
            raise RuntimeError("No model name is set: add HARNESS_MODEL to the ignored .env file")
        model = DEFAULT_LABEL
    return ModelConfig(base_url=base_url, api_key=api_key, model=model,
                       label=public_model_label(env), provider=provider)


def request_options(config: ModelConfig) -> dict:
    """Provider-specific options added to every chat request."""
    if config.provider == "openrouter":
        # Report real usage cost, only route to providers that honour JSON mode, and turn
        # off hidden reasoning, as the earlier DeepSeek runs did.
        return {"extra_body": {"usage": {"include": True},
                               "provider": {"require_parameters": True},
                               "reasoning": {"enabled": False}}}
    if config.provider == "deepseek":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    return {}


def usage_cost(usage) -> float | None:
    """The provider-reported cost in USD, when the provider sends one."""
    if usage is None:
        return None
    value = getattr(usage, "cost", None)
    if value is None:
        value = (getattr(usage, "model_extra", None) or {}).get("cost")
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
