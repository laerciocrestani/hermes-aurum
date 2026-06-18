"""Tests for ledger check and repair."""

from __future__ import annotations

import json
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "skills/financial-operator/scripts/ledger.py"
SCRIPTS = REPO_ROOT / "skills/financial-operator/scripts"


def run_ledger(hermes_home: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    env = {}
    if hermes_home is not None:
        env["HERMES_HOME"] = str(hermes_home)
    return subprocess.run(
        [sys.executable, str(LEDGER), *args],
        text=True,
        capture_output=True,
        env=env or None,
        check=False,
    )


def profile_ledger() -> Path:
    path = REPO_ROOT / "data" / "ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def seed_ledger(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '{"type":"account","name":"Banco Inter","kind":"asset"}',
        '{"type":"expense","date":"2026-06-10","account":"Banco Inter","category":"Alimentação","amount":52.30}',
        "not valid json",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class LedgerCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._profile_ledger = REPO_ROOT / "data" / "ledger.jsonl"
        self._had_profile = self._profile_ledger.exists()
        self._profile_backup: bytes | None = None
        if self._had_profile:
            self._profile_backup = self._profile_ledger.read_bytes()
            self._profile_ledger.unlink()

    def tearDown(self) -> None:
        if self._had_profile and self._profile_backup is not None:
            self._profile_ledger.parent.mkdir(parents=True, exist_ok=True)
            self._profile_ledger.write_bytes(self._profile_backup)
        elif self._profile_ledger.exists():
            self._profile_ledger.unlink()

    def test_check_reports_invalid_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed_ledger(profile_ledger())
            result = run_ledger(None, "check")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "corrupt")
            self.assertEqual(data["ledger"]["valid_count"], 2)
            self.assertEqual(len(data["ledger"]["errors"]), 1)

    def test_repair_keeps_valid_events(self) -> None:
        ledger = profile_ledger()
        seed_ledger(ledger)
        repair = run_ledger(None, "repair")
        self.assertEqual(repair.returncode, 0, repair.stderr)
        body = json.loads(repair.stdout)
        self.assertEqual(body["kept_events"], 2)
        self.assertEqual(body["removed_lines"], 1)
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        check = run_ledger(None, "check")
        self.assertEqual(json.loads(check.stdout)["status"], "ok")

    def test_reset_recreates_from_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = root / "references"
            refs.mkdir()
            shutil.copy2(REPO_ROOT / "references/categories.json", refs / "categories.json")
            seed = refs / "ledger.seed.jsonl"
            shutil.copy2(REPO_ROOT / "references/ledger.seed.jsonl", seed)
            data = root / "data"
            data.mkdir()
            (data / "ledger.jsonl").write_text('{"type":"expense","amount":1}\n', encoding="utf-8")
            paths = {
                "profile_root": root,
                "hermes_home": root,
                "seed": seed,
                "ledger": data / "ledger.jsonl",
            }
            sys.path.insert(0, str(SCRIPTS))
            from ledger import cmd_reset  # noqa: E402

            cmd_reset(paths, confirm=True)
            lines = (data / "ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 4)
            self.assertTrue(all('"type":"account"' in line or '"type": "account"' in line for line in lines))


if __name__ == "__main__":
    unittest.main()
