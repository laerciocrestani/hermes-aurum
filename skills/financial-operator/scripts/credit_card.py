"""Credit card billing cycle and installment logic for Aurum."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import Any

BILLING_PROFILES = frozenset({"br", "simple"})


@dataclass
class AccountInfo:
    kind: str = "asset"
    credit_limit: float | None = None
    closing_day: int | None = None
    due_day: int | None = None
    billing_profile: str = "br"


@dataclass
class InstallmentPlan:
    purchase_date: str
    total: float
    installments: int
    schedule: list[dict[str, Any]]


@dataclass
class CardState:
    balance: float = 0.0
    committed: float = 0.0
    statements: dict[str, dict[str, Any]] = field(default_factory=dict)
    installment_plans: list[InstallmentPlan] = field(default_factory=list)


def build_account_registry(events: list[dict[str, Any]]) -> dict[str, AccountInfo]:
    registry: dict[str, AccountInfo] = {}
    for event in events:
        etype = event.get("type")
        if etype == "account":
            name = event["name"]
            info = registry.get(name, AccountInfo())
            info.kind = event.get("kind", "asset")
            for key in ("credit_limit", "closing_day", "due_day", "billing_profile"):
                if key in event:
                    setattr(info, key, event[key])
            registry[name] = info
        elif etype == "account_config":
            account = event["account"]
            if account not in registry:
                registry[account] = AccountInfo(kind="liability")
            info = registry[account]
            for key in ("credit_limit", "closing_day", "due_day", "billing_profile"):
                if key in event:
                    setattr(info, key, event[key])
    return registry


def is_credit_card(registry: dict[str, AccountInfo], account: str) -> bool:
    return registry.get(account, AccountInfo()).kind == "liability"


def split_installments(total: float, count: int) -> list[float]:
    if count <= 1:
        return [round(total, 2)]
    base = round(total / count, 2)
    parts = [base] * count
    parts[-1] = round(total - base * (count - 1), 2)
    return parts


def _month_add(year: int, month: int, offset: int) -> tuple[int, int]:
    index = (year * 12 + (month - 1)) + offset
    return index // 12, (index % 12) + 1


def first_statement_year_month(purchase: date, closing_day: int) -> tuple[int, int]:
    if purchase.day <= closing_day:
        return purchase.year, purchase.month
    return _month_add(purchase.year, purchase.month, 1)


def statement_month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def installment_schedule(
    purchase: date,
    closing_day: int,
    total: float,
    installments: int,
) -> list[tuple[str, float]]:
    year, month = first_statement_year_month(purchase, closing_day)
    amounts = split_installments(total, installments)
    return [
        (statement_month_key(*_month_add(year, month, index)), amount)
        for index, amount in enumerate(amounts)
    ]


def closing_date_for_month(year: int, month: int, closing_day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(closing_day, last_day))


def is_statement_closed(month_key: str, closing_day: int, as_of: date) -> bool:
    year, month = map(int, month_key.split("-"))
    return as_of >= closing_date_for_month(year, month, closing_day)


def recompute_balance(card: CardState, closing_day: int, as_of: date) -> float:
    total = 0.0
    for month_key, stmt in card.statements.items():
        if stmt.get("paid"):
            continue
        if is_statement_closed(month_key, closing_day, as_of):
            total += float(stmt["amount"])
    return round(total, 2)


def add_to_statement(card: CardState, month_key: str, amount: float, due_day: int | None) -> None:
    stmt = card.statements.setdefault(month_key, {"amount": 0.0, "paid": False})
    stmt["amount"] = round(float(stmt["amount"]) + amount, 2)
    if due_day is not None:
        stmt["due_day"] = due_day


def apply_card_expense(
    card: CardState,
    info: AccountInfo,
    purchase_date: str,
    amount: float,
    installments: int,
    as_of: date | None = None,
) -> None:
    if info.closing_day is None:
        raise ValueError("Credit card requires closing_day in account_config")

    purchase = date.fromisoformat(purchase_date)
    profile = info.billing_profile or "br"
    count = max(1, installments)

    if profile == "simple" and count > 1:
        raise ValueError("installments > 1 requires billing_profile 'br'")

    schedule = installment_schedule(purchase, info.closing_day, float(amount), count)
    card.committed = round(card.committed + float(amount), 2)

    plan = InstallmentPlan(
        purchase_date=purchase_date,
        total=float(amount),
        installments=count,
        schedule=[{"month": month, "amount": part} for month, part in schedule],
    )
    if count > 1:
        card.installment_plans.append(plan)

    for month_key, part in schedule:
        add_to_statement(card, month_key, part, info.due_day)

    card.balance = recompute_balance(card, info.closing_day, as_of or date.today())


def apply_card_payment(
    card: CardState,
    info: AccountInfo,
    amount: float,
    as_of: date | None = None,
) -> None:
    if info.closing_day is None:
        raise ValueError("Credit card requires closing_day for payments")

    remaining = float(amount)
    for month_key in sorted(card.statements.keys()):
        if remaining <= 0:
            break
        stmt = card.statements[month_key]
        if stmt.get("paid"):
            continue
        due = float(stmt["amount"])
        if due <= 0:
            continue
        paid = min(remaining, due)
        stmt["amount"] = round(due - paid, 2)
        remaining = round(remaining - paid, 2)
        card.committed = round(max(0.0, card.committed - paid), 2)
        if stmt["amount"] == 0:
            stmt["paid"] = True

    card.balance = recompute_balance(card, info.closing_day, as_of or date.today())


def card_to_dict(card: CardState, info: AccountInfo) -> dict[str, Any]:
    limit = info.credit_limit
    available = round(limit - card.committed, 2) if limit is not None else None
    result: dict[str, Any] = {
        "balance": card.balance,
        "committed": card.committed,
        "credit_limit": limit,
        "available_credit": available,
        "closing_day": info.closing_day,
        "due_day": info.due_day,
        "billing_profile": info.billing_profile or "br",
        "statements": card.statements,
    }
    if card.installment_plans:
        result["installment_plans"] = [
            {
                "purchase_date": plan.purchase_date,
                "total": plan.total,
                "installments": plan.installments,
                "schedule": plan.schedule,
            }
            for plan in card.installment_plans
        ]
    return result


def expense_report_amounts(
    event: dict[str, Any],
    registry: dict[str, AccountInfo],
) -> list[tuple[str, float]]:
    """Return (YYYY-MM, amount) pairs for reporting — one per statement month."""
    account = event.get("account", "")
    info = registry.get(account, AccountInfo())
    if info.kind != "liability" or info.closing_day is None:
        month = event.get("date", "")[:7]
        return [(month, float(event["amount"]))]

    purchase_date = event.get("date", "")
    installments = int(event.get("installments", 1))
    profile = info.billing_profile or "br"
    count = max(1, installments)
    if profile == "simple" and count > 1:
        count = 1

    purchase = date.fromisoformat(purchase_date)
    schedule = installment_schedule(purchase, info.closing_day, float(event["amount"]), count)
    return schedule
