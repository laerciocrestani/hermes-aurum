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


def resolve_profile_root(refs: Path) -> Path:
    """Raiz do perfil Aurum (pai de references/)."""
    return refs.parent


def resolve_hermes_home(profile_root: Path) -> Path:
    """HERMES_HOME efetivo: env explícito ou raiz do perfil."""
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return profile_root.resolve()


def resolve_ledger_path(hermes_home: Path, profile_root: Path) -> Path:
    """Ledger: HERMES_HOME/data primeiro; depois candidatos do perfil instalado."""
    candidates = [
        hermes_home / "data" / "ledger.jsonl",
        profile_root / "data" / "ledger.jsonl",
        Path.home() / ".hermes" / "profiles" / "aurum" / "data" / "ledger.jsonl",
        Path.home() / ".hermes" / "data" / "ledger.jsonl",
    ]
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return (profile_root / "data" / "ledger.jsonl").resolve()


def get_paths() -> dict[str, Path]:
    refs = find_references_dir()
    profile_root = resolve_profile_root(refs)
    hermes_home = resolve_hermes_home(profile_root)
    return {
        "repo_root": profile_root,
        "profile_root": profile_root,
        "references": refs,
        "seed": refs / "ledger.seed.jsonl",
        "categories": refs / "categories.json",
        "hermes_home": hermes_home,
        "ledger": resolve_ledger_path(hermes_home, profile_root),
    }
