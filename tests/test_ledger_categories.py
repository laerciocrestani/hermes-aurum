"""Tests for ledger.py categories subcommand."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "skills/financial-operator/scripts/ledger.py"


class LedgerCategoriesTests(unittest.TestCase):
    def test_categories_lists_expense_and_income(self) -> None:
        result = subprocess.run(
            [sys.executable, str(LEDGER), "categories"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("Alimentação", data["categories"]["expense"])
        self.assertIn("Salário", data["categories"]["income"])
        self.assertTrue(data["path"].endswith("references/categories.json"))


if __name__ == "__main__":
    unittest.main()
