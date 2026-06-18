"""Tests for do.py intent dispatcher."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/financial-operator/scripts"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from do import handle_list_accounts, handle_preflight, run_intent  # noqa: E402


def _paths_in(root: Path, *, with_ledger: bool = False) -> dict:
    refs = root / "references"
    refs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "references/ledger.seed.jsonl", refs / "ledger.seed.jsonl")
    shutil.copy2(REPO_ROOT / "references/categories.json", refs / "categories.json")
    ledger = root / "data" / "ledger.jsonl"
    if with_ledger:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(refs / "ledger.seed.jsonl", ledger)
    return {
        "profile_root": root,
        "hermes_home": root,
        "seed": refs / "ledger.seed.jsonl",
        "ledger": ledger,
        "categories": refs / "categories.json",
    }


class DoTests(unittest.TestCase):
    def test_run_unknown_intent_returns_suggestion(self) -> None:
        result = run_intent("not-real", [])
        self.assertEqual(result["status"], "error")
        self.assertIn("suggestion", result)

    def test_list_accounts_bootstraps_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_list_accounts(_paths_in(Path(tmp)))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["account_count"], 4)
        self.assertEqual(result["debit"], ["Banco Inter", "Carteira", "Nubank"])
        self.assertEqual(result["credit"], ["Inter Cartão de Crédito"])

    def test_preflight_combines_accounts_and_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_preflight(_paths_in(Path(tmp), with_ledger=True))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["accounts"]["account_count"], 4)
        self.assertIn("Alimentação", result["categories"]["categories"]["expense"])


if __name__ == "__main__":
    unittest.main()
