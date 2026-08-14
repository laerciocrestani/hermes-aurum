"""Resolve caminhos do Aurum a partir da localização do script (funciona com symlinks)."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    profile_root: Path
    references: Path
    cashflow: Path
    accounts: Path
    categories: Path
    keywords: Path
    seed_accounts: Path
    seed_categories: Path
    seed_keywords: Path


def find_references_dir(start: Path | None = None) -> Path:
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
        "references/categories.json não encontrado — verifique se o perfil Aurum está íntegro."
    )


def resolve_hermes_home(profile_root: Path) -> Path:
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return profile_root.resolve()


def get_paths(start: Path | None = None) -> Paths:
    refs = find_references_dir(start)
    profile_root = refs.parent.resolve()
    data = profile_root / "data"
    return Paths(
        profile_root=profile_root,
        references=refs,
        cashflow=data / "cashflow.jsonl",
        accounts=data / "accounts.json",
        categories=data / "categories.json",
        keywords=data / "keywords.json",
        seed_accounts=refs / "accounts.json",
        seed_categories=refs / "categories.json",
        seed_keywords=refs / "keywords.json",
    )


def ensure_runtime_files(paths: Paths) -> None:
    """Copia seeds de referências para data/ na primeira execução."""
    paths.cashflow.parent.mkdir(parents=True, exist_ok=True)
    copies = (
        (paths.seed_accounts, paths.accounts),
        (paths.seed_categories, paths.categories),
        (paths.seed_keywords, paths.keywords),
    )
    for src, dest in copies:
        if dest.exists():
            continue
        if not src.exists():
            raise FileNotFoundError(f"Arquivo seed não encontrado: {src}")
        shutil.copy2(src, dest)
    if not paths.cashflow.exists():
        paths.cashflow.write_text("", encoding="utf-8")
