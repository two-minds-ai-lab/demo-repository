import argparse
import json

from agents import Agent, RunConfig, Runner
from agents.decorators import tool
from openai import OpenAI

from bill_agent_provider import (
    SUPPORTED_PROVIDERS,
    ProviderConfigurationError,
    create_bill_agent_runtime,
)
from bill_agent_tools import (
    get_bill_change_analysis_data,
    get_bill_due_dates_data,
)
from bill_analysis import build_bill_summary, format_bill_summary, load_bill_data


@tool
def get_bill_due_dates() -> str:
    """Get unpaid bills due soon or later this month and their totals."""
    return json.dumps(get_bill_due_dates_data())


@tool
def get_bill_change_analysis() -> str:
    """Get current and previous monthly totals plus unexpected bill changes."""
    return json.dumps(get_bill_change_analysis_data())


bill_manager_agent = Agent(
    name="Bill Manager",
    instructions=(
        "You are a concise personal bill manager. Use the provided tools for all "
        "bill facts, dates, totals, and comparisons; never calculate or invent "
        "bill values yourself. Use get_bill_due_dates for due-date questions. "
        "Use get_bill_change_analysis for monthly totals and unusual changes. "
        "Call both tools when the user asks for a complete bill summary. Clearly "
        "state the as-of date, format money as US dollars, and mention when a "
        "bill has no previous-month history."
    ),
    tools=[get_bill_due_dates, get_bill_change_analysis],
)


def _phi4_tool_names(content):
    supported_tools = (
        "get_bill_due_dates",
        "get_bill_change_analysis",
    )
    return [name for name in supported_tools if name in content]


def _ensure_phi4_tool_coverage(question, tool_names):
    question = question.lower()
    selected = list(tool_names)

    if any(word in question for word in ("complete", "summary", "all bills")):
        required = (
            "get_bill_due_dates",
            "get_bill_change_analysis",
        )
    elif any(
        word in question
        for word in ("change", "comparison", "anomaly", "high", "low")
    ):
        required = ("get_bill_change_analysis",)
    else:
        required = ("get_bill_due_dates",)

    for tool_name in required:
        if tool_name not in selected:
            selected.append(tool_name)
    return selected


def _format_phi4_tool_results(tool_names, tool_results):
    if set(tool_names) == {
        "get_bill_due_dates",
        "get_bill_change_analysis",
    }:
        return format_bill_summary(
            build_bill_summary(load_bill_data("data/bills.json"))
        )

    if "get_bill_due_dates" in tool_names:
        due_data = tool_results["get_bill_due_dates"]
        lines = [
            f"BILLS DUE AS OF {due_data['as_of_date']}",
            "",
            f"Due in the next {due_data['lookahead_days']} days:",
        ]
        for bill in due_data["due_in_lookahead_window"]:
            lines.append(
                f"- {bill['name']}: ${bill['amount_due']:.2f} "
                f"due {bill['due_date']}"
            )
        lines.append(
            "Total due: "
            f"${due_data['total_due_in_lookahead_window']:.2f}"
        )
        return "\n".join(lines)

    change_data = tool_results["get_bill_change_analysis"]
    comparison = change_data["monthly_comparison"]
    anomalies = change_data["individual_anomalies"]
    return "\n".join(
        [
            f"MONTHLY COMPARISON AS OF {change_data['as_of_date']}",
            "",
            f"Current total: ${comparison['current_total']:.2f}",
            f"Previous total: ${comparison['previous_total']:.2f}",
            f"Difference: ${comparison['difference']:+.2f} "
            f"({comparison['percentage_change']:+.1f}%)",
            "",
            "Unexpectedly high: "
            + ", ".join(anomalies["unexpectedly_high"]),
            "Unexpectedly low: "
            + ", ".join(anomalies["unexpectedly_low"]),
            "Within expected range: "
            + ", ".join(anomalies["within_expected_range"]),
        ]
    )


def _run_phi4_bill_manager(question, runtime):
    client = OpenAI(
        api_key=runtime.api_key,
        base_url=runtime.base_url,
    )
    instructions = bill_manager_agent.instructions
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_bill_due_dates",
                "description": (
                    "Get unpaid bills due soon or later this month and totals."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_bill_change_analysis",
                "description": (
                    "Get monthly totals and unexpected bill changes."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": question},
    ]
    response = client.chat.completions.create(
        model=runtime.model_name,
        messages=messages,
        tools=tools,
    )
    assistant_message = response.choices[0].message

    tool_names = [
        call.function.name for call in (assistant_message.tool_calls or [])
    ]
    if not tool_names:
        tool_names = _phi4_tool_names(assistant_message.content or "")
    if not tool_names:
        # Some Ollama Phi-4 Mini builds occasionally omit tool-call metadata.
        # Both tools are read-only, so use both to keep the answer grounded.
        tool_names = [
            "get_bill_due_dates",
            "get_bill_change_analysis",
        ]
    tool_names = _ensure_phi4_tool_coverage(question, tool_names)

    tool_results = {}
    for tool_name in tool_names:
        if tool_name == "get_bill_due_dates":
            tool_results[tool_name] = get_bill_due_dates_data()
        elif tool_name == "get_bill_change_analysis":
            tool_results[tool_name] = get_bill_change_analysis_data()

    return _format_phi4_tool_results(tool_names, tool_results)


def run_bill_manager(question, provider=None):
    """Run the Bill Manager agent for one user question."""
    runtime = create_bill_agent_runtime(provider=provider)
    if runtime.provider == "phi4":
        return _run_phi4_bill_manager(question, runtime)

    result = Runner.run_sync(
        bill_manager_agent,
        question,
        run_config=RunConfig(
            model=runtime.model,
            tracing_disabled=runtime.tracing_disabled,
            workflow_name=f"Bill Manager ({runtime.provider})",
        ),
    )
    return result.final_output


def main():
    parser = argparse.ArgumentParser(
        description="Ask the Bill Manager agent about recurring bills."
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Question for the Bill Manager agent.",
    )
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        help=(
            "Model provider. Defaults to BILL_AGENT_PROVIDER or 'openai'."
        ),
    )
    args = parser.parse_args()

    question = " ".join(args.question) or "Give me a complete bill summary."
    try:
        print(run_bill_manager(question, provider=args.provider))
    except ProviderConfigurationError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
