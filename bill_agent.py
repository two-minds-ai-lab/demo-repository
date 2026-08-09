import argparse
import json

from agents import Agent, RunConfig, Runner
from agents.decorators import tool

from bill_agent_provider import (
    SUPPORTED_PROVIDERS,
    ProviderConfigurationError,
    create_bill_agent_runtime,
)
from bill_agent_tools import (
    get_bill_change_analysis_data,
    get_bill_due_dates_data,
)


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


def run_bill_manager(question, provider=None):
    """Run the Bill Manager agent for one user question."""
    runtime = create_bill_agent_runtime(provider=provider)
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
