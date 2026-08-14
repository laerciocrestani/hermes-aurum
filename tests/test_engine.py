"""Store e motor do fluxo de caixa."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from helpers import make_workspace

from engine import apply_text, edit_by_id, list_entries
from store import load_entries


TODAY = date(2026, 8, 14)


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_workspace(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_apply_example_adds_categorized_expense(self) -> None:
        result = apply_text(
            self.paths,
            "Gastei 30 reias em mercado no debito com o banco inter.",
            today=TODAY,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["action"], "add")
        entry = result["entry"]
        self.assertEqual(entry["type"], "expense")
        self.assertEqual(entry["amount"], 30.0)
        self.assertEqual(entry["category"], "Alimentação")
        self.assertEqual(entry["account"], "Banco Inter")
        self.assertEqual(entry["method"], "debito")
        self.assertEqual(entry["description"], "Mercado")
        self.assertEqual(entry["date"], "2026-08-14")
        self.assertTrue(entry["id"].startswith("cf_"))

        listed = list_entries(self.paths, date_value="2026-08-14")
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["totals"]["expense"], 30.0)

    def test_remove_last(self) -> None:
        apply_text(self.paths, "Gastei 10 reais no mercado no Inter", today=TODAY)
        apply_text(self.paths, "Gastei 20 reais de uber no Nubank", today=TODAY)
        result = apply_text(self.paths, "Apaga o último lançamento", today=TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entry"]["amount"], 20.0)
        remaining = load_entries(self.paths.cashflow)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["amount"], 10.0)

    def test_remove_by_amount_and_category(self) -> None:
        apply_text(self.paths, "Gastei 30 reais no mercado no Inter", today=TODAY)
        apply_text(self.paths, "Gastei 50 reais de uber no Inter", today=TODAY)
        result = apply_text(self.paths, "Remove o gasto de 30 reais no mercado", today=TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entry"]["amount"], 30.0)
        remaining = load_entries(self.paths.cashflow)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["amount"], 50.0)

    def test_edit_last_amount(self) -> None:
        apply_text(self.paths, "Gastei 30 reais no mercado no Inter", today=TODAY)
        result = apply_text(self.paths, "Corrige o valor para 35", today=TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entry"]["amount"], 35.0)
        self.assertEqual(result["entry"]["category"], "Alimentação")

    def test_edit_old_and_new_amount(self) -> None:
        apply_text(self.paths, "Gastei 30 reais no mercado no Inter", today=TODAY)
        apply_text(self.paths, "Gastei 80 reais de uber no Nubank", today=TODAY)
        result = apply_text(self.paths, "Na verdade foi 35, não 30", today=TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entry"]["amount"], 35.0)
        self.assertEqual(result["entry"]["description"], "Mercado")

    def test_edit_by_id(self) -> None:
        created = apply_text(self.paths, "Gastei 12 reais no mercado no Inter", today=TODAY)
        updated = edit_by_id(self.paths, created["entry"]["id"], {"amount": 15})
        self.assertEqual(updated["entry"]["amount"], 15)

    def test_unknown_message(self) -> None:
        result = apply_text(self.paths, "Qual o sentido da vida?", today=TODAY)
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
