import os
from dataclasses import dataclass

from agents import OpenAIChatCompletionsModel, OpenAIResponsesModel
from openai import AsyncOpenAI


SUPPORTED_PROVIDERS = ("openai", "azure", "phi4")


class ProviderConfigurationError(ValueError):
    """Raised when a bill agent provider is not configured correctly."""


@dataclass(frozen=True)
class BillAgentRuntime:
    provider: str
    model_name: str
    model: object
    tracing_disabled: bool


def _required(environ, name, provider):
    value = environ.get(name)
    if not value:
        raise ProviderConfigurationError(
            f"{name} is required when BILL_AGENT_PROVIDER={provider}."
        )
    return value


def _azure_base_url(endpoint):
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/openai/v1"):
        return f"{endpoint}/"
    return f"{endpoint}/openai/v1/"


def create_bill_agent_runtime(provider=None, environ=None):
    """Create the model runtime selected by environment configuration."""
    environ = os.environ if environ is None else environ
    provider = (provider or environ.get("BILL_AGENT_PROVIDER", "openai")).lower()

    if provider not in SUPPORTED_PROVIDERS:
        supported = ", ".join(SUPPORTED_PROVIDERS)
        raise ProviderConfigurationError(
            f"Unsupported provider '{provider}'. Choose one of: {supported}."
        )

    if provider == "openai":
        api_key = _required(environ, "OPENAI_API_KEY", provider)
        model_name = environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        client = AsyncOpenAI(api_key=api_key)
        model = OpenAIResponsesModel(
            model=model_name,
            openai_client=client,
        )
        return BillAgentRuntime(
            provider=provider,
            model_name=model_name,
            model=model,
            tracing_disabled=False,
        )

    if provider == "azure":
        api_key = _required(environ, "AZURE_OPENAI_API_KEY", provider)
        endpoint = _required(environ, "AZURE_OPENAI_ENDPOINT", provider)
        model_name = _required(environ, "AZURE_OPENAI_DEPLOYMENT", provider)
        api_type = environ.get("AZURE_OPENAI_API", "responses").lower()
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=_azure_base_url(endpoint),
        )

        if api_type == "responses":
            model = OpenAIResponsesModel(
                model=model_name,
                openai_client=client,
            )
        elif api_type == "chat_completions":
            model = OpenAIChatCompletionsModel(
                model=model_name,
                openai_client=client,
            )
        else:
            raise ProviderConfigurationError(
                "AZURE_OPENAI_API must be 'responses' or 'chat_completions'."
            )

        return BillAgentRuntime(
            provider=provider,
            model_name=model_name,
            model=model,
            tracing_disabled=True,
        )

    model_name = environ.get("PHI4_MODEL", "phi4-mini")
    base_url = environ.get("PHI4_BASE_URL", "http://localhost:11434/v1")
    api_key = environ.get("PHI4_API_KEY", "ollama")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=client,
    )
    return BillAgentRuntime(
        provider=provider,
        model_name=model_name,
        model=model,
        tracing_disabled=True,
    )
