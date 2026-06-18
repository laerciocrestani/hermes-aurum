"""Tests for aurum-run shell wrapper aliases."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AURUM_RUN = REPO_ROOT / "skills/financial-operator/scripts/aurum-run"


class AurumRunTests(unittest.TestCase):
    def test_accounts_alias_matches_ledger_accounts(self) -> None:
        direct = subprocess.run(
            ["bash", str(AURUM_RUN), "ledger", "accounts"],
            text=True,
            capture_output=True,
            check=False,
        )
        alias = subprocess.run(
            ["bash", str(AURUM_RUN), "accounts"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(alias.returncode, 0, alias.stderr)
        self.assertEqual(json.loads(direct.stdout), json.loads(alias.stdout))

    def test_categories_alias_matches_ledger_categories(self) -> None:
        direct = subprocess.run(
            ["bash", str(AURUM_RUN), "ledger", "categories"],
            text=True,
            capture_output=True,
            check=False,
        )
        alias = subprocess.run(
            ["bash", str(AURUM_RUN), "categories"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(alias.returncode, 0, alias.stderr)
        self.assertEqual(json.loads(direct.stdout), json.loads(alias.stdout))

    def test_hint_returns_list_accounts(self) -> None:
        result = subprocess.run(
            ["bash", str(AURUM_RUN), "hint", "listar contas débito crédito"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["match"]["intent"], "list-accounts")

    def test_help_json_lists_intents(self) -> None:
        result = subprocess.run(
            ["bash", str(AURUM_RUN), "help", "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(len(data["intents"]), 8)

    def test_do_list_accounts(self) -> None:
        result = subprocess.run(
            ["bash", str(AURUM_RUN), "do", "list-accounts"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "ok")
        self.assertIn("debit", data)
        self.assertIn("credit", data)

    def test_unknown_command_suggests_hint(self) -> None:
        result = subprocess.run(
            ["bash", str(AURUM_RUN), "nope"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        data = json.loads(result.stderr)
        self.assertEqual(data["status"], "error")
        self.assertIn("hint", data["suggestion"])


if __name__ == "__main__":
    unittest.main()
