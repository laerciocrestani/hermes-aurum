"""Cadastro de contas débito/crédito e saldo da carteira."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from helpers import make_workspace

from catalog import find_account, load_catalog
from engine import apply_text, list_accounts
from parse import parse_message


TODAY = date(2026, 8, 14)


class AccountParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_workspace(Path(self.tmp.name))
        self.catalog = load_catalog(self.paths)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parse_debit_with_initial_balance(self) -> None:
        parsed = parse_message(
            "Nova conta débito Itaú com saldo de 1500",
            self.catalog,
            TODAY,
        )
        self.assertEqual(parsed.target, "account")
        self.assertEqual(parsed.kind, "debit")
        self.assertEqual(parsed.account, "Itaú")
        self.assertEqual(parsed.initial_balance, 1500.0)

    def test_parse_credit_card_cycle(self) -> None:
        parsed = parse_message(
            "Novo cartão Inter, fecha dia 19, fatura dia 25",
            self.catalog,
            TODAY,
        )
        self.assertEqual(parsed.target, "account")
        self.assertEqual(parsed.kind, "credit")
        self.assertEqual(parsed.account, "Banco Inter")
        self.assertEqual(parsed.closing_day, 19)
        self.assertEqual(parsed.due_day, 25)


class AccountEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_workspace(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_debit_requires_initial_balance(self) -> None:
        result = apply_text(self.paths, "Nova conta débito Itaú", today=TODAY)
        self.assertEqual(result["status"], "error")
        self.assertIn("saldo inicial", result["message"].lower())
        self.assertIn("initial_balance", result.get("missing", []))

    def test_credit_requires_closing_and_due(self) -> None:
        result = apply_text(self.paths, "Novo cartão Inter, fecha dia 19", today=TODAY)
        self.assertEqual(result["status"], "error")
        self.assertIn("fechamento", result["message"].lower())

    def test_debit_initial_balance_feeds_wallet(self) -> None:
        created = apply_text(
            self.paths,
            "Nova conta débito Itaú com saldo de 1500",
            today=TODAY,
        )
        self.assertEqual(created["status"], "ok")
        self.assertEqual(created["account"]["kind"], "debit")
        self.assertEqual(created["account"]["initial_balance"], 1500.0)
        self.assertEqual(created["account"]["balance"], 1500.0)

        apply_text(self.paths, "Gastei 30 reais no mercado no débito no Itaú", today=TODAY)
        listed = list_accounts(self.paths, today=TODAY)
        itau = next(row for row in listed["accounts"] if row["name"] == "Itaú")
        self.assertEqual(itau["balance"], 1470.0)

    def test_credit_card_stores_cycle_and_routes_installments(self) -> None:
        created = apply_text(
            self.paths,
            "Novo cartão Inter, fecha dia 19, fatura dia 25",
            today=TODAY,
        )
        self.assertEqual(created["status"], "ok")
        self.assertEqual(created["account"]["name"], "Banco Inter Cartão")
        self.assertEqual(created["account"]["closing_day"], 19)
        self.assertEqual(created["account"]["due_day"], 25)

        catalog = load_catalog(self.paths)
        card = find_account(catalog, "Banco Inter Cartão")
        self.assertIsNotNone(card)
        self.assertEqual(card.kind, "credit")

        purchase = apply_text(
            self.paths,
            "compra de 1000 no cartão de crédito banco inter em 5x",
            today=TODAY,
        )
        self.assertEqual(purchase["obligation"]["account"], "Banco Inter Cartão")
        self.assertEqual(purchase["obligation"]["due_day"], 25)
        self.assertEqual(purchase["charges"][0]["date"], "2026-08-25")


if __name__ == "__main__":
    unittest.main()
