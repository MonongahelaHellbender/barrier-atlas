#!/usr/bin/env python3
"""Audit the lightweight Barrier Atlas toolchain lock."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "tools" / "TOOLCHAIN.lock"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def main() -> int:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    min_version = _version_tuple(lock["python"]["minimum"])
    current = sys.version_info[: len(min_version)]
    if current < min_version:
        print(
            f"Python {lock['python']['minimum']}+ required, got "
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            file=sys.stderr,
        )
        return 1

    checked = []
    for tool in lock.get("optional_tools", []):
        raw_path = os.environ.get(tool.get("env", ""), "") or tool.get("default", "")
        if not raw_path:
            continue
        path = (ROOT / raw_path).resolve()
        if not path.exists():
            checked.append({"id": tool["id"], "status": "absent"})
            continue
        got = _sha256(path)
        want = tool.get("sha256")
        if want and got != want:
            print(
                f"{tool['id']} sha256 mismatch: got {got}, expected {want}",
                file=sys.stderr,
            )
            return 1
        checked.append({"id": tool["id"], "status": "present", "sha256": got})

    print(json.dumps({
        "status": "pass",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "optional_tools": checked,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
