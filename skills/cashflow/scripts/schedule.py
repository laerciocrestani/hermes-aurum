"""Agenda de cobranças: contas mensais e parcelamentos no crédito."""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from store import get_entry, load_entries, write_entries

SCHEDULE_KINDS = {"recurring", "installment"}
EDITABLE_FIELDS = (
    "kind",
    "description",
    "category",
    "amount",
    "total",
    "installments",
    "account",
    "method",
    "due_day",
    "start_month",
    "active",
)


def new_obligation_id() -> str:
    return "ob_" + uuid.uuid4().hex[:10]


def load_obligations(path: Path) -> list[dict[str, Any]]:
    return load_entries(path)


def write_obligations(path: Path, items: list[dict[str, Any]]) -> None:
    write_entries(path, items)


def append_obligation(path: Path, item: dict[str, Any]) -> dict[str, Any]:
    items = load_obligations(path)
    stored = dict(item)
    stored.setdefault("id", new_obligation_id())
    stored.setdefault("active", True)
    items.append(stored)
    write_obligations(path, items)
    return stored


def remove_obligation(path: Path, item_id: str) -> dict[str, Any]:
    items = load_obligations(path)
    found = get_entry(items, item_id)
    if found is None:
        raise KeyError(f"Cobrança não encontrada: {item_id}")
    remaining = [item for item in items if item.get("id") != item_id]
    write_obligations(path, remaining)
    return found


def edit_obligation(path: Path, item_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    items = load_obligations(path)
    updated: dict[str, Any] | None = None
    next_items: list[dict[str, Any]] = []
    for item in items:
        if item.get("id") != item_id:
            next_items.append(item)
            continue
        merged = dict(item)
        for key, value in fields.items():
            if key == "id":
                continue
            if key not in EDITABLE_FIELDS:
                raise ValueError(f"Campo não editável: {key}")
            merged[key] = value
        if "total" in merged and "installments" in merged and merged.get("kind") == "installment":
            n = int(merged["installments"])
            if n > 0:
                merged["amount"] = split_installments(float(merged["total"]), n)[0]
        updated = merged
        next_items.append(merged)
    if updated is None:
        raise KeyError(f"Cobrança não encontrada: {item_id}")
    write_obligations(path, next_items)
    return updated


def split_installments(total: float, count: int) -> list[float]:
    if count < 1:
        raise ValueError("installments deve ser >= 1")
    cents = int(round(float(total) * 100))
    base, remainder = divmod(cents, count)
    amounts = []
    for index in range(count):
        extra = 1 if index >= count - remainder else 0
        amounts.append(round((base + extra) / 100, 2))
    return amounts


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    shifted = month - 1 + delta
    return year + shifted // 12, shifted % 12 + 1


def due_date(year: int, month: int, due_day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(int(due_day), 1), last))


def parse_month(value: str) -> tuple[int, int]:
    year_s, month_s = value.split("-", 1)
    return int(year_s), int(month_s)


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def active_obligations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item.get("active", True)]


def project_charges(
    obligations: list[dict[str, Any]],
    today: date,
    *,
    months: int = 6,
    cashflow: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    horizon_year, horizon_month = add_months(today.year, today.month, max(months, 1) - 1)
    horizon_end = due_date(horizon_year, horizon_month, 31)
    charges: list[dict[str, Any]] = []

    for item in active_obligations(obligations):
        kind = item.get("kind")
        if kind == "recurring":
            charges.extend(_project_recurring(item, today, horizon_end))
        elif kind == "installment":
            charges.extend(_project_installment(item, today, horizon_end))

    cashflow = cashflow or []
    for charge in charges:
        charge["settled"] = _is_settled(charge, cashflow)
        if charge["settled"]:
            charge["status"] = "settled"
        elif charge["date"] < today.isoformat():
            charge["status"] = "overdue"
        else:
            charge["status"] = "upcoming"

    charges.sort(key=lambda row: (row["date"], row.get("description") or ""))
    return charges


def _project_recurring(item: dict[str, Any], today: date, horizon_end: date) -> list[dict[str, Any]]:
    due_day = int(item.get("due_day") or today.day)
    year, month = today.year, today.month
    rows: list[dict[str, Any]] = []
    while True:
        when = due_date(year, month, due_day)
        if when > horizon_end:
            break
        rows.append(_charge_row(item, when, float(item["amount"]), None, None))
        year, month = add_months(year, month, 1)
        if date(year, month, 1) > horizon_end:
            break
    return rows


def _project_installment(item: dict[str, Any], today: date, horizon_end: date) -> list[dict[str, Any]]:
    count = int(item.get("installments") or 0)
    if count < 1:
        return []
    total = float(item.get("total") or 0)
    amounts = split_installments(total, count)
    start = str(item.get("start_month") or today.strftime("%Y-%m"))
    year, month = parse_month(start)
    due_day = int(item.get("due_day") or 1)
    base = str(item.get("description") or "Compra")
    rows: list[dict[str, Any]] = []
    for index, amount in enumerate(amounts, start=1):
        when = due_date(year, month, due_day)
        if when > horizon_end:
            break
        label = f"{base} {index}/{count}"
        rows.append(_charge_row(item, when, amount, index, label))
        year, month = add_months(year, month, 1)
    return rows


def _charge_row(
    item: dict[str, Any],
    when: date,
    amount: float,
    installment_index: int | None,
    description: str | None,
) -> dict[str, Any]:
    return {
        "obligation_id": item.get("id"),
        "kind": item.get("kind"),
        "date": when.isoformat(),
        "amount": round(float(amount), 2),
        "category": item.get("category"),
        "account": item.get("account"),
        "method": item.get("method"),
        "description": description or item.get("description"),
        "due_day": item.get("due_day"),
        "installment_index": installment_index,
        "installments": item.get("installments"),
    }


def _is_settled(charge: dict[str, Any], cashflow: list[dict[str, Any]]) -> bool:
    month = charge["date"][:7]
    description = str(charge.get("description") or "")
    amount = float(charge.get("amount") or 0)
    for entry in cashflow:
        if entry.get("type") != "expense":
            continue
        if str(entry.get("date") or "")[:7] != month:
            continue
        entry_desc = str(entry.get("description") or "")
        if description and entry_desc == description:
            return True
        if charge.get("kind") == "recurring" and description and description.casefold() in entry_desc.casefold():
            return True
        if (
            charge.get("kind") == "installment"
            and entry.get("account") == charge.get("account")
            and abs(float(entry.get("amount") or 0) - amount) < 0.01
            and entry.get("method") == "credito"
        ):
            return True
    return False
