"""Monta comando shell (ou executa) a partir de texto em português."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from typing import Any

from catalog import AURUM_RUN
from credit_card import build_account_registry, is_credit_card
from ledger import account_names, init_ledger, load_events
from paths import get_paths


def normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents)


def compact_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(text))


AMOUNT_RE = re.compile(
    r"(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais|real)?",
    re.IGNORECASE,
)
INSTALLMENTS_RE = re.compile(r"(?:em\s+)?(\d+)\s*x\b", re.IGNORECASE)
WRITE_VERBS_RE = re.compile(r"\b(gastei|paguei|comprei|gasto|despesa)\b", re.IGNORECASE)


def parse_amount(text: str) -> float | None:
    match = AMOUNT_RE.search(text)
    if not match:
        return None
    raw = match.group(1).replace(",", ".")
    return float(raw)


def parse_installments(text: str) -> int:
    match = INSTALLMENTS_RE.search(text)
    if not match:
        return 1
    return max(1, int(match.group(1)))


def detect_payment_kind(text: str) -> str | None:
    norm = normalize_text(text)
    if re.search(r"\b(credito|cartao|parcelad)\w*", norm):
        return "liability"
    if re.search(r"\b(debito|pix)\w*", norm):
        return "asset"
    return None


def detect_category(text: str) -> tuple[str, str]:
    norm = normalize_text(text)
    if re.search(r"\bmercad\w*", norm):
        return "Alimentação", "Mercado"
    if re.search(r"\b(roupa|vestuario|vestuário)\w*", norm):
        return "Vestuário", "Roupas"
    if re.search(r"\btransport\w*", norm):
        return "Transporte", "Transporte"
    return "Outros", "Despesa"


def account_hints(text: str) -> list[str]:
    norm = normalize_text(text)
    hints: list[str] = []
    if re.search(r"c6\s*bank|c6bank", norm):
        hints.append("c6")
    if re.search(r"\binter\b", norm):
        hints.append("inter")
    if re.search(r"nubank", norm):
        hints.append("nubank")
    if re.search(r"carteira", norm):
        hints.append("carteira")
    if not hints:
        tokens = [compact_key(token) for token in norm.split() if len(token) >= 3]
        hints.extend(token for token in tokens if token not in {"reais", "real", "gastei", "paguei", "comprei"})
    return hints


def load_account_rows(paths: dict[str, Any]) -> list[dict[str, Any]]:
    ledger_path = paths["ledger"]
    init_ledger(ledger_path, paths["seed"])
    events = load_events(ledger_path)
    registry = build_account_registry(events)
    rows: list[dict[str, Any]] = []
    for name in sorted(account_names(events)):
        info = registry.get(name)
        kind = info.kind if info else "asset"
        rows.append({"name": name, "kind": kind})
    return rows


def resolve_account(text: str, accounts: list[dict[str, Any]], prefer_kind: str | None) -> str | None:
    hints = account_hints(text)
    if not hints:
        return None

    candidates: list[dict[str, Any]] = []
    for account in accounts:
        key = compact_key(account["name"])
        if any(hint in key or key in hint for hint in hints):
            candidates.append(account)

    if prefer_kind:
        filtered = [item for item in candidates if item["kind"] == prefer_kind]
        if filtered:
            candidates = filtered

    if len(candidates) == 1:
        return candidates[0]["name"]

    if len(candidates) > 1:
        norm = compact_key(text)
        for account in candidates:
            if compact_key(account["name"]) in norm or norm in compact_key(account["name"]):
                return account["name"]
        if prefer_kind:
            for account in candidates:
                if account["kind"] == prefer_kind:
                    return account["name"]
        return candidates[0]["name"]

    return None


class ComposeError(ValueError):
    def __init__(self, message: str, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.extra = extra or {}


def update_account_command(account: str) -> str:
    example = {
        "account": account,
        "credit_limit": 10000,
        "closing_day": 1,
        "due_day": 10,
        "billing_profile": "br",
    }
    body = json.dumps(example, ensure_ascii=False)
    escaped = body.replace("'", "'\\''")
    return f"{AURUM_RUN} do update-account '{escaped}'"


def validate_card_config(paths: dict[str, Any], account: str) -> None:
    init_ledger(paths["ledger"], paths["seed"])
    events = load_events(paths["ledger"])
    registry = build_account_registry(events)
    if not is_credit_card(registry, account):
        return

    info = registry[account]
    missing: list[str] = []
    if info.credit_limit is None:
        missing.append("credit_limit")
    if info.closing_day is None:
        missing.append("closing_day")
    if info.due_day is None:
        missing.append("due_day")

    if not missing:
        return

    raise ComposeError(
        f"Cartão '{account}' sem configuração ({', '.join(missing)}). "
        "Configure closing_day (fechamento) e due_day (vencimento) antes de registrar no crédito.",
        {
            "missing_fields": missing,
            "fix_command": update_account_command(account),
            "suggestion": update_account_command(account),
        },
    )


def build_expense_payload(text: str, paths: dict[str, Any]) -> dict[str, Any]:
    if not WRITE_VERBS_RE.search(text):
        raise ValueError("Não identifiquei despesa — use verbos como gastei, paguei ou comprei")

    amount = parse_amount(text)
    if amount is None or amount <= 0:
        raise ValueError("Não identifiquei o valor — inclua o valor em reais")

    accounts = load_account_rows(paths)
    prefer_kind = detect_payment_kind(text)
    account = resolve_account(text, accounts, prefer_kind)
    if not account:
        debit = [row["name"] for row in accounts if row["kind"] == "asset"]
        credit = [row["name"] for row in accounts if row["kind"] == "liability"]
        raise ComposeError(
            "Conta não identificada — rode list-accounts e use o nome exato",
            {"debit": debit, "credit": credit},
        )

    category, description = detect_category(text)
    installments = parse_installments(text)
    payload: dict[str, Any] = {
        "amount": amount,
        "account": account,
        "category": category,
        "description": description,
        "date": date.today().isoformat(),
    }
    if installments > 1:
        payload["installments"] = installments

    validate_card_config(paths, account)
    return payload


def shell_record_expense(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False)
    escaped = body.replace("'", "'\\''")
    return f"{AURUM_RUN} do record-expense '{escaped}'"


def compose_payload(text: str, paths: dict[str, Any] | None = None) -> dict[str, Any]:
    paths = paths or get_paths()
    expense = build_expense_payload(text, paths)
    command = shell_record_expense(expense)
    return {
        "status": "ok",
        "intent": "record-expense",
        "tool": "terminal",
        "command": command,
        "parsed": expense,
        "user_text": text,
    }
