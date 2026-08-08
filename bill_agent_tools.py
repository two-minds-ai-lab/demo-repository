from pathlib import Path

from bill_analysis import DEFAULT_DATA_FILE, build_bill_summary, load_bill_data


def get_bill_due_dates_data(data_file=DEFAULT_DATA_FILE):
    """Return upcoming and later-this-month bill due-date information."""
    data = load_bill_data(Path(data_file))
    summary = build_bill_summary(data)

    return {
        "as_of_date": summary["as_of_date"],
        "lookahead_days": data["lookahead_days"],
        "due_in_lookahead_window": summary["upcoming_bills"],
        "total_due_in_lookahead_window": summary["upcoming_total"],
        "due_later_this_month": summary["later_this_month"],
        "total_due_later_this_month": summary["later_total"],
    }


def get_bill_change_analysis_data(data_file=DEFAULT_DATA_FILE):
    """Return monthly totals and per-bill change classifications."""
    data = load_bill_data(Path(data_file))
    summary = build_bill_summary(data)

    return {
        "as_of_date": summary["as_of_date"],
        "monthly_comparison": summary["monthly_comparison"],
        "individual_anomalies": summary["individual_anomalies"],
    }
