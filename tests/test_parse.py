"""Parser de mensagens do dia a dia."""

from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import make_workspace

from catalog import load_catalog
from parse import parse_message


TODAY = date(2026, 8, 14)


class ParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.paths = make_workspace(Path(self.tmp.name))
        self.catalog = load_catalog(self.paths)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_example_mercado_debito_inter(self) -> None:
        parsed = parse_message(
            "Gastei 30 reias em mercado no debito com o banco inter.",
            self.catalog,
            TODAY,
        )
        self.assertEqual(parsed.action, "add")
        self.assertEqual(parsed.entry_type, "expense")
        self.assertEqual(parsed.amount, 30.0)
        self.assertEqual(parsed.category, "Alimentação")
        self.assertEqual(parsed.account, "Banco Inter")
        self.assertEqual(parsed.method, "debito")
        self.assertEqual(parsed.description, "Mercado")
        self.assertIsNone(parsed.date)

    def test_receita_salario(self) -> None:
        parsed = parse_message("Recebi 5000 reais de salário no Inter", self.catalog, TODAY)
        self.assertEqual(parsed.action, "add")
        self.assertEqual(parsed.entry_type, "income")
        self.assertEqual(parsed.category, "Salário")
        self.assertEqual(parsed.account, "Banco Inter")

    def test_remove_ultimo(self) -> None:
        parsed = parse_message("Apaga o último lançamento", self.catalog, TODAY)
        self.assertEqual(parsed.action, "remove")
        self.assertTrue(parsed.last)

    def test_edit_valor(self) -> None:
        parsed = parse_message("Corrige o valor para 35", self.catalog, TODAY)
        self.assertEqual(parsed.action, "edit")
        self.assertEqual(parsed.fields.get("amount"), 35.0)
        self.assertTrue(parsed.last)

    def test_edit_nao_foi(self) -> None:
        parsed = parse_message("Na verdade foi 35, não 30", self.catalog, TODAY)
        self.assertEqual(parsed.action, "edit")
        self.assertEqual(parsed.amount, 30.0)
        self.assertEqual(parsed.fields.get("amount"), 35.0)

    def test_ontem(self) -> None:
        parsed = parse_message("Gastei 12 reais de uber ontem no Nubank", self.catalog, TODAY)
        self.assertEqual(parsed.date, "2026-08-13")
        self.assertEqual(parsed.category, "Transporte")
        self.assertEqual(parsed.account, "Nubank")
        self.assertEqual(parsed.description, "Uber")


if __name__ == "__main__":
    unittest.main()
