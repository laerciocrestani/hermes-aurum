#!/usr/bin/env python3
"""Rebuild financial state from append-only ledger events."""

from __future__ import annotations

import json
import sys
from datetime import date
from typing import Any

from credit_card import (
    AccountInfo,
    CardState,
    apply_card_expense,
    apply_card_payment,
    build_account_registry,
    card_to_dict,
    is_credit_card,
    recompute_balance,
)
from ledger import load_events
from paths import get_paths


def apply_event(
    event: dict[str, Any],
    balances: dict[str, float],
    liabilities: dict[str, float],
    positions: dict[str, float],
    registry: dict[str, AccountInfo],
    cards: dict[str, CardState],
    as_of: date,
) -> None:
    etype = event.get("type")

    if etype == "expense":
        account = event["account"]
        amount = float(event["amount"])
        if is_credit_card(registry, account):
            info = registry[account]
            card = cards.setdefault(account, CardState())
            apply_card_expense(
                card,
                info,
                event["date"],
                amount,
                int(event.get("installments", 1)),
                as_of=as_of,
            )
        else:
            balances[account] = balances.get(account, 0.0) - amount
    elif etype == "income":
        account = event["account"]
        amount = float(event["amount"])
        if is_credit_card(registry, account):
            info = registry[account]
            card = cards.setdefault(account, CardState())
            apply_card_payment(card, info, amount, as_of=as_of)
        else:
            balances[account] = balances.get(account, 0.0) + amount
    elif etype == "transfer":
        amount = float(event["amount"])
        src, dst = event["from"], event["to"]
        src_info = registry.get(src, AccountInfo())
        dst_info = registry.get(dst, AccountInfo())

        if src_info.kind == "asset":
            balances[src] = balances.get(src, 0.0) - amount
        elif is_credit_card(registry, src):
            info = registry[src]
            card = cards.setdefault(src, CardState())
            card.committed = round(card.committed + amount, 2)
            if info.closing_day is not None:
                card.balance = recompute_balance(card, info.closing_day, as_of)

        if dst_info.kind == "asset":
            balances[dst] = balances.get(dst, 0.0) + amount
        elif is_credit_card(registry, dst):
            info = registry[dst]
            card = cards.setdefault(dst, CardState())
            apply_card_payment(card, info, amount, as_of=as_of)
    elif etype == "investment":
        amount = float(event["amount"])
        balances[event["account"]] = balances.get(event["account"], 0.0) - amount
        asset = event["asset"]
        positions[asset] = positions.get(asset, 0.0) + amount
    elif etype == "liability":
        liabilities[event["name"]] = float(event["amount"])
    elif etype == "adjustment":
        account = event["account"]
        amount = float(event["amount"])
        if is_credit_card(registry, account):
            info = registry[account]
            card = cards.setdefault(account, CardState())
            if amount > 0:
                card.committed = round(card.committed + amount, 2)
            else:
                apply_card_payment(card, info, abs(amount), as_of=as_of)
            if info.closing_day is not None:
                card.balance = recompute_balance(card, info.closing_day, as_of)
        else:
            balances[account] = balances.get(account, 0.0) + amount


def rebuild(events: list[dict[str, Any]], as_of: date | None = None) -> dict[str, Any]:
    as_of = as_of or date.today()
    registry = build_account_registry(events)
    balances: dict[str, float] = {}
    liabilities: dict[str, float] = {}
    positions: dict[str, float] = {}
    cards: dict[str, CardState] = {}

    for event in events:
        apply_event(event, balances, liabilities, positions, registry, cards, as_of)

    for name, info in registry.items():
        if info.kind == "liability" and info.closing_day is not None:
            cards.setdefault(name, CardState())

    asset_balances = {
        name: round(value, 2)
        for name, value in balances.items()
        if registry.get(name, AccountInfo()).kind == "asset"
    }
    card_debt = round(sum(card.balance for card in cards.values()), 2)
    standalone = round(sum(liabilities.values()), 2)

    total_assets = round(sum(asset_balances.values()) + sum(positions.values()), 2)
    total_liabilities = round(card_debt + standalone, 2)
    net_worth = round(total_assets - total_liabilities, 2)
    available = round(sum(asset_balances.values()) - card_debt - standalone, 2)

    credit_cards = {
        name: card_to_dict(card, registry[name])
        for name, card in sorted(cards.items())
    }

    return {
        "as_of": as_of.isoformat(),
        "balances": dict(sorted(asset_balances.items())),
        "liabilities": {k: round(v, 2) for k, v in sorted(liabilities.items())},
        "positions": {k: round(v, 2) for k, v in sorted(positions.items())},
        "credit_cards": credit_cards,
        "net_worth": net_worth,
        "available": available,
    }


def main() -> int:
    paths = get_paths()
    if not paths["ledger"].exists():
        print(json.dumps({"status": "error", "message": "Ledger not found. Record a transaction first."}))
        return 1
    events = load_events(paths["ledger"])
    print(json.dumps(rebuild(events), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
