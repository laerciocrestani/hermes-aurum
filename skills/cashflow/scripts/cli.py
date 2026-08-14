#!/usr/bin/env python3
"""CLI do Aurum — ponto de entrada usado pelo agente Hermes."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from engine import (
    CashflowError,
    add_from_payload,
    apply_text,
    edit_by_id,
    list_accounts,
    list_categories,
    list_entries,
    remove_by_id,
)
from paths import get_paths

USAGE = """Aurum — fluxo de caixa
  apply "Gastei 30 reais em mercado no débito com o banco Inter"
  add '{"type":"expense","amount":30,"category":"Alimentação","account":"Banco Inter"}'
  remove <id>
  edit <id> '{"amount":35}'
  list [--date YYYY-MM-DD] [--month YYYY-MM]
  today
  accounts
  categories
"""


def _today() -> date:
    raw = os.environ.get("AURUM_TODAY", "").strip()
    if raw:
        return date.fromisoformat(raw)
    return date.today()


def _print(payload: dict[str, Any], exit_code: int = 0) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return exit_code


def _load_json_arg(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CashflowError(f"JSON inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise CashflowError("JSON deve ser um objeto")
    return data


def _run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aurum-run", description="Fluxo de caixa do Aurum")
    parser.add_argument("--root", help="Raiz do perfil (testes)")
    sub = parser.add_subparsers(dest="command")

    apply_cmd = sub.add_parser("apply", help="Interpreta uma mensagem e executa")
    apply_cmd.add_argument("text", nargs="+", help="Mensagem do usuário")

    add_cmd = sub.add_parser("add", help="Insere um lançamento via JSON")
    add_cmd.add_argument("payload")

    remove_cmd = sub.add_parser("remove", help="Remove pelo id")
    remove_cmd.add_argument("id")

    edit_cmd = sub.add_parser("edit", help="Edita pelo id")
    edit_cmd.add_argument("id")
    edit_cmd.add_argument("payload")

    list_cmd = sub.add_parser("list", help="Lista lançamentos")
    list_cmd.add_argument("--date")
    list_cmd.add_argument("--month")
    list_cmd.add_argument("--limit", type=int)

    sub.add_parser("today", help="Lançamentos de hoje")
    sub.add_parser("accounts", help="Lista contas")
    sub.add_parser("categories", help="Lista categorias")
    sub.add_parser("help", help="Ajuda em JSON")

    args = parser.parse_args(argv)
    paths = get_paths(Path(args.root) if args.root else None)
    today = _today()
    command = args.command or "help"

    try:
        if command == "help":
            return _print({"status": "ok", "usage": USAGE.strip().splitlines()})
        if command == "apply":
            result = apply_text(paths, " ".join(args.text), today=today)
        elif command == "add":
            result = add_from_payload(paths, _load_json_arg(args.payload), today)
        elif command == "remove":
            result = remove_by_id(paths, args.id)
        elif command == "edit":
            result = edit_by_id(paths, args.id, _load_json_arg(args.payload))
        elif command == "list":
            result = list_entries(paths, date_value=args.date, month=args.month, limit=args.limit)
        elif command == "today":
            result = list_entries(paths, date_value=today.isoformat())
        elif command == "accounts":
            result = list_accounts(paths)
        elif command == "categories":
            result = list_categories(paths)
        else:
            result = {"status": "error", "message": f"Comando desconhecido: {command}", "usage": USAGE}
        return _print(result, 0 if result.get("status") == "ok" else 1)
    except CashflowError as exc:
        payload = {"status": "error", "message": str(exc), **exc.extra}
        return _print(payload, 1)
    except KeyError as exc:
        return _print({"status": "error", "message": str(exc).strip("'")}, 1)
    except Exception as exc:  # pragma: no cover - fallback
        return _print({"status": "error", "message": str(exc)}, 1)


def main() -> None:
    sys.exit(_run())


if __name__ == "__main__":
    main()
