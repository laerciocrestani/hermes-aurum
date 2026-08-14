"""Catálogo de contas, categorias e palavras-chave."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paths import Paths, ensure_runtime_files

ACCOUNT_KINDS = {"debit", "credit"}


@dataclass(frozen=True)
class Account:
    name: str
    aliases: tuple[str, ...]
    kind: str = "debit"
    initial_balance: float = 0.0
    closing_day: int | None = None
    due_day: int | None = None


@dataclass(frozen=True)
class Catalog:
    expense_categories: tuple[str, ...]
    income_categories: tuple[str, ...]
    accounts: tuple[Account, ...]
    expense_keywords: dict[str, tuple[str, ...]]
    income_keywords: dict[str, tuple[str, ...]]
    description_keywords: dict[str, tuple[str, ...]]


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def account_from_dict(item: dict[str, Any]) -> Account:
    kind = item.get("kind") or "debit"
    if kind not in ACCOUNT_KINDS:
        kind = "debit"
    closing = item.get("closing_day")
    due = item.get("due_day")
    return Account(
        name=item["name"],
        aliases=tuple(item.get("aliases") or []),
        kind=kind,
        initial_balance=float(item.get("initial_balance") or 0),
        closing_day=int(closing) if closing is not None else None,
        due_day=int(due) if due is not None else None,
    )


def account_to_dict(account: Account) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": account.name,
        "kind": account.kind,
        "aliases": list(account.aliases),
    }
    if account.kind == "credit":
        payload["closing_day"] = account.closing_day
        payload["due_day"] = account.due_day
    else:
        payload["initial_balance"] = round(float(account.initial_balance), 2)
    return payload


def load_catalog(paths: Paths) -> Catalog:
    ensure_runtime_files(paths)
    categories = _load_json(paths.categories)
    accounts_raw = _load_json(paths.accounts)
    keywords = _load_json(paths.keywords)

    accounts = tuple(account_from_dict(item) for item in accounts_raw.get("accounts", []))

    def _kw(section: str) -> dict[str, tuple[str, ...]]:
        data = keywords.get(section) or {}
        return {name: tuple(words) for name, words in data.items()}

    return Catalog(
        expense_categories=tuple(categories.get("expense") or []),
        income_categories=tuple(categories.get("income") or []),
        accounts=accounts,
        expense_keywords=_kw("expense"),
        income_keywords=_kw("income"),
        description_keywords=_kw("description"),
    )


def save_accounts(paths: Paths, accounts: list[Account]) -> None:
    payload = {"accounts": [account_to_dict(account) for account in accounts]}
    paths.accounts.parent.mkdir(parents=True, exist_ok=True)
    paths.accounts.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def find_account(catalog: Catalog, name: str) -> Account | None:
    key = name.casefold()
    for account in catalog.accounts:
        if account.name.casefold() == key:
            return account
    return None


def upsert_account(paths: Paths, account: Account) -> Account:
    catalog = load_catalog(paths)
    accounts = list(catalog.accounts)
    for index, existing in enumerate(accounts):
        if existing.name.casefold() == account.name.casefold():
            accounts[index] = account
            save_accounts(paths, accounts)
            return account
    accounts.append(account)
    save_accounts(paths, accounts)
    return account
