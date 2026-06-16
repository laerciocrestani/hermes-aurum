"""Tests for ledger.py append (CLI JSON and stdin)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "skills/financial-operator/scripts/ledger.py"


def run_append(hermes_home: Path, payload: dict, *, use_stdin: bool = False) -> subprocess.CompletedProcess[str]:
    env = {"HERMES_HOME": str(hermes_home)}
    body = json.dumps(payload, ensure_ascii=False)
    if use_stdin:
        return subprocess.run(
            [sys.executable, str(LEDGER), "append", "-"],
            input=body,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
    return subprocess.run(
        [sys.executable, str(LEDGER), "append", body],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_append_expense_via_argv(tmp_path: Path) -> None:
    result = run_append(
        tmp_path,
        {
            "type": "expense",
            "date": "2026-06-16",
            "account": "Banco Inter",
            "category": "Alimentação",
            "amount": 0.85,
            "description": "mercado",
        },
    )
    assert result.returncode == 0, result.stderr
    assert '"status": "ok"' in result.stdout


def test_append_expense_via_stdin(tmp_path: Path) -> None:
    result = run_append(
        tmp_path,
        {
            "type": "expense",
            "date": "2026-06-16",
            "account": "Banco Inter",
            "category": "Alimentação",
            "amount": 0.85,
        },
        use_stdin=True,
    )
    assert result.returncode == 0, result.stderr
    ledger = tmp_path / "data" / "ledger.jsonl"
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    last = json.loads(lines[-1])
    assert last["amount"] == 0.85
