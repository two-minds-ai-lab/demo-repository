from copy import deepcopy

import pytest

from bill_analysis import (
    analyze_all_bill_changes,
    build_bill_summary,
    calculate_monthly_totals,
    format_bill_summary,
    get_upcoming_bills,
    load_bill_data,
)


@pytest.fixture
def bill_data():
    return load_bill_data("data/bills.json")


def test_loads_exactly_six_complete_bills(bill_data):
    assert len(bill_data["bills"]) == 6
    for bill in bill_data["bills"]:
        assert {
            "bill_id",
            "name",
            "category",
            "recurrence",
            "current_statement",
            "history",
        } <= bill.keys()
        assert "amount_due" in bill["current_statement"]
        assert "amount_due" in bill["history"][0]


def test_finds_three_upcoming_bills(bill_data):
    result = get_upcoming_bills(
        bill_data["bills"],
        bill_data["today"],
        bill_data["lookahead_days"],
    )

    assert [bill["name"] for bill in result] == [
        "Chase Visa",
        "PSE Electricity",
        "Citi Mastercard",
    ]


def test_upcoming_total_is_507_90(bill_data):
    result = build_bill_summary(bill_data)

    assert result["upcoming_total"] == pytest.approx(507.90)


def test_monthly_totals(bill_data):
    result = calculate_monthly_totals(bill_data["bills"])

    assert result["current_total"] == pytest.approx(762.90)
    assert result["previous_total"] == pytest.approx(733.50)
    assert result["difference"] == pytest.approx(29.40)
    assert result["percentage_change"] == pytest.approx(4.0, abs=0.05)


def test_chase_is_unexpectedly_high(bill_data):
    result = analyze_all_bill_changes(
        bill_data["bills"],
        bill_data["comparison_rules"],
    )

    assert "Chase Visa" in result["unexpectedly_high"]


def test_tmobile_is_unexpectedly_low(bill_data):
    result = analyze_all_bill_changes(
        bill_data["bills"],
        bill_data["comparison_rules"],
    )

    assert "T-Mobile" in result["unexpectedly_low"]


def test_paid_bill_is_not_upcoming(bill_data):
    data = deepcopy(bill_data)
    data["bills"][0]["current_statement"]["status"] = "paid"

    result = get_upcoming_bills(
        data["bills"],
        data["today"],
        data["lookahead_days"],
    )

    assert "Chase Visa" not in [bill["name"] for bill in result]


def test_missing_history_does_not_crash(bill_data):
    data = deepcopy(bill_data)
    data["bills"][0]["history"] = []

    result = build_bill_summary(data)

    chase = next(
        bill for bill in result["upcoming_bills"] if bill["name"] == "Chase Visa"
    )
    assert chase["flag"] == "no_history"
    assert chase["previous_amount"] is None
    assert "Chase Visa" in result["individual_anomalies"]["no_history"]


def test_later_this_month_total_is_255(bill_data):
    result = build_bill_summary(bill_data)

    assert [bill["name"] for bill in result["later_this_month"]] == [
        "T-Mobile",
        "American Express",
        "Xfinity Broadband",
    ]
    assert result["later_total"] == pytest.approx(255.0)


def test_report_formats_negative_change_before_currency_symbol(bill_data):
    report = format_bill_summary(build_bill_summary(bill_data))

    assert "Change: -$50.00 (-55.6%)" in report
