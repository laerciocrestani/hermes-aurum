"""Contas mensais, parcelamentos e cobranças futuras."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from helpers import make_workspace

from catalog import load_catalog
from engine import apply_text, upcoming
from parse import parse_message
from schedule import load_obligations, split_installments


TODAY = date(2026, 8, 14)


class ScheduleParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_workspace(Path(self.tmp.name))
        self.catalog = load_catalog(self.paths)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_installment_purchase(self) -> None:
        parsed = parse_message(
            "compra de 1000 no cartão de crédito banco inter em 5x",
            self.catalog,
            TODAY,
        )
        self.assertEqual(parsed.action, "add")
        self.assertEqual(parsed.target, "schedule")
        self.assertEqual(parsed.kind, "installment")
        self.assertEqual(parsed.amount, 1000.0)
        self.assertEqual(parsed.installments, 5)
        self.assertEqual(parsed.account, "Banco Inter")
        self.assertEqual(parsed.method, "credito")

    def test_monthly_water_bill(self) -> None:
        parsed = parse_message(
            "Conta de água 80 reais todo mês dia 10 no Inter",
            self.catalog,
            TODAY,
        )
        self.assertEqual(parsed.action, "add")
        self.assertEqual(parsed.target, "schedule")
        self.assertEqual(parsed.kind, "recurring")
        self.assertEqual(parsed.amount, 80.0)
        self.assertEqual(parsed.due_day, 10)
        self.assertEqual(parsed.description, "Água")
        self.assertEqual(parsed.category, "Moradia")
        self.assertEqual(parsed.account, "Banco Inter")

    def test_paying_bill_stays_cashflow(self) -> None:
        parsed = parse_message("Paguei a luz 150 reais no Inter", self.catalog, TODAY)
        self.assertEqual(parsed.target, "entry")
        self.assertEqual(parsed.action, "add")
        self.assertEqual(parsed.description, "Luz")


class ScheduleEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_workspace(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_add_installment_projects_five_charges(self) -> None:
        result = apply_text(
            self.paths,
            "compra de 1000 no cartão de crédito banco inter em 5x",
            today=TODAY,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["action"], "add_installment")
        obligation = result["obligation"]
        self.assertEqual(obligation["total"], 1000.0)
        self.assertEqual(obligation["installments"], 5)
        self.assertEqual(obligation["amount"], 200.0)
        self.assertEqual(obligation["method"], "credito")
        self.assertEqual(len(result["charges"]), 5)
        self.assertEqual(result["charges"][0]["date"], "2026-08-14")
        self.assertEqual(result["charges"][-1]["date"], "2026-12-14")
        self.assertEqual(result["charges"][0]["description"], "Compra 1/5")

    def test_monthly_bills_crud(self) -> None:
        agua = apply_text(
            self.paths,
            "Conta de água 80 reais todo mês dia 10 no Inter",
            today=TODAY,
        )
        self.assertEqual(agua["action"], "add_recurring")
        apply_text(self.paths, "Conta de luz 150 por mês dia 12", today=TODAY)
        apply_text(self.paths, "telefone 50 reais mensal no Inter", today=TODAY)

        edited = apply_text(self.paths, "Muda a água para 90", today=TODAY)
        self.assertEqual(edited["status"], "ok")
        self.assertEqual(edited["obligation"]["amount"], 90.0)
        self.assertEqual(edited["obligation"]["description"], "Água")

        removed = apply_text(self.paths, "Apaga a conta de luz", today=TODAY)
        self.assertEqual(removed["status"], "ok")
        self.assertEqual(removed["obligation"]["description"], "Luz")

        remaining = load_obligations(self.paths.schedule)
        names = {item["description"] for item in remaining}
        self.assertIn("Água", names)
        self.assertIn("Telefone", names)
        self.assertNotIn("Luz", names)

    def test_upcoming_lists_open_charges(self) -> None:
        apply_text(self.paths, "Conta de água 80 reais todo mês dia 20 no Inter", today=TODAY)
        apply_text(
            self.paths,
            "compra de 1000 no cartão de crédito banco inter em 5x",
            today=TODAY,
        )
        result = upcoming(self.paths, today=TODAY, months=6)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["count"], 6)
        descriptions = {row["description"] for row in result["charges"]}
        self.assertIn("Água", descriptions)
        self.assertIn("Compra 1/5", descriptions)
        self.assertIn("Compra 5/5", descriptions)

    def test_cancel_installments(self) -> None:
        apply_text(
            self.paths,
            "compra de 1000 no cartão de crédito banco inter em 5x",
            today=TODAY,
        )
        result = apply_text(self.paths, "Cancela a compra em 5x", today=TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["obligation"]["total"], 1000.0)
        self.assertEqual(load_obligations(self.paths.schedule), [])

    def test_split_remainder_on_last_parcel(self) -> None:
        amounts = split_installments(1000, 3)
        self.assertEqual(sum(amounts), 1000.0)
        self.assertEqual(amounts[-1], 333.34)


if __name__ == "__main__":
    unittest.main()
