#!/usr/bin/env python3
"""Relatórios financeiros derivados de eventos do ledger."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from typing import Any

from credit_card import build_account_registry, expense_report_amounts
from ledger import load_events
from paths import get_paths


def filter_month(events: list[dict[str, Any]], month: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("date", "").startswith(month)]


def monthly_report(events: list[dict[str, Any]], month: str) -> dict[str, Any]:
    registry = build_account_registry(events)
    expenses: dict[str, float] = defaultdict(float)
    incomes: dict[str, float] = defaultdict(float)
    transaction_count = 0

    for e in events:
        etype = e.get("type")
        if etype == "expense":
            for stmt_month, amount in expense_report_amounts(e, registry):
                if stmt_month == month:
                    expenses[e["category"]] += amount
                    transaction_count += 1
        elif etype == "income" and e.get("date", "").startswith(month):
            incomes[e["category"]] += float(e["amount"])
            transaction_count += 1

    total_expense = sum(expenses.values())
    total_income = sum(incomes.values())

    return {
        "month": month,
        "expenses": {k: round(v, 2) for k, v in sorted(expenses.items())},
        "incomes": {k: round(v, 2) for k, v in sorted(incomes.items())},
        "total_expense": round(total_expense, 2),
        "total_income": round(total_income, 2),
        "net_cashflow": round(total_income - total_expense, 2),
        "transaction_count": transaction_count,
    }


def category_report(events: list[dict[str, Any]], name: str, month: str | None) -> dict[str, Any]:
    registry = build_account_registry(events)
    matches: list[dict[str, Any]] = []
    total = 0.0

    for e in events:
        if e.get("type") == "expense" and e.get("category") == name:
            for stmt_month, amount in expense_report_amounts(e, registry):
                if month is None or stmt_month == month:
                    entry = dict(e)
                    entry["statement_month"] = stmt_month
                    entry["report_amount"] = amount
                    matches.append(entry)
                    total += amount
        elif e.get("type") == "income" and e.get("category") == name:
            if month is None or e.get("date", "").startswith(month):
                matches.append(e)
                total += float(e["amount"])

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
    parser = argparse.ArgumentParser(description="Relatórios financeiros do Aurum")
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
        print(json.dumps({"status": "error", "message": "Ledger não encontrado."}))
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
