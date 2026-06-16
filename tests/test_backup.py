"""Tests for backup.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUP = REPO_ROOT / "skills/financial-operator/scripts/backup.py"
LEDGER = REPO_ROOT / "skills/financial-operator/scripts/ledger.py"


def test_backup_creates_archive(tmp_path: Path) -> None:
    home = tmp_path / "aurum"
    home.mkdir()
    env = {"HERMES_HOME": str(home), "AURUM_BACKUP_DIR": str(home / "bkp")}

    append = subprocess.run(
        [
            sys.executable,
            str(LEDGER),
            "append",
            json.dumps(
                {
                    "type": "expense",
                    "date": "2026-06-16",
                    "account": "Banco Inter",
                    "category": "Alimentação",
                    "amount": 1.0,
                }
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert append.returncode == 0, append.stderr

    run = subprocess.run(
        [sys.executable, str(BACKUP), "run", "--keep-days", "7"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    payload = json.loads(run.stdout)
    archive = Path(payload["archive"])
    assert archive.is_file()

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert "data/ledger.jsonl" in names
    assert "references/categories.json" in names
