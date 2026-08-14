"""CLI aurum-run."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS, make_workspace

from cli import _run


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = make_workspace(Path(self.tmp.name))
        self.env_today = os.environ.get("AURUM_TODAY")
        os.environ["AURUM_TODAY"] = "2026-08-14"

    def tearDown(self) -> None:
        if self.env_today is None:
            os.environ.pop("AURUM_TODAY", None)
        else:
            os.environ["AURUM_TODAY"] = self.env_today
        self.tmp.cleanup()

    def _run(self, *argv: str) -> dict:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = _run(["--root", str(self.paths.profile_root), *argv])
        payload = json.loads(buf.getvalue())
        payload["_exit"] = code
        return payload

    def test_apply_via_cli(self) -> None:
        result = self._run(
            "apply",
            "Gastei 30 reais em mercado no débito com o banco Inter",
        )
        self.assertEqual(result["_exit"], 0)
        self.assertEqual(result["entry"]["category"], "Alimentação")
        self.assertEqual(result["entry"]["account"], "Banco Inter")

    def test_today_lists_entry(self) -> None:
        self._run("apply", "Gastei 30 reais em mercado no Inter")
        listed = self._run("today")
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["totals"]["expense"], 30.0)

    def test_accounts_and_categories(self) -> None:
        accounts = self._run("accounts")
        categories = self._run("categories")
        self.assertGreaterEqual(accounts["count"], 1)
        self.assertIn("Alimentação", categories["expense"])

    def test_wrapper_exists(self) -> None:
        wrapper = SCRIPTS / "aurum-run"
        self.assertTrue(wrapper.is_file())


if __name__ == "__main__":
    unittest.main()
