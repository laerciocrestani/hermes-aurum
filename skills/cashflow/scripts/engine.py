"""Regras de negócio do fluxo de caixa e da agenda de cobranças."""

from __future__ import annotations

from datetime import date
from typing import Any

from catalog import Catalog, load_catalog
from parse import ParsedIntent, parse_message
from paths import Paths, ensure_runtime_files
from schedule import (
    EDITABLE_FIELDS as SCHEDULE_FIELDS,
    append_obligation,
    edit_obligation,
    load_obligations,
    project_charges,
    remove_obligation,
    split_installments,
)
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


def describe_obligation(item: dict[str, Any]) -> str:
    if item.get("kind") == "installment":
        total = float(item.get("total") or 0)
        count = int(item.get("installments") or 0)
        parcel = float(item.get("amount") or 0)
        parts = [f"Compra de {format_brl(total)}"]
        if item.get("description") and item["description"] != "Compra":
            parts.append(f"({item['description']})")
        parts.append(f"no {item.get('account')} ({method_label(item.get('method')) or 'crédito'})")
        parts.append(f"em {count}x de {format_brl(parcel)}")
        if item.get("start_month"):
            parts.append(f"— 1ª parcela em {item['start_month']}")
        if item.get("due_day"):
            parts.append(f"(dia {item['due_day']})")
        return " ".join(parts) + "."
    parts = [f"Conta mensal {item.get('description') or item.get('category')}"]
    parts.append(f"de {format_brl(float(item.get('amount') or 0))}")
    if item.get("due_day"):
        parts.append(f"— vence dia {item['due_day']}")
    if item.get("account"):
        parts.append(f"no {item['account']}")
    if item.get("method"):
        parts.append(f"({method_label(item['method'])})")
    return " ".join(parts) + "."


def _ok(action: str, **payload: Any) -> dict[str, Any]:
    return {"status": "ok", "action": action, **payload}


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


def match_obligations(items: list[dict[str, Any]], parsed: ParsedIntent) -> list[dict[str, Any]]:
    result = [item for item in items if item.get("active", True)]
    if parsed.kind:
        result = [item for item in result if item.get("kind") == parsed.kind]
    if parsed.account:
        result = [item for item in result if item.get("account") == parsed.account]
    if parsed.installments:
        result = [item for item in result if int(item.get("installments") or 0) == parsed.installments]
    if parsed.amount is not None:
        amount_hits = []
        for item in result:
            monthly = float(item.get("amount") or 0)
            total = float(item.get("total") or 0)
            if abs(monthly - parsed.amount) < 0.01 or abs(total - parsed.amount) < 0.01:
                amount_hits.append(item)
        if amount_hits:
            result = amount_hits
    desc = parsed.description
    generic = {None, parsed.category, "Lançamento", "Compra"}
    if desc and desc not in generic:
        named = [item for item in result if item.get("description") == desc]
        if named:
            result = named
    if parsed.last and result:
        return result[-1:]
    if parsed.last and not result:
        pool = [item for item in items if item.get("active", True)]
        if parsed.kind:
            pool = [item for item in pool if item.get("kind") == parsed.kind]
        return pool[-1:] if pool else []
    return result


def pick_obligation(items: list[dict[str, Any]], parsed: ParsedIntent) -> dict[str, Any]:
    matched = match_obligations(items, parsed)
    if not matched:
        raise CashflowError(
            "Não encontrei uma cobrança que combine com essa mensagem.",
            {"parsed": _public_parsed(parsed)},
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


def _resolve_account(parsed: ParsedIntent, catalog: Catalog, entries: list[dict[str, Any]]) -> str:
    account = parsed.account or last_account(entries) or DEFAULT_ACCOUNT
    names = {item.name for item in catalog.accounts}
    if account not in names:
        return DEFAULT_ACCOUNT if DEFAULT_ACCOUNT in names else next(iter(names))
    return account


def _resolve_category(parsed: ParsedIntent, catalog: Catalog) -> str:
    entry_type = parsed.entry_type or "expense"
    pool = catalog.expense_categories if entry_type == "expense" else catalog.income_categories
    return parsed.category or ("Outros" if "Outros" in pool else pool[0])


def validate_obligation(item: dict[str, Any], catalog: Catalog) -> None:
    if item.get("kind") not in {"recurring", "installment"}:
        raise CashflowError("kind deve ser recurring ou installment")
    amount = item.get("amount")
    if not isinstance(amount, (int, float)) or float(amount) <= 0:
        raise CashflowError("amount deve ser um número maior que zero")
    if item.get("category") not in catalog.expense_categories:
        raise CashflowError(
            f"Categoria inválida: {item.get('category')}",
            {"valid": list(catalog.expense_categories)},
        )
    names = {account.name for account in catalog.accounts}
    if item.get("account") not in names:
        raise CashflowError(
            f"Conta inválida: {item.get('account')}",
            {"valid": sorted(names)},
        )
    due_day = item.get("due_day")
    if due_day is not None and (not isinstance(due_day, int) or not 1 <= due_day <= 31):
        raise CashflowError("due_day deve ser um inteiro entre 1 e 31")
    if item.get("kind") == "installment":
        count = item.get("installments")
        if not isinstance(count, int) or count < 2:
            raise CashflowError("Parcelamento exige 2x ou mais")
        total = item.get("total")
        if not isinstance(total, (int, float)) or float(total) <= 0:
            raise CashflowError("total deve ser maior que zero")


def build_add_entry(parsed: ParsedIntent, catalog: Catalog, entries: list[dict[str, Any]], today: date) -> dict[str, Any]:
    if parsed.amount is None or parsed.amount <= 0:
        raise CashflowError("Não identifiquei o valor. Inclua o valor em reais.")
    entry_type = parsed.entry_type or "expense"
    return {
        "type": entry_type,
        "date": parsed.date or today.isoformat(),
        "amount": round(float(parsed.amount), 2),
        "category": _resolve_category(parsed, catalog),
        "account": _resolve_account(parsed, catalog, entries),
        "method": parsed.method,
        "description": parsed.description or _resolve_category(parsed, catalog),
    }


def build_recurring(parsed: ParsedIntent, catalog: Catalog, entries: list[dict[str, Any]], today: date) -> dict[str, Any]:
    if parsed.amount is None or parsed.amount <= 0:
        raise CashflowError("Não identifiquei o valor da conta mensal.")
    category = _resolve_category(parsed, catalog)
    return {
        "kind": "recurring",
        "description": parsed.description or category,
        "category": category,
        "amount": round(float(parsed.amount), 2),
        "account": _resolve_account(parsed, catalog, entries),
        "method": parsed.method,
        "due_day": parsed.due_day or today.day,
        "active": True,
    }


def build_installment(parsed: ParsedIntent, catalog: Catalog, entries: list[dict[str, Any]], today: date) -> dict[str, Any]:
    count = parsed.installments or 0
    if count < 2:
        raise CashflowError("Não identifiquei o número de parcelas (ex.: em 5x).")
    if parsed.amount is None or parsed.amount <= 0:
        raise CashflowError("Não identifiquei o valor da compra.")
    total = round(float(parsed.amount), 2)
    parcels = split_installments(total, count)
    category = _resolve_category(parsed, catalog)
    return {
        "kind": "installment",
        "description": parsed.description or "Compra",
        "category": category,
        "amount": parcels[0],
        "total": total,
        "installments": count,
        "account": _resolve_account(parsed, catalog, entries),
        "method": parsed.method or "credito",
        "due_day": parsed.due_day or today.day,
        "start_month": today.strftime("%Y-%m"),
        "active": True,
    }


def add_from_payload(paths: Paths, payload: dict[str, Any], today: date) -> dict[str, Any]:
    ensure_runtime_files(paths)
    kind = payload.get("kind")
    installments = payload.get("installments")
    if kind in {"recurring", "installment"} or (isinstance(installments, int) and installments > 1):
        parsed = ParsedIntent(
            action="add",
            entry_type="expense",
            amount=float(payload["amount"]) if payload.get("amount") is not None else (
                float(payload["total"]) if payload.get("total") is not None else None
            ),
            category=payload.get("category"),
            account=payload.get("account"),
            method=payload.get("method"),
            description=payload.get("description"),
            kind=kind or "installment",
            installments=installments if isinstance(installments, int) else None,
            due_day=payload.get("due_day"),
            target="schedule",
        )
        return add_obligation(paths, parsed, today)
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
    return _ok("add", message=describe_entry(stored), entry=stored)


def add_obligation(paths: Paths, parsed: ParsedIntent, today: date) -> dict[str, Any]:
    catalog = load_catalog(paths)
    entries = load_entries(paths.cashflow)
    if parsed.kind == "installment":
        item = build_installment(parsed, catalog, entries, today)
        validate_obligation(item, catalog)
        stored = append_obligation(paths.schedule, item)
        charges = project_charges([stored], today, months=max(stored["installments"], 1))
        return _ok(
            "add_installment",
            message=describe_obligation(stored),
            obligation=stored,
            charges=charges,
        )
    item = build_recurring(parsed, catalog, entries, today)
    validate_obligation(item, catalog)
    existing = [
        row
        for row in load_obligations(paths.schedule)
        if row.get("active", True)
        and row.get("kind") == "recurring"
        and str(row.get("description") or "").casefold() == str(item["description"]).casefold()
    ]
    if existing:
        fields = {
            "amount": item["amount"],
            "account": item["account"],
            "method": item["method"],
            "due_day": item["due_day"],
            "category": item["category"],
        }
        stored = edit_obligation(paths.schedule, existing[-1]["id"], fields)
        return _ok(
            "edit_recurring",
            message=f"Conta atualizada. {describe_obligation(stored)}",
            obligation=stored,
            changes=fields,
        )
    stored = append_obligation(paths.schedule, item)
    return _ok("add_recurring", message=describe_obligation(stored), obligation=stored)


def apply_text(paths: Paths, text: str, today: date | None = None) -> dict[str, Any]:
    ensure_runtime_files(paths)
    today = today or date.today()
    catalog = load_catalog(paths)
    parsed = parse_message(text, catalog, today)
    if parsed.action == "unknown":
        return _error(
            "Não entendi se é para inserir, remover ou editar. "
            "Exemplos: 'Gastei 30 reais no mercado', 'Conta de luz 150 por mês', "
            "'Compra de 1000 no crédito Inter em 5x', 'O que vence esse mês?'.",
            parsed={"action": parsed.action, "raw": parsed.raw},
        )
    if parsed.action == "upcoming" or (parsed.action == "list" and parsed.target == "schedule"):
        return upcoming(paths, today=today)
    if parsed.target == "schedule":
        return _apply_schedule(paths, parsed, today, catalog)
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


def _apply_schedule(paths: Paths, parsed: ParsedIntent, today: date, catalog: Catalog) -> dict[str, Any]:
    if parsed.action == "add":
        return add_obligation(paths, parsed, today)
    items = load_obligations(paths.schedule)
    if parsed.action == "remove":
        target = pick_obligation(items, parsed)
        removed = remove_obligation(paths.schedule, target["id"])
        return _ok("remove_schedule", message=f"Removido. {describe_obligation(removed)}", obligation=removed)
    if parsed.action == "edit":
        fields = {key: value for key, value in parsed.fields.items() if key in SCHEDULE_FIELDS}
        if not fields:
            return _error(
                "Não identifiquei o que alterar na cobrança. Ex.: 'Muda a água para 90' ou 'Muda o vencimento da luz para dia 15'.",
                parsed=_public_parsed(parsed),
            )
        target = pick_obligation(items, parsed)
        preview = dict(target)
        preview.update(fields)
        if preview.get("kind") == "installment" and "amount" in fields and "total" not in fields:
            count = int(preview.get("installments") or 0)
            if count:
                preview["total"] = round(float(fields["amount"]) * count, 2)
                fields["total"] = preview["total"]
        validate_obligation(preview, catalog)
        updated = edit_obligation(paths.schedule, target["id"], fields)
        return _ok(
            "edit_schedule",
            message=f"Atualizado. {describe_obligation(updated)}",
            obligation=updated,
            changes=fields,
        )
    return _error(f"Ação não suportada na agenda: {parsed.action}")


def upcoming(
    paths: Paths,
    *,
    today: date | None = None,
    months: int = 6,
) -> dict[str, Any]:
    ensure_runtime_files(paths)
    today = today or date.today()
    obligations = load_obligations(paths.schedule)
    cashflow = load_entries(paths.cashflow)
    charges = project_charges(obligations, today, months=months, cashflow=cashflow)
    open_charges = [row for row in charges if row["status"] != "settled"]
    this_month = today.strftime("%Y-%m")
    month_open = [row for row in open_charges if row["date"].startswith(this_month)]
    total_open = round(sum(float(row["amount"]) for row in open_charges), 2)
    total_month = round(sum(float(row["amount"]) for row in month_open), 2)
    overdue = [row for row in open_charges if row["status"] == "overdue"]
    return _ok(
        "upcoming",
        months=months,
        count=len(open_charges),
        month=this_month,
        month_count=len(month_open),
        totals={"open": total_open, "month": total_month, "overdue": round(sum(float(r["amount"]) for r in overdue), 2)},
        obligations=[item for item in obligations if item.get("active", True)],
        charges=open_charges,
        message=_upcoming_message(this_month, month_open, open_charges, total_month, total_open),
    )


def _upcoming_message(
    month: str,
    month_open: list[dict[str, Any]],
    open_charges: list[dict[str, Any]],
    total_month: float,
    total_open: float,
) -> str:
    if not open_charges:
        return "Nenhuma cobrança futura na agenda."
    preview = " · ".join(
        f"{row.get('description')} {row['date'][8:]} ({format_brl(row['amount'])})"
        for row in month_open[:5]
    )
    extra = f" Este mês ({month}): {len(month_open)} · {format_brl(total_month)}."
    if preview:
        extra += f" {preview}."
    return (
        f"{len(open_charges)} cobrança(s) em aberto · {format_brl(total_open)}."
        + extra
    )


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
    if entry_id.startswith("ob_"):
        removed = remove_obligation(paths.schedule, entry_id)
        return _ok("remove_schedule", message=f"Removido. {describe_obligation(removed)}", obligation=removed)
    removed = remove_entry(paths.cashflow, entry_id)
    return _ok("remove", message=f"Removido. {describe_entry(removed)}", entry=removed)


def edit_by_id(paths: Paths, entry_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    ensure_runtime_files(paths)
    catalog = load_catalog(paths)
    if entry_id.startswith("ob_"):
        items = load_obligations(paths.schedule)
        current = next((item for item in items if item.get("id") == entry_id), None)
        if current is None:
            raise KeyError(f"Cobrança não encontrada: {entry_id}")
        preview = dict(current)
        preview.update(fields)
        validate_obligation(preview, catalog)
        updated = edit_obligation(paths.schedule, entry_id, fields)
        return _ok("edit_schedule", message=f"Atualizado. {describe_obligation(updated)}", obligation=updated, changes=fields)
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
        "target": parsed.target,
        "kind": parsed.kind,
        "installments": parsed.installments,
        "due_day": parsed.due_day,
        "fields": parsed.fields,
    }
