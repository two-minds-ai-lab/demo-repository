import argparse
import json
import re

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
from bill_retrieval import search_bills


@tool
def get_bill_due_dates() -> str:
    """Get unpaid bills due soon or later this month and their totals."""
    return json.dumps(get_bill_due_dates_data())


@tool
def get_bill_change_analysis() -> str:
    """Get current and previous monthly totals plus unexpected bill changes."""
    return json.dumps(get_bill_change_analysis_data())


@tool
def search_bill_records(query: str) -> str:
    """Find bill records using exact, semantic, and hybrid retrieval."""
    return json.dumps(search_bills(query, mode="hybrid"))


bill_manager_agent = Agent(
    name="Bill Manager",
    instructions=(
        "You are a concise personal bill manager. Use the provided tools for all "
        "bill facts, dates, totals, and comparisons; never calculate or invent "
        "bill values yourself. Use get_bill_due_dates for due-date questions. "
        "Use get_bill_change_analysis for monthly totals and unusual changes. "
        "Use search_bill_records when the user asks to find, search, locate, "
        "or identify a bill, statement, amount, date, provider, or source. Pass "
        "the user's exact wording to search_bill_records, especially amounts "
        "and dates. "
        "Call both tools when the user asks for a complete bill summary. Clearly "
        "state the as-of date, format money as US dollars, and mention when a "
        "bill has no previous-month history."
    ),
    tools=[
        get_bill_due_dates,
        get_bill_change_analysis,
        search_bill_records,
    ],
)


def _phi4_tool_names(content):
    supported_tools = (
        "get_bill_due_dates",
        "get_bill_change_analysis",
        "search_bill_records",
    )
    return [name for name in supported_tools if name in content]


def _ensure_phi4_tool_coverage(question, tool_names):
    question = question.lower()
    selected = list(dict.fromkeys(tool_names))
    required = []

    if any(word in question for word in ("complete", "summary", "all bills")):
        required.extend(
            ("get_bill_due_dates", "get_bill_change_analysis")
        )
    if any(
        word in question
        for word in (
            "find",
            "identify",
            "locate",
            "record",
            "search",
            "source",
            "statement",
            "email",
            "document",
            "which bill",
            "what bill",
        )
    ) or re.search(r"\b\d+\.\d{2}\b|\b\d{4}-\d{2}-\d{2}\b", question):
        required.append("search_bill_records")
    if any(
        word in question
        for word in ("change", "comparison", "anomaly", "high", "low")
    ):
        required.append("get_bill_change_analysis")
    if any(
        word in question
        for word in ("due", "upcoming", "next week", "later this month")
    ):
        required.append("get_bill_due_dates")
    if required:
        return list(dict.fromkeys(required))
    if selected:
        return selected
    return ["get_bill_due_dates"]


def _limit_retrieval_results(question, results):
    """Apply explicit single-result language to retrieval display results."""
    question = (question or "").lower()
    top_result_requested = re.search(
        r"\b(rank|ranked)\s*1\b|\btop\s*(result|1)\b|"
        r"\bfirst\s+result\b|\bonly\s+for\b",
        question,
    )
    return results[:1] if top_result_requested else results


def _bill_summary_items():
    """Index calculated bill details by stable bill ID for cross-tool joins."""
    summary = build_bill_summary(load_bill_data("data/bills.json"))
    return {
        bill["bill_id"]: bill
        for bill in [
            *summary["upcoming_bills"],
            *summary["later_this_month"],
        ]
    }


def _format_phi4_tool_results(tool_names, tool_results, question=None):
    if set(tool_names) == {
        "get_bill_due_dates",
        "get_bill_change_analysis",
    }:
        return format_bill_summary(
            build_bill_summary(load_bill_data("data/bills.json"))
        )

    sections = []
    retrieval_results = tool_results.get("search_bill_records", [])
    displayed_results = _limit_retrieval_results(question, retrieval_results)
    # Follow-up tools must join on bill_id, never on model text or list position.
    matched_ids = {
        result["bill_id"] for result in retrieval_results[:1]
    }

    if "search_bill_records" in tool_names:
        lines = ["BILL SEARCH RESULTS", ""]
        if not displayed_results:
            lines.append("No matching bills found.")
        else:
            for index, result in enumerate(displayed_results, start=1):
                ranks = ", ".join(
                    f"{source} rank {rank}"
                    for source, rank in result.get("ranks", {}).items()
                )
                rank_text = f" ({ranks})" if ranks else ""
                lines.append(
                    f"{index}. {result['name']} [{result['category']}]"
                    f"{rank_text}"
                )
        sections.append("\n".join(lines))

    if "get_bill_due_dates" in tool_names:
        if "search_bill_records" in tool_names:
            # A retrieval follow-up answers only for rank 1, not every due bill.
            summary_items = _bill_summary_items()
            matched_bills = [
                summary_items[bill_id]
                for bill_id in matched_ids
                if bill_id in summary_items
            ]
            lines = ["MATCHED BILL DUE DETAILS", ""]
            if not matched_bills:
                lines.append("No matching bill due details found.")
            else:
                for bill in matched_bills:
                    lines.append(
                        f"- {bill['name']}: ${bill['amount_due']:.2f} "
                        f"due {bill['due_date']}"
                    )
                matched_total = sum(
                    bill["amount_due"] for bill in matched_bills
                )
                lines.append(f"Matched total due: ${matched_total:.2f}")
        else:
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
        sections.append("\n".join(lines))

    if "get_bill_change_analysis" in tool_names:
        if "search_bill_records" in tool_names:
            # Reuse the same stable-ID join for targeted change explanations.
            summary_items = _bill_summary_items()
            matched_bills = [
                summary_items[bill_id]
                for bill_id in matched_ids
                if bill_id in summary_items
            ]
            lines = ["MATCHED BILL CHANGES", ""]
            if not matched_bills:
                lines.append("No matching bill change details found.")
            else:
                for bill in matched_bills:
                    amount_change = bill["amount_change"]
                    percentage_change = bill["percentage_change"]
                    flag = bill["flag"].replace("_", " ").capitalize()
                    lines.extend(
                        [
                            bill["name"],
                            f"Current amount: ${bill['amount_due']:.2f}",
                        ]
                    )
                    if bill["previous_amount"] is None:
                        lines.extend(
                            [
                                "Previous amount: No history",
                                "Change: N/A",
                            ]
                        )
                    else:
                        amount_sign = "+" if amount_change >= 0 else "-"
                        percentage_sign = (
                            "+" if percentage_change >= 0 else "-"
                        )
                        lines.extend(
                            [
                                f"Previous amount: "
                                f"${bill['previous_amount']:.2f}",
                                f"Change: {amount_sign}"
                                f"${abs(amount_change):.2f} "
                                f"({percentage_sign}"
                                f"{abs(percentage_change):.1f}%)",
                            ]
                        )
                    lines.append(f"Flag: {flag}")
        else:
            change_data = tool_results["get_bill_change_analysis"]
            comparison = change_data["monthly_comparison"]
            anomalies = change_data["individual_anomalies"]
            difference = comparison["difference"]
            difference_sign = "+" if difference >= 0 else "-"
            lines = [
                f"MONTHLY COMPARISON AS OF {change_data['as_of_date']}",
                "",
                f"Current total: ${comparison['current_total']:.2f}",
                f"Previous total: ${comparison['previous_total']:.2f}",
                f"Difference: {difference_sign}${abs(difference):.2f} "
                f"({comparison['percentage_change']:+.1f}%)",
                "",
                "Unexpectedly high: "
                + ", ".join(anomalies["unexpectedly_high"]),
                "Unexpectedly low: "
                + ", ".join(anomalies["unexpectedly_low"]),
                "Within expected range: "
                + ", ".join(anomalies["within_expected_range"]),
            ]
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


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
                "name": "search_bill_records",
                "description": (
                    "Find bills by provider, description, amount, or due date "
                    "using BM25 and semantic retrieval."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's exact search wording.",
                        }
                    },
                    "required": ["query"],
                },
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
        # Coverage rules safely select only the read-only tools the intent needs.
        tool_names = []
    tool_names = _ensure_phi4_tool_coverage(question, tool_names)

    tool_results = {}
    for tool_name in tool_names:
        if tool_name == "get_bill_due_dates":
            tool_results[tool_name] = get_bill_due_dates_data()
        elif tool_name == "get_bill_change_analysis":
            tool_results[tool_name] = get_bill_change_analysis_data()
        elif tool_name == "search_bill_records":
            tool_results[tool_name] = search_bills(question, mode="hybrid")

    return _format_phi4_tool_results(
        tool_names,
        tool_results,
        question=question,
    )


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
