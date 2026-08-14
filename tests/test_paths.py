"""Resolução de caminhos e seeds."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from helpers import make_workspace

from paths import ensure_runtime_files


class PathsTests(unittest.TestCase):
    def test_runtime_files_created_from_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_workspace(Path(tmp))
            ensure_runtime_files(paths)
            self.assertTrue(paths.accounts.is_file())
            self.assertTrue(paths.categories.is_file())
            self.assertTrue(paths.cashflow.is_file())
            self.assertTrue(paths.schedule.is_file())


if __name__ == "__main__":
    unittest.main()
