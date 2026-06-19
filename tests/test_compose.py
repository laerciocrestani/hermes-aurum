"""Tests for compose.py — natural language expense registration."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/financial-operator/scripts"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from compose import ComposeError, build_expense_payload, compose_payload, resolve_account  # noqa: E402
from do import handle_record_expense  # noqa: E402


def _paths_with_c6(root: Path) -> dict:
    refs = root / "references"
    refs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "references/categories.json", refs / "categories.json")
    seed = refs / "ledger.seed.jsonl"
    seed.write_text(
        "\n".join(
            [
                '{"type":"account","name":"Banco Inter","kind":"asset"}',
                '{"type":"account","name":"C6Bank","kind":"asset"}',
                '{"type":"account","name":"C6 Bank","kind":"liability","credit_limit":10000,"closing_day":1,"due_day":10,"billing_profile":"br"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "profile_root": root,
        "hermes_home": root,
        "seed": seed,
        "ledger": root / "data" / "ledger.jsonl",
        "categories": refs / "categories.json",
    }


class ComposeTests(unittest.TestCase):
    def test_resolve_c6_credit(self) -> None:
        accounts = [
            {"name": "C6Bank", "kind": "asset"},
            {"name": "C6 Bank", "kind": "liability"},
        ]
        name = resolve_account("C6bank crédito", accounts, "liability")
        self.assertEqual(name, "C6 Bank")

    def test_build_expense_installments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_with_c6(Path(tmp))
            payload = build_expense_payload("Gastei 33 reais no C6bank crédito em 3x", paths)
        self.assertEqual(payload["amount"], 33)
        self.assertEqual(payload["account"], "C6 Bank")
        self.assertEqual(payload["installments"], 3)
        self.assertEqual(payload["category"], "Outros")

    def test_compose_run_registers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_with_c6(Path(tmp))
            planned = compose_payload("Gastei 33 reais no C6bank crédito em 3x", paths)
            record = handle_record_expense(paths, json.dumps(planned["parsed"], ensure_ascii=False))
        self.assertEqual(planned["status"], "ok")
        self.assertEqual(planned["parsed"]["account"], "C6 Bank")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["intent"], "record-expense")

    def test_c6banck_typo_and_vestuario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_with_c6(Path(tmp))
            payload = build_expense_payload(
                "Gastei 70 reais no C6banck crédito em 3x vestuario hoje",
                paths,
            )
        self.assertEqual(payload["amount"], 70)
        self.assertEqual(payload["account"], "C6 Bank")
        self.assertEqual(payload["category"], "Vestuário")
        self.assertEqual(payload["installments"], 3)

    def test_compose_json_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_with_c6(Path(tmp))
            payload = build_expense_payload(
                '{"amount":70,"account":"C6 Bank","category":"Vestuário","installments":3}',
                paths,
            )
        self.assertEqual(payload["category"], "Vestuário")
        self.assertEqual(payload["installments"], 3)

    def test_compose_errors_without_card_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_with_c6(Path(tmp))
            # C6 Bank sem closing_day no seed — só kind liability
            paths["seed"].write_text(
                "\n".join(
                    [
                        '{"type":"account","name":"C6Bank","kind":"asset"}',
                        '{"type":"account","name":"C6 Bank","kind":"liability"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ComposeError) as ctx:
                build_expense_payload("Gastei 33 reais no C6bank crédito em 3x", paths)
        self.assertIn("closing_day", ctx.exception.extra["missing_fields"])
        self.assertIn("update-account", ctx.exception.extra["fix_command"])

    def test_compose_without_run_returns_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_with_c6(Path(tmp))
            result = compose_payload("Gastei 10 reais no Inter débito", paths)
        self.assertEqual(result["status"], "ok")
        self.assertIn("record-expense", result["command"])
        self.assertEqual(result["parsed"]["account"], "Banco Inter")


if __name__ == "__main__":
    unittest.main()
