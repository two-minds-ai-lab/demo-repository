import pytest
from agents import OpenAIChatCompletionsModel, OpenAIResponsesModel

from bill_agent import bill_manager_agent
from bill_agent_provider import (
    ProviderConfigurationError,
    create_bill_agent_runtime,
)
from bill_agent_tools import (
    get_bill_change_analysis_data,
    get_bill_due_dates_data,
)


def test_due_dates_tool_returns_upcoming_and_later_totals():
    result = get_bill_due_dates_data()

    assert [bill["name"] for bill in result["due_in_lookahead_window"]] == [
        "Chase Visa",
        "PSE Electricity",
        "Citi Mastercard",
    ]
    assert result["total_due_in_lookahead_window"] == pytest.approx(507.90)
    assert result["total_due_later_this_month"] == pytest.approx(255.0)


def test_change_analysis_tool_returns_totals_and_anomalies():
    result = get_bill_change_analysis_data()

    comparison = result["monthly_comparison"]
    assert comparison["current_total"] == pytest.approx(762.90)
    assert comparison["previous_total"] == pytest.approx(733.50)
    assert comparison["percentage_change"] == pytest.approx(4.0, abs=0.05)
    assert result["individual_anomalies"]["unexpectedly_high"] == [
        "Chase Visa",
        "PSE Electricity",
    ]


def test_bill_manager_has_exactly_two_tools():
    assert len(bill_manager_agent.tools) == 2
    assert {tool.name for tool in bill_manager_agent.tools} == {
        "get_bill_due_dates",
        "get_bill_change_analysis",
    }


def test_openai_provider_uses_responses_model():
    runtime = create_bill_agent_runtime(
        environ={
            "BILL_AGENT_PROVIDER": "openai",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "test-openai-model",
        }
    )

    assert runtime.provider == "openai"
    assert runtime.model_name == "test-openai-model"
    assert isinstance(runtime.model, OpenAIResponsesModel)
    assert runtime.tracing_disabled is False


def test_azure_provider_supports_responses_api():
    runtime = create_bill_agent_runtime(
        environ={
            "BILL_AGENT_PROVIDER": "azure",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "test-deployment",
        }
    )

    assert runtime.provider == "azure"
    assert runtime.model_name == "test-deployment"
    assert isinstance(runtime.model, OpenAIResponsesModel)
    assert runtime.tracing_disabled is True


def test_azure_provider_supports_chat_completions_api():
    runtime = create_bill_agent_runtime(
        environ={
            "BILL_AGENT_PROVIDER": "azure",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "test-deployment",
            "AZURE_OPENAI_API": "chat_completions",
        }
    )

    assert isinstance(runtime.model, OpenAIChatCompletionsModel)


def test_phi4_provider_uses_local_chat_completions():
    runtime = create_bill_agent_runtime(
        environ={
            "BILL_AGENT_PROVIDER": "phi4",
            "PHI4_MODEL": "phi4-mini",
        }
    )

    assert runtime.provider == "phi4"
    assert runtime.model_name == "phi4-mini"
    assert isinstance(runtime.model, OpenAIChatCompletionsModel)
    assert runtime.tracing_disabled is True


def test_provider_reports_missing_required_configuration():
    with pytest.raises(
        ProviderConfigurationError,
        match="AZURE_OPENAI_API_KEY is required",
    ):
        create_bill_agent_runtime(
            environ={"BILL_AGENT_PROVIDER": "azure"}
        )
