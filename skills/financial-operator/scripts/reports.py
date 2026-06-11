#!/usr/bin/env python3
"""Financial reports derived from ledger events."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from typing import Any

from ledger import load_events
from paths import get_paths


def filter_month(events: list[dict[str, Any]], month: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("date", "").startswith(month)]


def monthly_report(events: list[dict[str, Any]], month: str) -> dict[str, Any]:
    month_events = filter_month(events, month)
    expenses: dict[str, float] = defaultdict(float)
    incomes: dict[str, float] = defaultdict(float)

    for e in month_events:
        if e.get("type") == "expense":
            expenses[e["category"]] += float(e["amount"])
        elif e.get("type") == "income":
            incomes[e["category"]] += float(e["amount"])

    total_expense = sum(expenses.values())
    total_income = sum(incomes.values())

    return {
        "month": month,
        "expenses": {k: round(v, 2) for k, v in sorted(expenses.items())},
        "incomes": {k: round(v, 2) for k, v in sorted(incomes.items())},
        "total_expense": round(total_expense, 2),
        "total_income": round(total_income, 2),
        "net_cashflow": round(total_income - total_expense, 2),
        "transaction_count": len(month_events),
    }


def category_report(events: list[dict[str, Any]], name: str, month: str | None) -> dict[str, Any]:
    filtered = events
    if month:
        filtered = filter_month(filtered, month)

    matches = [
        e
        for e in filtered
        if e.get("type") in ("expense", "income") and e.get("category") == name
    ]
    total = sum(float(e["amount"]) for e in matches)

    return {
        "category": name,
        "month": month,
        "total": round(total, 2),
        "transactions": matches,
    }


def summary_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    month = date.today().strftime("%Y-%m")
    return monthly_report(events, month)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aurum financial reports")
    sub = parser.add_subparsers(dest="command", required=True)

    p_monthly = sub.add_parser("monthly")
    p_monthly.add_argument("--month", required=True)

    p_category = sub.add_parser("category")
    p_category.add_argument("--name", required=True)
    p_category.add_argument("--month")

    sub.add_parser("summary")

    args = parser.parse_args()
    paths = get_paths()

    if not paths["ledger"].exists():
        print(json.dumps({"status": "error", "message": "Ledger not found."}))
        return 1

    events = load_events(paths["ledger"])

    if args.command == "monthly":
        result = monthly_report(events, args.month)
    elif args.command == "category":
        result = category_report(events, args.name, args.month)
    else:
        result = summary_report(events)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
