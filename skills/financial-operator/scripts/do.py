#!/usr/bin/env python3
"""Dispatcher de intenções do Aurum — hint, help e do."""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from datetime import date
from typing import Any

from catalog import get_intent, help_payload, help_text, hint_payload, menu_text
from ledger import (
    cmd_accounts,
    cmd_append,
    cmd_categories,
    cmd_check,
    init_ledger,
    load_events,
)
from paths import get_paths
from rebuild_state import rebuild
from reports import category_report, monthly_report, summary_report


def _capture_json(callable_obj, *args, **kwargs) -> dict[str, Any]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        callable_obj(*args, **kwargs)
    raw = buffer.getvalue().strip()
    if not raw:
        return {"status": "error", "message": "Saída vazia do comando"}
    return json.loads(raw)


def _paths() -> dict:
    return get_paths()


def _events(paths: dict) -> list[dict[str, Any]]:
    init_ledger(paths["ledger"], paths["seed"])
    return load_events(paths["ledger"])


def handle_list_accounts(paths: dict) -> dict[str, Any]:
    return _capture_json(cmd_accounts, paths)


def handle_list_categories(paths: dict) -> dict[str, Any]:
    payload = _capture_json(cmd_categories, paths)
    payload["status"] = "ok"
    return payload


def handle_monthly_report(paths: dict, *, month: str | None = None) -> dict[str, Any]:
    target_month = month or date.today().strftime("%Y-%m")
    events = _events(paths)
    result = monthly_report(events, target_month)
    result["status"] = "ok"
    return result


def handle_summary(paths: dict) -> dict[str, Any]:
    events = _events(paths)
    result = summary_report(events)
    result["status"] = "ok"
    return result


def handle_balances(paths: dict) -> dict[str, Any]:
    events = _events(paths)
    result = rebuild(events)
    result["status"] = "ok"
    return result


def handle_category_report(
    paths: dict,
    *,
    name: str | None = None,
    month: str | None = None,
) -> dict[str, Any]:
    if not name:
        raise ValueError("category-report exige --name <Categoria>")
    events = _events(paths)
    result = category_report(events, name, month)
    result["status"] = "ok"
    return result


def handle_ledger_check(paths: dict) -> dict[str, Any]:
    return _capture_json(cmd_check, paths)


def handle_preflight(paths: dict) -> dict[str, Any]:
    accounts = _capture_json(cmd_accounts, paths)
    categories = _capture_json(cmd_categories, paths)
    return {
        "status": "ok",
        "accounts": accounts,
        "categories": categories,
    }


def _parse_record_payload(raw: str, *, event_type: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Payload deve ser um objeto JSON")

    event: dict[str, Any] = {"type": event_type}
    event.update(payload)
    event.setdefault("date", date.today().isoformat())
    return event


def handle_record_expense(paths: dict, raw_json: str) -> dict[str, Any]:
    event = _parse_record_payload(raw_json, event_type="expense")
    append_result = _capture_json(cmd_append, paths, json.dumps(event, ensure_ascii=False))
    balances = handle_balances(paths)
    return {
        "status": "ok",
        "intent": "record-expense",
        "event": append_result.get("event", event),
        "balances": balances,
    }


def handle_record_income(paths: dict, raw_json: str) -> dict[str, Any]:
    event = _parse_record_payload(raw_json, event_type="income")
    append_result = _capture_json(cmd_append, paths, json.dumps(event, ensure_ascii=False))
    balances = handle_balances(paths)
    return {
        "status": "ok",
        "intent": "record-income",
        "event": append_result.get("event", event),
        "balances": balances,
    }


def handle_record_transfer(paths: dict, raw_json: str) -> dict[str, Any]:
    event = _parse_record_payload(raw_json, event_type="transfer")
    if "from" not in event or "to" not in event:
        raise ValueError("transfer exige 'from', 'to' e 'amount'")
    append_result = _capture_json(cmd_append, paths, json.dumps(event, ensure_ascii=False))
    balances = handle_balances(paths)
    return {
        "status": "ok",
        "intent": "record-transfer",
        "event": append_result.get("event", event),
        "balances": balances,
    }


def handle_record_mixed_expense(paths: dict, raw_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Payload deve ser um objeto JSON")

    parts = payload.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("record-mixed-expense exige array 'parts' com ao menos um item")

    category = payload.get("category")
    if not category:
        raise ValueError("record-mixed-expense exige 'category'")
    txn_date = payload.get("date", date.today().isoformat())
    description = payload.get("description", "")

    recorded: list[dict[str, Any]] = []
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("cada item de 'parts' deve ser um objeto")
        account = part.get("account")
        amount = part.get("amount")
        if not account or not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("cada part exige 'account' e 'amount' > 0")
        event: dict[str, Any] = {
            "type": "expense",
            "date": txn_date,
            "account": account,
            "category": category,
            "amount": amount,
        }
        if description:
            event["description"] = description
        if "installments" in part:
            event["installments"] = part["installments"]
        append_result = _capture_json(cmd_append, paths, json.dumps(event, ensure_ascii=False))
        recorded.append(append_result.get("event", event))

    balances = handle_balances(paths)
    return {
        "status": "ok",
        "intent": "record-mixed-expense",
        "events": recorded,
        "part_count": len(recorded),
        "balances": balances,
    }


def handle_add_category(paths: dict, raw_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc
    name = payload.get("name")
    kind = payload.get("kind", "expense")
    if not name or not isinstance(name, str):
        raise ValueError("add-category exige 'name'")
    if kind not in ("expense", "income"):
        raise ValueError("kind deve ser 'expense' ou 'income'")

    cat_path = paths["categories"]
    with open(cat_path, encoding="utf-8") as f:
        data = json.load(f)
    pool = data.setdefault(kind, [])
    if name in pool:
        return {
            "status": "ok",
            "message": "Categoria já existe",
            "name": name,
            "kind": kind,
            "categories": data,
        }
    pool.append(name)
    pool.sort()
    with open(cat_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return {
        "status": "ok",
        "intent": "add-category",
        "added": name,
        "kind": kind,
        "categories": data,
    }


def handle_add_account(paths: dict, raw_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc
    event: dict[str, Any] = {"type": "account"}
    event.update(payload)
    if "name" not in event or "kind" not in event:
        raise ValueError("add-account exige 'name' e 'kind'")
    append_result = _capture_json(cmd_append, paths, json.dumps(event, ensure_ascii=False))
    accounts = handle_list_accounts(paths)
    return {
        "status": "ok",
        "intent": "add-account",
        "event": append_result.get("event", event),
        "accounts": accounts,
    }


def handle_update_account(paths: dict, raw_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc
    event: dict[str, Any] = {"type": "account_config"}
    event.update(payload)
    if "account" not in event:
        raise ValueError("update-account exige 'account'")
    append_result = _capture_json(cmd_append, paths, json.dumps(event, ensure_ascii=False))
    accounts = handle_list_accounts(paths)
    return {
        "status": "ok",
        "intent": "update-account",
        "event": append_result.get("event", event),
        "accounts": accounts,
    }


HANDLERS: dict[str, Any] = {
    "list-accounts": lambda paths, _args: handle_list_accounts(paths),
    "list-categories": lambda paths, _args: handle_list_categories(paths),
    "monthly-report": lambda paths, args: handle_monthly_report(paths, month=args.get("month")),
    "summary": lambda paths, _args: handle_summary(paths),
    "balances": lambda paths, _args: handle_balances(paths),
    "category-report": lambda paths, args: handle_category_report(
        paths,
        name=args.get("name"),
        month=args.get("month"),
    ),
    "ledger-check": lambda paths, _args: handle_ledger_check(paths),
    "preflight": lambda paths, _args: handle_preflight(paths),
}


WRITE_HANDLERS = {
    "record-expense": handle_record_expense,
    "record-income": handle_record_income,
    "record-transfer": handle_record_transfer,
    "record-mixed-expense": handle_record_mixed_expense,
    "add-category": handle_add_category,
    "add-account": handle_add_account,
    "update-account": handle_update_account,
}


def _parse_run_args(argv: list[str]) -> tuple[str, dict[str, str], str | None]:
    if not argv:
        raise ValueError("Uso: aurum-run do <intent> [args...]")
    intent_name = argv[0]
    kwargs: dict[str, str] = {}
    json_payload: str | None = None
    index = 1
    while index < len(argv):
        token = argv[index]
        if token in ("--month", "--name") and index + 1 < len(argv):
            key = token.lstrip("-").replace("-", "_")
            kwargs[key] = argv[index + 1]
            index += 2
            continue
        json_payload = token
        index += 1
        if index < len(argv):
            json_payload = " ".join(argv[index - 1 :])
        break
    return intent_name, kwargs, json_payload


def run_intent(intent_name: str, argv: list[str]) -> dict[str, Any]:
    intent = get_intent(intent_name)
    if intent is None:
        return {
            "status": "error",
            "message": f"Intenção desconhecida: {intent_name}",
            "suggestion": f'aurum-run hint "{intent_name}"',
            "available": list(HANDLERS) + list(WRITE_HANDLERS),
        }

    paths = _paths()
    try:
        if intent_name in WRITE_HANDLERS:
            _, _kwargs, json_payload = _parse_run_args([intent_name, *argv])
            if not json_payload:
                raise ValueError(f"{intent_name} exige JSON com os campos da transação")
            return WRITE_HANDLERS[intent_name](paths, json_payload)

        _name, kwargs, _json_payload = _parse_run_args([intent_name, *argv])
        if intent_name not in HANDLERS:
            return {
                "status": "error",
                "message": f"Intenção sem handler: {intent_name}",
                "suggestion": "aurum-run help --json",
            }
        return HANDLERS[intent_name](paths, kwargs)
    except (ValueError, FileNotFoundError) as exc:
        return {
            "status": "error",
            "message": str(exc),
            "intent": intent_name,
            "suggestion": f'aurum-run hint "{intent.description_pt}"',
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Intenções do Aurum")
    sub = parser.add_subparsers(dest="command", required=True)

    p_hint = sub.add_parser("hint")
    p_hint.add_argument("query", nargs="+")

    p_help = sub.add_parser("help")
    p_help.add_argument("--json", action="store_true")

    sub.add_parser("menu")

    p_run = sub.add_parser("run")
    p_run.add_argument("intent")
    p_run.add_argument("rest", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "hint":
        query = " ".join(args.query)
        print(json.dumps(hint_payload(query), ensure_ascii=False, indent=2))
        return 0

    if args.command == "help":
        if args.json:
            print(json.dumps(help_payload(), ensure_ascii=False, indent=2))
        else:
            print(help_text())
        return 0

    if args.command == "menu":
        print(menu_text())
        return 0

    if args.command == "run":
        result = run_intent(args.intent, args.rest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") != "error" else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
