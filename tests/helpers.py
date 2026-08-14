"""Helpers de teste para o Aurum v2."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills/cashflow/scripts"
sys.path.insert(0, str(SCRIPTS))

from paths import Paths, get_paths  # noqa: E402


def make_workspace(tmp: Path) -> Paths:
    refs = tmp / "references"
    refs.mkdir(parents=True)
    for name in ("accounts.json", "categories.json", "keywords.json"):
        shutil.copy2(REPO_ROOT / "references" / name, refs / name)
    return get_paths(tmp)
