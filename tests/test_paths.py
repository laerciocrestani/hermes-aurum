"""Tests for ledger path resolution."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "financial-operator" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from paths import get_paths, resolve_ledger_path, resolve_profile_root, find_references_dir  # noqa: E402


class LedgerPathTests(unittest.TestCase):
    def test_prefers_profile_ledger_over_global_hermes_home(self) -> None:
        refs = find_references_dir()
        profile = resolve_profile_root(refs)
        with tempfile.TemporaryDirectory() as tmp:
            global_home = Path(tmp) / "global"
            profile_data = profile / "data"
            global_data = global_home / "data"
            profile_data.mkdir(parents=True, exist_ok=True)
            global_data.mkdir(parents=True, exist_ok=True)
            (profile_data / "ledger.jsonl").write_text('{"type":"account","name":"Perfil"}\n', encoding="utf-8")
            (global_data / "ledger.jsonl").write_text('{"type":"account","name":"Global"}\n', encoding="utf-8")
            chosen = resolve_ledger_path(global_home, profile)
            self.assertEqual(chosen, (profile_data / "ledger.jsonl").resolve())

    def test_get_paths_uses_profile_ledger_path_even_when_only_global_exists(self) -> None:
        refs = find_references_dir()
        profile = resolve_profile_root(refs)
        profile_ledger = profile / "data" / "ledger.jsonl"
        with tempfile.TemporaryDirectory() as tmp:
            global_home = Path(tmp) / "global"
            global_data = global_home / "data"
            global_data.mkdir(parents=True)
            (global_data / "ledger.jsonl").write_text('{"type":"account","name":"Global"}\n', encoding="utf-8")
            try:
                os.environ["HERMES_HOME"] = str(global_home)
                paths = get_paths()
                self.assertEqual(paths["ledger"].resolve(), profile_ledger.resolve())
            finally:
                os.environ.pop("HERMES_HOME", None)


if __name__ == "__main__":
    unittest.main()
