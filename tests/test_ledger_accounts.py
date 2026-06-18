"""Tests for ledger.py accounts output (debit/credit grouping)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills/financial-operator/scripts"
sys.path.insert(0, str(SCRIPTS))

from ledger import cmd_accounts  # noqa: E402


class LedgerAccountsTests(unittest.TestCase):
    def test_accounts_groups_debit_and_credit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = root / "references"
            data = root / "data"
            refs.mkdir()
            data.mkdir()
            shutil.copy2(REPO_ROOT / "references/ledger.seed.jsonl", refs / "ledger.seed.jsonl")
            ledger = data / "ledger.jsonl"
            ledger.write_text(
                "\n".join(
                    [
                        '{"type":"account","name":"Banco Inter","kind":"asset"}',
                        '{"type":"account","name":"Inter Cartão","kind":"liability","credit_limit":10000,"closing_day":10,"due_day":17}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            paths = {
                "profile_root": root,
                "hermes_home": root,
                "seed": refs / "ledger.seed.jsonl",
                "ledger": ledger,
            }

            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_accounts(paths)
            payload = json.loads(buf.getvalue())

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["account_count"], 2)
            self.assertEqual(payload["debit"], ["Banco Inter"])
            self.assertEqual(payload["credit"], ["Inter Cartão"])

    def test_accounts_bootstraps_from_seed_when_ledger_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = root / "references"
            refs.mkdir()
            seed = refs / "ledger.seed.jsonl"
            shutil.copy2(REPO_ROOT / "references/ledger.seed.jsonl", seed)
            paths = {
                "profile_root": root,
                "hermes_home": root,
                "seed": seed,
                "ledger": root / "data" / "ledger.jsonl",
            }

            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_accounts(paths)
            payload = json.loads(buf.getvalue())

            self.assertEqual(payload["account_count"], 4)
            self.assertEqual(payload["debit"], ["Banco Inter", "Carteira", "Nubank"])
            self.assertEqual(payload["credit"], ["Inter Cartão de Crédito"])
            self.assertTrue(paths["ledger"].is_file())


if __name__ == "__main__":
    unittest.main()
