#!/usr/bin/env python3
"""
Prepare local directories for Docker bind mounts and set permissions
so containers (running as UID 1000) can write SQLite DB, logs and backups.

Usage examples:
  python scripts/prepare_volumes.py --all
  python scripts/prepare_volumes.py --cities city1 city2

On Linux/macOS: sets owner to uid:1000 and group to gid:1000 when possible,
falls back to chmod 0777 if chown fails.
On Windows: grants Full Control to Everyone via icacls (best-effort).
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable


APP_UID = 1000
APP_GID = 1000


def ensure_dirs(paths: Iterable[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def set_permissions_posix(paths: Iterable[Path]) -> None:
    for p in paths:
        try:
            os.chown(p, APP_UID, APP_GID)  # type: ignore[attr-defined]
        except Exception:
            # chown may fail on some filesystems; ignore
            pass
        try:
            # Allow rwx for all to avoid permission surprises
            os.chmod(p, 0o777)
        except Exception:
            pass


def grant_windows_acl(path: Path) -> None:
    # Grant Full control to Everyone on folder recursively
    # SDDL SID for Everyone: S-1-1-0; icacls supports name "Everyone" as well
    try:
        subprocess.run(
            [
                "icacls",
                str(path),
                "/grant",
                "Everyone:(OI)(CI)F",
                "/T",
                "/C",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
    except Exception:
        pass


def set_permissions_windows(paths: Iterable[Path]) -> None:
    for p in paths:
        grant_windows_acl(p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare volumes for Docker containers")
    parser.add_argument(
        "--cities",
        nargs="+",
        choices=["city1", "city2"],
        help="Which cities to prepare (default: both)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Prepare for both city1 and city2",
    )

    args = parser.parse_args()

    cities = ["city1", "city2"] if args.all or not args.cities else args.cities

    root = Path(__file__).resolve().parents[1]
    to_prepare: list[Path] = []

    for city in cities:
        to_prepare.extend(
            [
                root / "data" / city,
                root / "logs" / city,
                root / "backups" / city,
            ]
        )

    ensure_dirs(to_prepare)

    if is_windows():
        set_permissions_windows(to_prepare)
    else:
        set_permissions_posix(to_prepare)

    print("Prepared directories:")
    for p in to_prepare:
        print(f" - {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
