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


if __name__ == "__main__":
    unittest.main()
