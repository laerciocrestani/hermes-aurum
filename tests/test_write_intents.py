"""Tests for v1.4.1 write intents (transfer, mixed, add-category)."""

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

from do import (  # noqa: E402
    handle_add_category,
    handle_record_mixed_expense,
    handle_record_transfer,
)


def _paths_in(root: Path) -> dict:
    refs = root / "references"
    refs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "references/ledger.seed.jsonl", refs / "ledger.seed.jsonl")
    shutil.copy2(REPO_ROOT / "references/categories.json", refs / "categories.json")
    return {
        "profile_root": root,
        "hermes_home": root,
        "seed": refs / "ledger.seed.jsonl",
        "ledger": root / "data" / "ledger.jsonl",
        "categories": refs / "categories.json",
    }


class WriteIntentTests(unittest.TestCase):
    def test_record_transfer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_in(Path(tmp))
            result = handle_record_transfer(
                paths,
                json.dumps(
                    {
                        "from": "Banco Inter",
                        "to": "Carteira",
                        "amount": 50,
                        "description": "Saque",
                    }
                ),
            )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["event"]["type"], "transfer")
        self.assertEqual(result["balances"]["balances"]["Banco Inter"], -50.0)
        self.assertEqual(result["balances"]["balances"]["Carteira"], 50.0)

    def test_record_mixed_expense(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_in(Path(tmp))
            result = handle_record_mixed_expense(
                paths,
                json.dumps(
                    {
                        "category": "Vestuário",
                        "description": "Roupas",
                        "parts": [
                            {"amount": 100, "account": "Carteira"},
                            {"amount": 900, "account": "Inter Cartão de Crédito", "installments": 9},
                        ],
                    }
                ),
            )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["part_count"], 2)
        self.assertEqual(len(result["events"]), 2)

    def test_add_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths_in(Path(tmp))
            result = handle_add_category(
                paths,
                json.dumps({"name": "Pets", "kind": "expense"}),
            )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["added"], "Pets")
        self.assertIn("Pets", result["categories"]["expense"])


if __name__ == "__main__":
    unittest.main()
