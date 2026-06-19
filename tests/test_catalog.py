"""Tests for catalog.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/financial-operator/scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog import (  # noqa: E402
    CATALOG_VERSION,
    INTENTS,
    get_intent,
    help_payload,
    hint_payload,
    serialize_intent,
)


class CatalogTests(unittest.TestCase):
    def test_all_intents_have_unique_names(self) -> None:
        names = [intent.name for intent in INTENTS]
        self.assertEqual(len(names), len(set(names)))

    def test_get_intent(self) -> None:
        self.assertIsNotNone(get_intent("list-accounts"))
        self.assertIsNone(get_intent("nope"))

    def test_help_payload_has_intents(self) -> None:
        payload = help_payload()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["version"], CATALOG_VERSION)
        self.assertEqual(len(payload["intents"]), len(INTENTS))
        self.assertIn("legacy_commands", payload)
        self.assertEqual(payload["helper"]["tool"], "terminal")
        self.assertIn("aurum_run", payload["forbidden_tools"])

    def test_hint_matches_list_accounts(self) -> None:
        result = hint_payload("listar contas débito crédito")
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(result["match"])
        assert result["match"] is not None
        self.assertEqual(result["match"]["intent"], "list-accounts")
        self.assertEqual(result["match"]["confidence"], "high")

    def test_hint_matches_record_transfer(self) -> None:
        result = hint_payload("transferi 50 reais da conta inter para carteira")
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(result["match"])
        assert result["match"] is not None
        self.assertEqual(result["match"]["intent"], "record-transfer")

    def test_hint_empty_query_errors(self) -> None:
        result = hint_payload("   ")
        self.assertEqual(result["status"], "error")

    def test_serialize_intent_includes_command(self) -> None:
        intent = get_intent("balances")
        assert intent is not None
        data = serialize_intent(intent)
        self.assertTrue(data["command"].endswith("aurum-run do balances"))


if __name__ == "__main__":
    unittest.main()
