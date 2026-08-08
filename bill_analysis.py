import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path


DEFAULT_DATA_FILE = Path(__file__).parent / "data" / "bills.json"


def load_bill_data(file_path):
    """Load and return bill data from a JSON file."""
    with Path(file_path).open(encoding="utf-8") as bill_file:
        return json.load(bill_file)


def _parse_date(value):
    return date.fromisoformat(value)


def _previous_month(statement_month):
    current_month = datetime.strptime(statement_month, "%Y-%m")
    previous_month_end = current_month.date() - timedelta(days=1)
    return previous_month_end.strftime("%Y-%m")


def _previous_statement(bill):
    statement_month = bill["current_statement"]["statement_month"]
    expected_month = _previous_month(statement_month)
    return next(
        (
            statement
            for statement in bill.get("history", [])
            if statement.get("statement_month") == expected_month
        ),
        None,
    )


def get_upcoming_bills(bills, today, lookahead_days):
    """Return unpaid bills due within the configured date window."""
    today = _parse_date(today) if isinstance(today, str) else today
    end_date = today + timedelta(days=lookahead_days)

    upcoming = []
    for bill in bills:
        statement = bill["current_statement"]
        due_date = _parse_date(statement["due_date"])
        if statement.get("status") != "paid" and today <= due_date <= end_date:
            upcoming.append(bill)

    return sorted(
        upcoming,
        key=lambda bill: bill["current_statement"]["due_date"],
    )


def calculate_monthly_totals(bills):
    """Return current-month and previous-month totals."""
    current_total = sum(
        bill["current_statement"]["amount_due"] for bill in bills
    )
    previous_total = sum(
        previous["amount_due"]
        for bill in bills
        if (previous := _previous_statement(bill)) is not None
    )
    difference = current_total - previous_total
    percentage_change = (
        difference / previous_total * 100 if previous_total else None
    )

    return {
        "current_total": current_total,
        "previous_total": previous_total,
        "difference": difference,
        "percentage_change": percentage_change,
    }


def analyze_bill_change(
    current_amount,
    previous_amount,
    percentage_threshold,
    absolute_threshold,
):
    """Calculate the change and classify it."""
    if previous_amount is None:
        return {
            "amount_change": None,
            "percentage_change": None,
            "flag": "no_history",
        }

    amount_change = current_amount - previous_amount
    if previous_amount:
        percentage_change = amount_change / previous_amount * 100
    elif amount_change:
        percentage_change = None
    else:
        percentage_change = 0.0

    exceeds_absolute_threshold = abs(amount_change) >= absolute_threshold
    exceeds_percentage_threshold = (
        percentage_change is None
        or abs(percentage_change) >= percentage_threshold
    )

    if exceeds_absolute_threshold and exceeds_percentage_threshold:
        flag = "unexpectedly_high" if amount_change > 0 else "unexpectedly_low"
    else:
        flag = "within_expected_range"

    return {
        "amount_change": amount_change,
        "percentage_change": percentage_change,
        "flag": flag,
    }


def analyze_all_bill_changes(bills, comparison_rules):
    """Return monthly comparison groups for every bill."""
    groups = {
        "unexpectedly_high": [],
        "unexpectedly_low": [],
        "within_expected_range": [],
        "no_history": [],
    }

    for bill in bills:
        previous = _previous_statement(bill)
        analysis = analyze_bill_change(
            bill["current_statement"]["amount_due"],
            previous["amount_due"] if previous else None,
            comparison_rules["percentage_change_threshold"],
            comparison_rules["minimum_absolute_change"],
        )
        groups[analysis["flag"]].append(bill["name"])

    return groups


def _bill_summary_item(bill, comparison_rules):
    statement = bill["current_statement"]
    previous = _previous_statement(bill)
    previous_amount = previous["amount_due"] if previous else None
    analysis = analyze_bill_change(
        statement["amount_due"],
        previous_amount,
        comparison_rules["percentage_change_threshold"],
        comparison_rules["minimum_absolute_change"],
    )
    return {
        "bill_id": bill["bill_id"],
        "name": bill["name"],
        "due_date": statement["due_date"],
        "amount_due": statement["amount_due"],
        "previous_amount": previous_amount,
        **analysis,
    }


def build_bill_summary(data):
    """Combine upcoming bills, totals and variance analysis."""
    bills = data["bills"]
    today = _parse_date(data["today"])
    rules = data["comparison_rules"]
    upcoming = get_upcoming_bills(bills, today, data["lookahead_days"])
    upcoming_ids = {bill["bill_id"] for bill in upcoming}

    later = [
        bill
        for bill in bills
        if bill["bill_id"] not in upcoming_ids
        and bill["current_statement"].get("status") != "paid"
        and _parse_date(bill["current_statement"]["due_date"]).year == today.year
        and _parse_date(bill["current_statement"]["due_date"]).month == today.month
        and _parse_date(bill["current_statement"]["due_date"]) > today
    ]
    later.sort(key=lambda bill: bill["current_statement"]["due_date"])

    monthly_comparison = calculate_monthly_totals(bills)
    monthly_analysis = analyze_bill_change(
        monthly_comparison["current_total"],
        monthly_comparison["previous_total"],
        rules["percentage_change_threshold"],
        rules["minimum_absolute_change"],
    )
    monthly_comparison["flag"] = monthly_analysis["flag"]
    monthly_comparison["percentage_threshold"] = rules[
        "percentage_change_threshold"
    ]

    upcoming_items = [_bill_summary_item(bill, rules) for bill in upcoming]
    later_items = [_bill_summary_item(bill, rules) for bill in later]

    return {
        "as_of_date": data["today"],
        "upcoming_bills": upcoming_items,
        "upcoming_total": sum(item["amount_due"] for item in upcoming_items),
        "later_this_month": later_items,
        "later_total": sum(item["amount_due"] for item in later_items),
        "monthly_comparison": monthly_comparison,
        "individual_anomalies": analyze_all_bill_changes(bills, rules),
    }


def _format_date(value, include_year=False):
    parsed = _parse_date(value)
    formatted = f"{parsed.strftime('%B')} {parsed.day}"
    return f"{formatted}, {parsed.year}" if include_year else formatted


def _format_money(value, show_sign=False):
    if value < 0:
        return f"-${abs(value):,.2f}"
    sign = "+" if show_sign and value > 0 else ""
    return f"{sign}${value:,.2f}"


def _format_percentage(value, show_sign=False):
    if value is None:
        return "N/A"
    sign = "+" if show_sign and value > 0 else ""
    return f"{sign}{value:.1f}%"


def _flag_label(flag):
    return {
        "unexpectedly_high": "Unexpectedly high",
        "unexpectedly_low": "Unexpectedly low",
        "within_expected_range": "Within expected range",
        "no_history": "No previous-month history",
    }[flag]


def format_bill_summary(summary):
    """Convert the structured summary into readable text."""
    lines = [
        "BILL SUMMARY",
        f"As of: {_format_date(summary['as_of_date'], include_year=True)}",
        "",
        "DUE IN THE NEXT 7 DAYS",
        "",
    ]

    for bill in summary["upcoming_bills"]:
        lines.extend(
            [
                bill["name"],
                f"Due date: {_format_date(bill['due_date'])}",
                f"Amount: {_format_money(bill['amount_due'])}",
            ]
        )
        if bill["previous_amount"] is None:
            lines.append("Previous month: No history")
            lines.append("Change: N/A")
        else:
            lines.append(
                f"Previous month: {_format_money(bill['previous_amount'])}"
            )
            lines.append(
                "Change: "
                f"{_format_money(bill['amount_change'], show_sign=True)} "
                f"({_format_percentage(bill['percentage_change'], show_sign=True)})"
            )
        lines.extend([f"Flag: {_flag_label(bill['flag'])}", ""])

    lines.extend(
        [
            "Total due in the next 7 days: "
            f"{_format_money(summary['upcoming_total'])}",
            "",
            "DUE LATER THIS MONTH",
            "",
        ]
    )
    for bill in summary["later_this_month"]:
        lines.append(
            f"{bill['name']}: {_format_money(bill['amount_due'])} "
            f"due {_format_date(bill['due_date'])}"
        )

    comparison = summary["monthly_comparison"]
    lines.extend(
        [
            f"Total due later this month: {_format_money(summary['later_total'])}",
            "",
            "MONTHLY COMPARISON",
            "",
            f"Current-month total: {_format_money(comparison['current_total'])}",
            f"Previous-month total: {_format_money(comparison['previous_total'])}",
            "Difference: "
            f"{_format_money(comparison['difference'], show_sign=True)} "
            f"({_format_percentage(comparison['percentage_change'], show_sign=True)})",
            "",
            "Overall assessment:",
        ]
    )
    if comparison["flag"] == "within_expected_range":
        lines.append(
            "The monthly total is within the expected "
            f"{comparison['percentage_threshold']:g}% range."
        )
    else:
        lines.append(
            f"The monthly total is {_flag_label(comparison['flag']).lower()}."
        )

    anomalies = summary["individual_anomalies"]
    lines.extend(["", "Individual anomalies:", ""])
    labels = (
        ("unexpectedly_high", "Unexpectedly high"),
        ("unexpectedly_low", "Unexpectedly low"),
        ("within_expected_range", "Within expected range"),
        ("no_history", "No previous-month history"),
    )
    for key, label in labels:
        if anomalies[key]:
            lines.append(f"{label}: {', '.join(anomalies[key])}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze recurring monthly bills.")
    parser.add_argument(
        "file",
        nargs="?",
        default=DEFAULT_DATA_FILE,
        help="Path to the bill JSON file.",
    )
    args = parser.parse_args()
    data = load_bill_data(args.file)
    print(format_bill_summary(build_bill_summary(data)))


if __name__ == "__main__":
    main()
