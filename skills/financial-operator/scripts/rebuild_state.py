#!/usr/bin/env python3
"""Rebuild financial state from append-only ledger events."""

from __future__ import annotations

import json
import sys
from datetime import date
from typing import Any

from ledger import load_events
from paths import get_paths


def apply_event(
    event: dict[str, Any],
    balances: dict[str, float],
    liabilities: dict[str, float],
    positions: dict[str, float],
) -> None:
    etype = event.get("type")

    if etype == "expense":
        balances[event["account"]] = balances.get(event["account"], 0.0) - float(event["amount"])
    elif etype == "income":
        balances[event["account"]] = balances.get(event["account"], 0.0) + float(event["amount"])
    elif etype == "transfer":
        amount = float(event["amount"])
        balances[event["from"]] = balances.get(event["from"], 0.0) - amount
        balances[event["to"]] = balances.get(event["to"], 0.0) + amount
    elif etype == "investment":
        amount = float(event["amount"])
        balances[event["account"]] = balances.get(event["account"], 0.0) - amount
        asset = event["asset"]
        positions[asset] = positions.get(asset, 0.0) + amount
    elif etype == "liability":
        liabilities[event["name"]] = float(event["amount"])
    elif etype == "adjustment":
        balances[event["account"]] = balances.get(event["account"], 0.0) + float(event["amount"])


def rebuild(events: list[dict[str, Any]]) -> dict[str, Any]:
    balances: dict[str, float] = {}
    liabilities: dict[str, float] = {}
    positions: dict[str, float] = {}

    for event in events:
        apply_event(event, balances, liabilities, positions)

    total_assets = sum(balances.values()) + sum(positions.values())
    total_liabilities = sum(liabilities.values())
    net_worth = total_assets - total_liabilities
    available = sum(balances.values()) - total_liabilities

    return {
        "as_of": date.today().isoformat(),
        "balances": {k: round(v, 2) for k, v in sorted(balances.items())},
        "liabilities": {k: round(v, 2) for k, v in sorted(liabilities.items())},
        "positions": {k: round(v, 2) for k, v in sorted(positions.items())},
        "net_worth": round(net_worth, 2),
        "available": round(available, 2),
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
