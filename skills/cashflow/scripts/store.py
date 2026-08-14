"""Store mutável do fluxo de caixa (JSONL com id)."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

ENTRY_TYPES = {"expense", "income"}
METHODS = {"debito", "credito", "pix", "dinheiro"}
EDITABLE_FIELDS = ("type", "date", "amount", "category", "account", "method", "description")


def new_id() -> str:
    return "cf_" + uuid.uuid4().hex[:10]


def load_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido na linha {lineno}: {exc}") from exc
            if isinstance(item, dict):
                entries.append(item)
    return entries


def write_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in entries)
    fd, tmp_name = tempfile.mkstemp(prefix="cashflow.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def get_entry(entries: list[dict[str, Any]], entry_id: str) -> dict[str, Any] | None:
    for item in entries:
        if item.get("id") == entry_id:
            return item
    return None


def append_entry(path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    entries = load_entries(path)
    stored = dict(entry)
    stored.setdefault("id", new_id())
    entries.append(stored)
    write_entries(path, entries)
    return stored


def remove_entry(path: Path, entry_id: str) -> dict[str, Any]:
    entries = load_entries(path)
    found = get_entry(entries, entry_id)
    if found is None:
        raise KeyError(f"Lançamento não encontrado: {entry_id}")
    remaining = [item for item in entries if item.get("id") != entry_id]
    write_entries(path, remaining)
    return found


def edit_entry(path: Path, entry_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    entries = load_entries(path)
    updated: dict[str, Any] | None = None
    next_entries: list[dict[str, Any]] = []
    for item in entries:
        if item.get("id") != entry_id:
            next_entries.append(item)
            continue
        merged = dict(item)
        for key, value in fields.items():
            if key == "id":
                continue
            if key not in EDITABLE_FIELDS:
                raise ValueError(f"Campo não editável: {key}")
            merged[key] = value
        updated = merged
        next_entries.append(merged)
    if updated is None:
        raise KeyError(f"Lançamento não encontrado: {entry_id}")
    write_entries(path, next_entries)
    return updated


def filter_entries(
    entries: list[dict[str, Any]],
    *,
    date: str | None = None,
    month: str | None = None,
    entry_type: str | None = None,
    account: str | None = None,
    category: str | None = None,
    amount: float | None = None,
) -> list[dict[str, Any]]:
    result = entries
    if date:
        result = [item for item in result if item.get("date") == date]
    if month:
        result = [item for item in result if str(item.get("date", "")).startswith(month)]
    if entry_type:
        result = [item for item in result if item.get("type") == entry_type]
    if account:
        result = [item for item in result if item.get("account") == account]
    if category:
        result = [item for item in result if item.get("category") == category]
    if amount is not None:
        result = [item for item in result if _same_amount(item.get("amount"), amount)]
    return result


def _same_amount(left: Any, right: float) -> bool:
    try:
        return abs(float(left) - float(right)) < 0.001
    except (TypeError, ValueError):
        return False


def totals(entries: list[dict[str, Any]]) -> dict[str, float]:
    expenses = sum(float(item.get("amount") or 0) for item in entries if item.get("type") == "expense")
    income = sum(float(item.get("amount") or 0) for item in entries if item.get("type") == "income")
    return {
        "expense": round(expenses, 2),
        "income": round(income, 2),
        "net": round(income - expenses, 2),
    }
