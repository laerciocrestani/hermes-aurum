"""Tests for credit card billing and ledger validation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "financial-operator" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from credit_card import (  # noqa: E402
    apply_card_expense,
    apply_card_payment,
    build_account_registry,
    installment_schedule,
    split_installments,
)
from ledger import load_categories, validate_event  # noqa: E402
from rebuild_state import rebuild  # noqa: E402
from reports import monthly_report  # noqa: E402


def card_account_events() -> list[dict]:
    return [
        {
            "type": "account",
            "name": "Inter Cartão de Crédito",
            "kind": "liability",
            "credit_limit": 26800,
            "closing_day": 19,
            "due_day": 25,
        },
        {"type": "account", "name": "Banco Inter", "kind": "asset"},
    ]


class CreditCardLogicTests(unittest.TestCase):
    def test_split_installments(self) -> None:
        self.assertEqual(split_installments(150, 3), [50.0, 50.0, 50.0])

    def test_installment_schedule_before_closing(self) -> None:
        schedule = installment_schedule(date(2026, 6, 15), 19, 150, 3)
        self.assertEqual(
            schedule,
            [("2026-06", 50.0), ("2026-07", 50.0), ("2026-08", 50.0)],
        )

    def test_installment_schedule_after_closing(self) -> None:
        schedule = installment_schedule(date(2026, 6, 20), 19, 150, 3)
        self.assertEqual(
            schedule,
            [("2026-07", 50.0), ("2026-08", 50.0), ("2026-09", 50.0)],
        )


class LedgerValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        categories_path = Path(__file__).resolve().parents[1] / "references" / "categories.json"
        self.categories = load_categories(categories_path)
        self.events = card_account_events()

    def test_account_config_valid(self) -> None:
        event = {
            "type": "account_config",
            "account": "Inter Cartão de Crédito",
            "credit_limit": 30000,
        }
        validate_event(event, self.events, self.categories)

    def test_installments_rejected_on_simple_profile(self) -> None:
        events = self.events + [
            {
                "type": "account_config",
                "account": "Inter Cartão de Crédito",
                "billing_profile": "simple",
            }
        ]
        event = {
            "type": "expense",
            "date": "2026-06-15",
            "account": "Inter Cartão de Crédito",
            "category": "Alimentação",
            "amount": 150,
            "installments": 3,
        }
        with self.assertRaisesRegex(ValueError, "billing_profile 'br'"):
            validate_event(event, events, self.categories)

    def test_expense_requires_closing_day(self) -> None:
        events = [
            {"type": "account", "name": "Card", "kind": "liability"},
        ]
        event = {
            "type": "expense",
            "date": "2026-06-15",
            "account": "Card",
            "category": "Alimentação",
            "amount": 50,
        }
        with self.assertRaisesRegex(ValueError, "closing_day"):
            validate_event(event, events, self.categories)


class RebuildStateTests(unittest.TestCase):
    def test_installment_committed_and_statements(self) -> None:
        events = card_account_events() + [
            {
                "type": "expense",
                "date": "2026-06-15",
                "account": "Inter Cartão de Crédito",
                "category": "Other",
                "amount": 150,
                "installments": 3,
            }
        ]
        state = rebuild(events, as_of=date(2026, 6, 18))
        card = state["credit_cards"]["Inter Cartão de Crédito"]
        self.assertEqual(card["committed"], 150)
        self.assertEqual(card["balance"], 0)
        self.assertEqual(card["available_credit"], 26650)

        state_closed = rebuild(events, as_of=date(2026, 6, 20))
        card_closed = state_closed["credit_cards"]["Inter Cartão de Crédito"]
        self.assertEqual(card_closed["balance"], 50)

    def test_payment_releases_committed(self) -> None:
        events = card_account_events() + [
            {
                "type": "expense",
                "date": "2026-06-15",
                "account": "Inter Cartão de Crédito",
                "category": "Other",
                "amount": 150,
                "installments": 3,
            },
            {
                "type": "transfer",
                "date": "2026-06-25",
                "from": "Banco Inter",
                "to": "Inter Cartão de Crédito",
                "amount": 50,
            },
        ]
        state = rebuild(events, as_of=date(2026, 6, 26))
        card = state["credit_cards"]["Inter Cartão de Crédito"]
        self.assertEqual(card["balance"], 0)
        self.assertEqual(card["committed"], 100)
        self.assertEqual(card["available_credit"], 26700)

    def test_asset_expense_unchanged(self) -> None:
        events = card_account_events() + [
            {
                "type": "expense",
                "date": "2026-06-10",
                "account": "Banco Inter",
                "category": "Alimentação",
                "amount": 40,
            }
        ]
        state = rebuild(events)
        self.assertEqual(state["balances"]["Banco Inter"], -40)
        self.assertEqual(state["credit_cards"]["Inter Cartão de Crédito"]["balance"], 0)


class ReportsTests(unittest.TestCase):
    def test_installment_spread_across_months(self) -> None:
        events = card_account_events() + [
            {
                "type": "expense",
                "date": "2026-06-15",
                "account": "Inter Cartão de Crédito",
                "category": "Other",
                "amount": 150,
                "installments": 3,
            }
        ]
        june = monthly_report(events, "2026-06")
        july = monthly_report(events, "2026-07")
        august = monthly_report(events, "2026-08")
        self.assertEqual(june["total_expense"], 50)
        self.assertEqual(july["total_expense"], 50)
        self.assertEqual(august["total_expense"], 50)


if __name__ == "__main__":
    unittest.main()
