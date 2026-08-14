"""Catálogo de contas, categorias e palavras-chave."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paths import Paths, ensure_runtime_files


@dataclass(frozen=True)
class Account:
    name: str
    aliases: tuple[str, ...]


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


def load_catalog(paths: Paths) -> Catalog:
    ensure_runtime_files(paths)
    categories = _load_json(paths.categories)
    accounts_raw = _load_json(paths.accounts)
    keywords = _load_json(paths.keywords)

    accounts = tuple(
        Account(
            name=item["name"],
            aliases=tuple(item.get("aliases") or []),
        )
        for item in accounts_raw.get("accounts", [])
    )

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
    payload = {
        "accounts": [
            {"name": account.name, "aliases": list(account.aliases)}
            for account in accounts
        ]
    }
    paths.accounts.parent.mkdir(parents=True, exist_ok=True)
    paths.accounts.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def add_account(paths: Paths, name: str, aliases: list[str] | None = None) -> Account:
    catalog = load_catalog(paths)
    existing = {account.name.casefold(): account for account in catalog.accounts}
    if name.casefold() in existing:
        return existing[name.casefold()]
    account = Account(name=name, aliases=tuple(aliases or [name.casefold()]))
    save_accounts(paths, [*catalog.accounts, account])
    return account
