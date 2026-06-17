"""Resolve caminhos do Aurum a partir da localização do script (funciona com symlinks)."""

from __future__ import annotations

import os
from pathlib import Path


def find_references_dir(start: Path | None = None) -> Path:
    """Walk up from start until references/categories.json is found."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for _ in range(10):
        ref = current / "references"
        if (ref / "categories.json").is_file():
            return ref
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError(
        "references/categories.json não encontrado — verifique se o repositório Aurum está íntegro "
        "ou se as skills estão com symlink a partir do repositório."
    )


def get_paths() -> dict[str, Path]:
    refs = find_references_dir()
    repo_root = refs.parent
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    return {
        "repo_root": repo_root,
        "references": refs,
        "seed": refs / "ledger.seed.jsonl",
        "categories": refs / "categories.json",
        "ledger": hermes_home / "data" / "ledger.jsonl",
    }
