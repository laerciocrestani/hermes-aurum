#!/usr/bin/env python3
"""Daily backup for Aurum profile data (ledger, categories, memory)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from paths import get_paths

# Override with AURUM_BACKUP_DIR (absolute path on the server).
DEFAULT_BACKUP_SUBDIR = "bkp"
DEFAULT_KEEP_DAYS = 30


def backup_root(hermes_home: Path) -> Path:
    override = os.environ.get("AURUM_BACKUP_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (hermes_home / DEFAULT_BACKUP_SUBDIR).resolve()


def files_to_backup(hermes_home: Path, paths: dict[str, Path]) -> list[tuple[Path, str]]:
    """Return (source, arcname) pairs. arcname is relative inside the archive."""
    candidates: list[tuple[Path, str]] = [
        (paths["ledger"], "data/ledger.jsonl"),
        (paths["categories"], "references/categories.json"),
        (hermes_home / "config.yaml", "config.yaml"),
        (hermes_home / "MEMORY.md", "MEMORY.md"),
        (hermes_home / "USER.md", "USER.md"),
        (hermes_home / "SOUL.md", "SOUL.md"),
    ]
    env_file = hermes_home / ".env"
    if env_file.is_file():
        candidates.append((env_file, ".env"))

    out: list[tuple[Path, str]] = []
    for src, arcname in candidates:
        if src.is_file():
            out.append((src, arcname))
    return out


def prune_old_backups(root: Path, keep_days: int) -> list[str]:
    if keep_days <= 0:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    removed: list[str] = []
    for path in sorted(root.glob("aurum-*.tar.gz")):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            path.unlink()
            removed.append(str(path))
    return removed


def run_backup(keep_days: int) -> dict:
    paths = get_paths()
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    root = backup_root(hermes_home)
    root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d")
    archive = root / f"aurum-{stamp}.tar.gz"

    sources = files_to_backup(hermes_home, paths)
    if not sources:
        raise FileNotFoundError(
            "Nothing to back up — ledger not found. "
            f"Expected ledger at {paths['ledger']}"
        )

    with tarfile.open(archive, "w:gz") as tar:
        for src, arcname in sources:
            tar.add(src, arcname=arcname)
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "hermes_home": str(hermes_home),
            "files": [arcname for _, arcname in sources],
        }
        manifest_path = root / f".manifest-{stamp}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tar.add(manifest_path, arcname="manifest.json")
        manifest_path.unlink(missing_ok=True)

    os.chmod(archive, 0o600)
    removed = prune_old_backups(root, keep_days)

    return {
        "status": "ok",
        "archive": str(archive),
        "files": [arcname for _, arcname in sources],
        "removed_old": removed,
        "backup_dir": str(root),
        "keep_days": keep_days,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aurum daily backup")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Create today's backup archive")
    p_run.add_argument(
        "--keep-days",
        type=int,
        default=int(os.environ.get("AURUM_BACKUP_KEEP_DAYS", DEFAULT_KEEP_DAYS)),
        help=f"Delete archives older than N days (default: {DEFAULT_KEEP_DAYS})",
    )

    p_list = sub.add_parser("list", help="List backup archives")

    args = parser.parse_args()
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    root = backup_root(hermes_home)

    try:
        if args.command == "run":
            result = run_backup(args.keep_days)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "list":
            archives = sorted(root.glob("aurum-*.tar.gz")) if root.is_dir() else []
            print(
                json.dumps(
                    {
                        "backup_dir": str(root),
                        "archives": [str(p) for p in archives],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except (FileNotFoundError, OSError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
