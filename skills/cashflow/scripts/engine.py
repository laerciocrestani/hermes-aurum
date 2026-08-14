"""Regras de negócio do fluxo de caixa."""

from __future__ import annotations

from datetime import date
from typing import Any

from catalog import Catalog, load_catalog
from parse import ParsedIntent, parse_message
from paths import Paths, ensure_runtime_files
from store import (
    METHODS,
    append_entry,
    edit_entry,
    filter_entries,
    load_entries,
    remove_entry,
    totals,
)

DEFAULT_ACCOUNT = "Carteira"


class CashflowError(ValueError):
    def __init__(self, message: str, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.extra = extra or {}


def format_brl(amount: float) -> str:
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def method_label(method: str | None) -> str:
    labels = {
        "debito": "débito",
        "credito": "crédito",
        "pix": "PIX",
        "dinheiro": "dinheiro",
    }
    return labels.get(method or "", method or "")


def describe_entry(entry: dict[str, Any]) -> str:
    kind = "Despesa" if entry.get("type") == "expense" else "Receita"
    parts = [
        f"{kind} de {format_brl(float(entry['amount']))}",
        f"em {entry.get('category')}",
    ]
    if entry.get("description") and entry.get("description") != entry.get("category"):
        parts.append(f"({entry['description']})")
    if entry.get("account"):
        parts.append(f"no {entry['account']}")
    if entry.get("method"):
        parts.append(f"({method_label(entry['method'])})")
    if entry.get("date"):
        parts.append(f"em {entry['date']}")
    return " ".join(parts) + "."


def _ok(action: str, **payload: Any) -> dict[str, Any]:
    result = {"status": "ok", "action": action, **payload}
    return result


def _error(message: str, **payload: Any) -> dict[str, Any]:
    return {"status": "error", "message": message, **payload}


def last_account(entries: list[dict[str, Any]]) -> str | None:
    for item in reversed(entries):
        account = item.get("account")
        if account:
            return str(account)
    return None


def match_entries(entries: list[dict[str, Any]], parsed: ParsedIntent) -> list[dict[str, Any]]:
    matched = filter_entries(
        entries,
        date=parsed.date,
        entry_type=parsed.entry_type,
        account=parsed.account,
        category=parsed.category,
        amount=parsed.amount,
    )
    has_filters = any(
        value is not None
        for value in (parsed.date, parsed.entry_type, parsed.account, parsed.category, parsed.amount)
    )
    if parsed.last and matched:
        return matched[-1:]
    if parsed.last and not has_filters:
        return entries[-1:] if entries else []
    return matched


def pick_match(entries: list[dict[str, Any]], parsed: ParsedIntent) -> dict[str, Any]:
    matched = match_entries(entries, parsed)
    if not matched:
        raise CashflowError(
            "Não encontrei um lançamento que combine com essa mensagem.",
            {"parsed": parsed.__dict__},
        )
    return matched[-1]


def validate_entry(entry: dict[str, Any], catalog: Catalog) -> None:
    if entry.get("type") not in {"expense", "income"}:
        raise CashflowError("type deve ser expense ou income")
    amount = entry.get("amount")
    if not isinstance(amount, (int, float)) or float(amount) <= 0:
        raise CashflowError("amount deve ser um número maior que zero")
    pool = catalog.expense_categories if entry["type"] == "expense" else catalog.income_categories
    if entry.get("category") not in pool:
        raise CashflowError(
            f"Categoria inválida: {entry.get('category')}",
            {"valid": list(pool)},
        )
    names = {account.name for account in catalog.accounts}
    if entry.get("account") not in names:
        raise CashflowError(
            f"Conta inválida: {entry.get('account')}",
            {"valid": sorted(names)},
        )
    method = entry.get("method")
    if method is not None and method not in METHODS:
        raise CashflowError(
            f"Método inválido: {method}",
            {"valid": sorted(METHODS)},
        )


def build_add_entry(parsed: ParsedIntent, catalog: Catalog, entries: list[dict[str, Any]], today: date) -> dict[str, Any]:
    if parsed.amount is None or parsed.amount <= 0:
        raise CashflowError("Não identifiquei o valor. Inclua o valor em reais.")
    entry_type = parsed.entry_type or "expense"
    pool = catalog.expense_categories if entry_type == "expense" else catalog.income_categories
    category = parsed.category or ("Outros" if "Outros" in pool else pool[0])
    account = parsed.account or last_account(entries) or DEFAULT_ACCOUNT
    names = {item.name for item in catalog.accounts}
    if account not in names:
        account = DEFAULT_ACCOUNT if DEFAULT_ACCOUNT in names else next(iter(names))
    return {
        "type": entry_type,
        "date": parsed.date or today.isoformat(),
        "amount": round(float(parsed.amount), 2),
        "category": category,
        "account": account,
        "method": parsed.method,
        "description": parsed.description or category,
    }


def add_from_payload(paths: Paths, payload: dict[str, Any], today: date) -> dict[str, Any]:
    ensure_runtime_files(paths)
    catalog = load_catalog(paths)
    entries = load_entries(paths.cashflow)
    parsed = ParsedIntent(
        action="add",
        entry_type=payload.get("type", "expense"),
        amount=float(payload["amount"]) if payload.get("amount") is not None else None,
        category=payload.get("category"),
        account=payload.get("account"),
        method=payload.get("method"),
        description=payload.get("description"),
        date=payload.get("date"),
    )
    entry = build_add_entry(parsed, catalog, entries, today)
    validate_entry(entry, catalog)
    stored = append_entry(paths.cashflow, entry)
    return _ok(
        "add",
        message=describe_entry(stored),
        entry=stored,
    )


def apply_text(paths: Paths, text: str, today: date | None = None) -> dict[str, Any]:
    ensure_runtime_files(paths)
    today = today or date.today()
    catalog = load_catalog(paths)
    parsed = parse_message(text, catalog, today)
    if parsed.action == "unknown":
        return _error(
            "Não entendi se é para inserir, remover ou editar. "
            "Exemplos: 'Gastei 30 reais no mercado', 'Apaga o último', 'Corrige o valor para 35'.",
            parsed={"action": parsed.action, "raw": parsed.raw},
        )
    if parsed.action == "add":
        entries = load_entries(paths.cashflow)
        entry = build_add_entry(parsed, catalog, entries, today)
        validate_entry(entry, catalog)
        stored = append_entry(paths.cashflow, entry)
        return _ok("add", message=describe_entry(stored), entry=stored, parsed=_public_parsed(parsed))
    if parsed.action == "remove":
        entries = load_entries(paths.cashflow)
        target = pick_match(entries, parsed)
        removed = remove_entry(paths.cashflow, target["id"])
        return _ok("remove", message=f"Removido. {describe_entry(removed)}", entry=removed)
    if parsed.action == "edit":
        if not parsed.fields:
            return _error(
                "Não identifiquei o que alterar. Diga o novo valor, por exemplo: 'Corrige o valor para 35'.",
                parsed=_public_parsed(parsed),
            )
        entries = load_entries(paths.cashflow)
        target = pick_match(entries, parsed)
        preview = dict(target)
        preview.update(parsed.fields)
        validate_entry(preview, catalog)
        updated = edit_entry(paths.cashflow, target["id"], parsed.fields)
        return _ok(
            "edit",
            message=f"Atualizado. {describe_entry(updated)}",
            entry=updated,
            changes=parsed.fields,
        )
    if parsed.action == "list":
        return list_entries(paths, date_value=parsed.date or today.isoformat())
    return _error(f"Ação não suportada: {parsed.action}")


def list_entries(
    paths: Paths,
    *,
    date_value: str | None = None,
    month: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    ensure_runtime_files(paths)
    entries = load_entries(paths.cashflow)
    filtered = filter_entries(entries, date=date_value, month=month)
    if limit is not None:
        filtered = filtered[-limit:]
    summary = totals(filtered)
    return _ok(
        "list",
        date=date_value,
        month=month,
        count=len(filtered),
        totals=summary,
        entries=filtered,
        message=_list_message(date_value, month, filtered, summary),
    )


def _list_message(
    date_value: str | None,
    month: str | None,
    entries: list[dict[str, Any]],
    summary: dict[str, float],
) -> str:
    when = date_value or month or "período"
    if not entries:
        return f"Nenhum lançamento em {when}."
    return (
        f"{len(entries)} lançamento(s) em {when}. "
        f"Despesas {format_brl(summary['expense'])} · "
        f"Receitas {format_brl(summary['income'])} · "
        f"Saldo {format_brl(summary['net'])}."
    )


def remove_by_id(paths: Paths, entry_id: str) -> dict[str, Any]:
    ensure_runtime_files(paths)
    removed = remove_entry(paths.cashflow, entry_id)
    return _ok("remove", message=f"Removido. {describe_entry(removed)}", entry=removed)


def edit_by_id(paths: Paths, entry_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    ensure_runtime_files(paths)
    catalog = load_catalog(paths)
    entries = load_entries(paths.cashflow)
    current = next((item for item in entries if item.get("id") == entry_id), None)
    if current is None:
        raise KeyError(f"Lançamento não encontrado: {entry_id}")
    preview = dict(current)
    preview.update(fields)
    validate_entry(preview, catalog)
    updated = edit_entry(paths.cashflow, entry_id, fields)
    return _ok("edit", message=f"Atualizado. {describe_entry(updated)}", entry=updated, changes=fields)


def list_accounts(paths: Paths) -> dict[str, Any]:
    catalog = load_catalog(paths)
    rows = [{"name": account.name, "aliases": list(account.aliases)} for account in catalog.accounts]
    return _ok("accounts", accounts=rows, count=len(rows))


def list_categories(paths: Paths) -> dict[str, Any]:
    catalog = load_catalog(paths)
    return _ok(
        "categories",
        expense=list(catalog.expense_categories),
        income=list(catalog.income_categories),
    )


def _public_parsed(parsed: ParsedIntent) -> dict[str, Any]:
    return {
        "action": parsed.action,
        "type": parsed.entry_type,
        "amount": parsed.amount,
        "category": parsed.category,
        "account": parsed.account,
        "method": parsed.method,
        "description": parsed.description,
        "date": parsed.date,
        "last": parsed.last,
        "fields": parsed.fields,
    }
