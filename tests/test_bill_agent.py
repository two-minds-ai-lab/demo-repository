import pytest
from agents import OpenAIChatCompletionsModel, OpenAIResponsesModel

from bill_agent import (
    _ensure_phi4_tool_coverage,
    _format_phi4_tool_results,
    _phi4_tool_names,
    _limit_retrieval_results,
    bill_manager_agent,
)
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


def test_bill_manager_has_exactly_three_tools():
    assert len(bill_manager_agent.tools) == 3
    assert {tool.name for tool in bill_manager_agent.tools} == {
        "get_bill_due_dates",
        "get_bill_change_analysis",
        "search_bill_records",
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


def test_phi4_text_tool_calls_are_recognized():
    content = (
        '[{"type":"function","function":{"name":"get_bill_due_dates"}},'
        '{"type":"function","function":'
        '{"name":"get_bill_change_analysis"}},'
        '{"type":"function","function":{"name":"search_bill_records"}}]'
    )

    assert _phi4_tool_names(content) == [
        "get_bill_due_dates",
        "get_bill_change_analysis",
        "search_bill_records",
    ]


def test_phi4_non_tool_text_has_no_recognized_tool_calls():
    assert _phi4_tool_names("Please provide your account details.") == []


def test_phi4_complete_summary_uses_deterministic_formatter():
    due_data = get_bill_due_dates_data()
    change_data = get_bill_change_analysis_data()

    report = _format_phi4_tool_results(
        ["get_bill_due_dates", "get_bill_change_analysis"],
        {
            "get_bill_due_dates": due_data,
            "get_bill_change_analysis": change_data,
        },
    )

    assert "As of: August 4, 2026" in report
    assert "Total due in the next 7 days: $507.90" in report
    assert "Current-month total: $762.90" in report


def test_phi4_complete_summary_always_uses_both_tools():
    assert _ensure_phi4_tool_coverage(
        "Give me a complete bill summary.",
        ["get_bill_due_dates"],
    ) == [
        "get_bill_due_dates",
        "get_bill_change_analysis",
    ]


def test_phi4_search_question_always_uses_retrieval():
    assert _ensure_phi4_tool_coverage(
        "Find my power bill.",
        [],
    ) == ["search_bill_records"]


def test_phi4_retrieval_intent_suppresses_unrelated_selected_tools():
    assert _ensure_phi4_tool_coverage(
        "Which bill is the power bill?",
        [
            "search_bill_records",
            "get_bill_due_dates",
            "get_bill_change_analysis",
        ],
    ) == ["search_bill_records"]


def test_phi4_exact_amount_question_uses_retrieval():
    assert _ensure_phi4_tool_coverage(
        "Which bill is 142.50?",
        [],
    ) == ["search_bill_records"]


def test_phi4_compound_search_and_change_uses_both_tools():
    assert _ensure_phi4_tool_coverage(
        "Find my power bill and tell me whether it changed.",
        ["search_bill_records"],
    ) == [
        "search_bill_records",
        "get_bill_change_analysis",
    ]


def test_phi4_retrieval_results_use_deterministic_formatter():
    report = _format_phi4_tool_results(
        ["search_bill_records"],
        {
            "search_bill_records": [
                {
                    "bill_id": "pse_electricity",
                    "name": "PSE Electricity",
                    "category": "utilities",
                    "score": 0.03,
                    "ranks": {"bm25": 1, "semantic": 1},
                    "evidence": "PSE Electricity",
                }
            ]
        },
    )

    assert "1. PSE Electricity [utilities]" in report
    assert "bm25 rank 1" in report


def test_rank_one_request_limits_displayed_retrieval_results():
    results = [
        {"bill_id": "pse_electricity"},
        {"bill_id": "xfinity_broadband"},
    ]

    assert _limit_retrieval_results(
        "Show only the bill ranked 1.",
        results,
    ) == [results[0]]


def test_retrieval_due_question_joins_only_top_match():
    report = _format_phi4_tool_results(
        ["search_bill_records", "get_bill_due_dates"],
        {
            "search_bill_records": [
                {
                    "bill_id": "pse_electricity",
                    "name": "PSE Electricity",
                    "category": "utilities",
                    "score": 0.03,
                    "ranks": {"bm25": 1, "semantic": 1},
                    "evidence": "PSE Electricity",
                },
                {
                    "bill_id": "xfinity_broadband",
                    "name": "Xfinity Broadband",
                    "category": "broadband",
                    "score": 0.02,
                    "ranks": {"semantic": 2},
                    "evidence": "Xfinity Broadband",
                },
            ],
            "get_bill_due_dates": get_bill_due_dates_data(),
        },
        question=(
            "Which bill is power bill and how much is due only for "
            "power bill ranked 1?"
        ),
    )

    assert "1. PSE Electricity [utilities]" in report
    assert "2. Xfinity Broadband" not in report
    assert "Matched total due: $142.50" in report
    assert "Chase Visa: $325.40" not in report


def test_retrieval_follow_up_joins_by_bill_id_not_display_name():
    report = _format_phi4_tool_results(
        ["search_bill_records", "get_bill_due_dates"],
        {
            "search_bill_records": [
                {
                    "bill_id": "pse_electricity",
                    "name": "Model-generated display text",
                    "category": "utilities",
                    "score": 0.03,
                    "ranks": {"semantic": 1},
                    "evidence": "PSE Electricity",
                }
            ],
            "get_bill_due_dates": get_bill_due_dates_data(),
        },
        question="Find the power bill and tell me what is due.",
    )

    assert "PSE Electricity: $142.50" in report


def test_no_retrieval_match_does_not_leak_unrelated_due_bills():
    report = _format_phi4_tool_results(
        ["search_bill_records", "get_bill_due_dates"],
        {
            "search_bill_records": [],
            "get_bill_due_dates": get_bill_due_dates_data(),
        },
        question="Which bill is $142.40?",
    )

    assert "No matching bills found." in report
    assert "No matching bill due details found." in report
    assert "Chase Visa" not in report
    assert "PSE Electricity: $142.50" not in report


def test_retrieval_change_question_joins_only_top_match():
    report = _format_phi4_tool_results(
        ["search_bill_records", "get_bill_change_analysis"],
        {
            "search_bill_records": [
                {
                    "bill_id": "pse_electricity",
                    "name": "PSE Electricity",
                    "category": "utilities",
                    "score": 0.03,
                    "ranks": {"semantic": 1},
                    "evidence": "PSE Electricity",
                }
            ],
            "get_bill_change_analysis": get_bill_change_analysis_data(),
        },
        question="Find my power bill and tell me whether it changed.",
    )

    assert "MATCHED BILL CHANGES" in report
    assert "Current amount: $142.50" in report
    assert "Change: +$47.50 (+50.0%)" in report
    assert "Chase Visa" not in report


def test_phi4_change_formatter_places_sign_before_currency_symbol():
    report = _format_phi4_tool_results(
        ["get_bill_change_analysis"],
        {"get_bill_change_analysis": get_bill_change_analysis_data()},
    )

    assert "Difference: +$29.40 (+4.0%)" in report
