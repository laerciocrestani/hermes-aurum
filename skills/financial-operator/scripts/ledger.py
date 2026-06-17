#!/usr/bin/env python3
"""Ledger JSONL append-only do Aurum."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from credit_card import BILLING_PROFILES, build_account_registry, is_credit_card
from paths import get_paths, known_ledger_paths, resolve_profile_root, resolve_hermes_home, find_references_dir

EVENT_TYPES = {
    "account",
    "account_config",
    "expense",
    "income",
    "transfer",
    "investment",
    "liability",
    "adjustment",
}

CONFIG_FIELDS = ("credit_limit", "closing_day", "due_day", "billing_profile")


def append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_events(ledger_path: Path) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with open(ledger_path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido na linha {lineno}: {exc}") from exc
    return events


def scan_ledger(ledger_path: Path) -> dict[str, Any]:
    """Valida cada linha sem abortar no primeiro erro."""
    if not ledger_path.exists():
        return {
            "path": str(ledger_path),
            "exists": False,
            "line_count": 0,
            "valid_count": 0,
            "errors": [],
            "valid_events": [],
        }

    errors: list[dict[str, Any]] = []
    valid_events: list[dict[str, Any]] = []
    line_count = 0

    with open(ledger_path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            line_count += 1
            try:
                valid_events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append(
                    {
                        "line": lineno,
                        "error": str(exc),
                        "preview": line[:120],
                    }
                )

    return {
        "path": str(ledger_path),
        "exists": True,
        "line_count": line_count,
        "valid_count": len(valid_events),
        "errors": errors,
        "valid_events": valid_events,
    }


def load_categories(categories_path: Path) -> dict[str, set[str]]:
    with open(categories_path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: set(v) for k, v in data.items()}


def account_names(events: list[dict[str, Any]]) -> set[str]:
    return {e["name"] for e in events if e.get("type") == "account" and "name" in e}


def validate_day_field(value: Any, field_name: str) -> None:
    if not isinstance(value, int) or not 1 <= value <= 31:
        raise ValueError(f"{field_name} deve ser inteiro entre 1 e 31")


def validate_card_config_fields(event: dict[str, Any], *, require_all: bool = False) -> None:
    present = [key for key in CONFIG_FIELDS if key in event]
    if require_all and len(present) < len(CONFIG_FIELDS):
        raise ValueError("conta liability exige credit_limit, closing_day, due_day")
    if not present:
        return

    if "credit_limit" in event:
        limit = event["credit_limit"]
        if not isinstance(limit, (int, float)) or limit <= 0:
            raise ValueError("credit_limit deve ser > 0")
    if "closing_day" in event:
        validate_day_field(event["closing_day"], "closing_day")
    if "due_day" in event:
        validate_day_field(event["due_day"], "due_day")
    if "billing_profile" in event:
        profile = event["billing_profile"]
        if profile not in BILLING_PROFILES:
            raise ValueError(f"billing_profile deve ser um de: {', '.join(sorted(BILLING_PROFILES))}")


def init_ledger(ledger_path: Path, seed_path: Path) -> None:
    if ledger_path.exists():
        return
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not seed_path.exists():
        raise FileNotFoundError(f"Arquivo seed não encontrado: {seed_path}")
    shutil.copy2(seed_path, ledger_path)


def validate_event(
    event: dict[str, Any],
    events: list[dict[str, Any]],
    categories: dict[str, set[str]],
) -> None:
    etype = event.get("type")
    if etype not in EVENT_TYPES:
        raise ValueError(f"Tipo de evento desconhecido: {etype}")

    accounts = account_names(events)
    registry = build_account_registry(events)

    if etype == "account":
        name = event.get("name")
        if not name:
            raise ValueError("evento account exige 'name'")
        if name in accounts:
            raise ValueError(f"Conta já existe: {name}")
        kind = event.get("kind")
        if kind not in ("asset", "liability"):
            raise ValueError("kind da conta deve ser 'asset' ou 'liability'")
        if kind == "liability":
            validate_card_config_fields(event)
        elif any(key in event for key in CONFIG_FIELDS):
            raise ValueError("campos de config de cartão exigem kind 'liability'")
        return

    if etype == "account_config":
        account = event.get("account")
        if not account:
            raise ValueError("account_config exige 'account'")
        if account not in accounts:
            raise ValueError(f"Conta não encontrada: {account}")
        if registry.get(account) and registry[account].kind != "liability":
            raise ValueError("account_config só se aplica a contas liability")
        config_present = [key for key in CONFIG_FIELDS if key in event]
        if not config_present:
            raise ValueError("account_config exige ao menos um campo de config")
        validate_card_config_fields(event)
        return

    if etype in ("expense", "income"):
        account = event.get("account")
        category = event.get("category")
        amount = event.get("amount")
        if account not in accounts:
            raise ValueError(f"Conta não encontrada: {account}")
        if etype == "expense":
            pool = categories.get("expense", set())
        else:
            pool = categories.get("income", set())
        if category not in pool:
            raise ValueError(f"Categoria inválida '{category}' para {etype}")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError(f"valor de {etype} deve ser > 0")
        if etype == "expense" and is_credit_card(registry, account):
            installments = event.get("installments", 1)
            if not isinstance(installments, int) or installments < 1:
                raise ValueError("installments deve ser inteiro >= 1")
            profile = registry[account].billing_profile or "br"
            if profile == "simple" and installments > 1:
                raise ValueError("installments > 1 exige billing_profile 'br'")
            if registry[account].closing_day is None:
                raise ValueError(f"Cartão de crédito '{account}' exige closing_day em account_config")
        return

    if etype == "transfer":
        src, dst, amount = event.get("from"), event.get("to"), event.get("amount")
        if src not in accounts:
            raise ValueError(f"Conta não encontrada: {src}")
        if dst not in accounts:
            raise ValueError(f"Conta não encontrada: {dst}")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("valor de transferência deve ser > 0")
        return

    if etype == "investment":
        account, amount = event.get("account"), event.get("amount")
        if account not in accounts:
            raise ValueError(f"Conta não encontrada: {account}")
        if not event.get("asset"):
            raise ValueError("investment exige 'asset'")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("valor de investment deve ser > 0")
        return

    if etype == "adjustment":
        account, amount, reason = event.get("account"), event.get("amount"), event.get("reason")
        if account not in accounts:
            raise ValueError(f"Conta não encontrada: {account}")
        if not isinstance(amount, (int, float)) or amount == 0:
            raise ValueError("valor de adjustment deve ser diferente de zero")
        if not reason:
            raise ValueError("adjustment exige 'reason'")
        return

    if etype == "liability":
        if not event.get("name"):
            raise ValueError("liability exige 'name'")
        amount = event.get("amount")
        if not isinstance(amount, (int, float)):
            raise ValueError("liability exige 'amount' numérico")


def cmd_init(paths: dict[str, Path]) -> None:
    init_ledger(paths["ledger"], paths["seed"])
    print(json.dumps({"status": "ok", "ledger": str(paths["ledger"])}))


def read_append_json(arg: str) -> str:
    """Read JSON from arg or stdin when arg is '-'."""
    if arg == "-":
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("Nenhum JSON no stdin")
        return raw
    return arg


def cmd_append(paths: dict[str, Path], raw_json: str) -> None:
    init_ledger(paths["ledger"], paths["seed"])
    try:
        event = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc

    events = load_events(paths["ledger"])
    categories = load_categories(paths["categories"])
    validate_event(event, events, categories)
    append_line(paths["ledger"], json.dumps(event, ensure_ascii=False))
    print(json.dumps({"status": "ok", "event": event}))


def cmd_list(paths: dict[str, Path], etype: str | None, month: str | None) -> None:
    events = load_events(paths["ledger"])
    if etype:
        events = [e for e in events if e.get("type") == etype]
    if month:
        events = [e for e in events if e.get("date", "").startswith(month)]
    print(json.dumps(events, ensure_ascii=False, indent=2))


def cmd_accounts(paths: dict[str, Path]) -> None:
    events = load_events(paths["ledger"])
    registry = build_account_registry(events)
    result = []
    for name in sorted(account_names(events)):
        info = registry.get(name)
        entry: dict[str, Any] = {"name": name, "kind": info.kind if info else "asset"}
        if info and info.kind == "liability":
            for key in CONFIG_FIELDS:
                value = getattr(info, key, None)
                if value is not None:
                    entry[key] = value
        result.append(entry)
    print(json.dumps({"accounts": result}, ensure_ascii=False, indent=2))


def cmd_check(paths: dict[str, Path]) -> None:
    from paths import resolve_ledger_path, resolve_profile_root, resolve_hermes_home, find_references_dir

    refs = find_references_dir()
    profile_root = resolve_profile_root(refs)
    hermes_home = resolve_hermes_home(profile_root)
    active = paths["ledger"]

    candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in [
        active,
        hermes_home / "data" / "ledger.jsonl",
        profile_root / "data" / "ledger.jsonl",
    ]:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        candidates.append(resolved)

    scans = []
    for p in candidates:
        s = scan_ledger(p)
        s.pop("valid_events", None)
        scans.append(s)
    active_scan = next((s for s in scans if Path(s["path"]) == active.resolve()), None)
    if active_scan is None:
        s = scan_ledger(active)
        s.pop("valid_events", None)
        active_scan = s

    result = {
        "status": "ok" if not active_scan["errors"] else "corrupt",
        "ledger": active_scan,
        "hermes_home": str(hermes_home),
        "profile_root": str(profile_root),
        "other_locations": [s for s in scans if Path(s["path"]) != active.resolve()],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_repair(paths: dict[str, Path], *, dry_run: bool) -> None:
    ledger_path = paths["ledger"]
    scan = scan_ledger(ledger_path)

    if not scan["exists"]:
        raise FileNotFoundError(f"Ledger não encontrado: {ledger_path}")

    if not scan["errors"]:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "message": "Nenhuma linha inválida — reparo não necessário",
                    "path": str(ledger_path),
                    "valid_count": scan["valid_count"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    backup_path = ledger_path.with_suffix(".jsonl.bak")
    if not dry_run:
        shutil.copy2(ledger_path, backup_path)
        with open(ledger_path, "w", encoding="utf-8") as f:
            for event in scan["valid_events"]:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    print(
        json.dumps(
            {
                "status": "ok" if not dry_run else "dry_run",
                "path": str(ledger_path),
                "backup": str(backup_path) if not dry_run else None,
                "removed_lines": len(scan["errors"]),
                "kept_events": scan["valid_count"],
                "errors": scan["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_reset(paths: dict[str, Path], *, confirm: bool) -> None:
    if not confirm:
        raise ValueError("Reset destrutivo — confirme com --confirm")

    profile_root = paths["profile_root"]
    hermes_home = paths["hermes_home"]
    target = (profile_root / "data" / "ledger.jsonl").resolve()
    seed = paths["seed"]
    if not seed.is_file():
        raise FileNotFoundError(f"Arquivo seed não encontrado: {seed}")

    backups: list[str] = []
    removed: list[str] = []

    for ledger_path in known_ledger_paths(profile_root, hermes_home):
        if ledger_path.is_file():
            stamp = ledger_path.name + ".bak.reset"
            backup_path = ledger_path.with_name(stamp)
            shutil.copy2(ledger_path, backup_path)
            backups.append(str(backup_path))
            ledger_path.unlink()
            removed.append(str(ledger_path))

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(seed, target)

    print(
        json.dumps(
            {
                "status": "ok",
                "message": "Ledger zerado a partir do seed",
                "ledger": str(target),
                "seed": str(seed),
                "backups": backups,
                "removed": removed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Ledger append-only do Aurum")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    p_append = sub.add_parser("append")
    p_append.add_argument(
        "json",
        help='String JSON do evento, ou "-" para ler um objeto JSON do stdin',
    )

    p_list = sub.add_parser("list")
    p_list.add_argument("--type", dest="etype")
    p_list.add_argument("--month")

    sub.add_parser("accounts")

    sub.add_parser("check")
    p_repair = sub.add_parser("repair")
    p_repair.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria removido sem alterar o arquivo",
    )

    p_reset = sub.add_parser("reset")
    p_reset.add_argument(
        "--confirm",
        action="store_true",
        help="Apaga ledgers conhecidos e recria do seed (faz backup .bak.reset)",
    )

    args = parser.parse_args()
    paths = get_paths()

    try:
        if args.command == "init":
            cmd_init(paths)
        elif args.command == "append":
            cmd_append(paths, read_append_json(args.json))
        elif args.command == "list":
            cmd_list(paths, args.etype, args.month)
        elif args.command == "accounts":
            cmd_accounts(paths)
        elif args.command == "check":
            cmd_check(paths)
        elif args.command == "repair":
            cmd_repair(paths, dry_run=args.dry_run)
        elif args.command == "reset":
            cmd_reset(paths, confirm=args.confirm)
        return 0
    except (ValueError, FileNotFoundError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
