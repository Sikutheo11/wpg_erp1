#!/usr/bin/env python3
"""Fail when sensitive runtime artifacts are tracked by Git."""

from pathlib import PurePosixPath
import subprocess
import sys


DENIED_NAMES = {
    ".env",
    "db.sqlite3",
}
DENIED_SUFFIXES = {
    ".sqlite3",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".dump",
}
DENIED_PARTS = {
    "backups",
}
ALLOWED_NAMES = {
    ".env.example",
}


def is_sensitive(path_text):
    path = PurePosixPath(path_text)
    if path.name in ALLOWED_NAMES:
        return False
    return (
        path.name in DENIED_NAMES
        or path.suffix.lower() in DENIED_SUFFIXES
        or bool(set(path.parts) & DENIED_PARTS)
    )


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [
        item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


def main():
    violations = sorted(
        path for path in tracked_files() if is_sensitive(path)
    )
    if violations:
        print("SECURITY_PREFLIGHT_FAILED")
        for path in violations:
            print(f"Tracked sensitive artifact: {path}")
        return 1

    print("SECURITY_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
