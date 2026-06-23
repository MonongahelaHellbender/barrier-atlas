#!/usr/bin/env python3
"""Implementation-independent conformance harness for Barrier Atlas v0.1."""
import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_once(command: str, fixture: Path) -> dict:
    argv = shlex.split(command) + ["--envelope", str(fixture)]
    proc = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if not proc.stdout.strip():
        raise AssertionError(f"{fixture.name}: runner produced no stdout (stderr={proc.stderr})")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"{fixture.name}: runner stdout is not one JSON object: {e}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        ) from e


def _fixture_paths() -> list[Path]:
    paths = []
    for path in sorted(FIXTURES.rglob("*.barrier.json")):
        env = _load(path)
        if "expected_verdict" in env:
            paths.append(path)
    return paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runner", default="python3 tools/spec_runner.py")
    args = ap.parse_args()

    failures = []
    for fixture in _fixture_paths():
        env = _load(fixture)
        expected = env["expected_verdict"]
        expected_reason = env.get("expected_reason_code")
        try:
            first = _run_once(args.runner, fixture)
            second = _run_once(args.runner, fixture)
            if first.get("final_verdict") != expected:
                raise AssertionError(
                    f"{fixture.name}: expected verdict {expected}, got {first.get('final_verdict')}"
                )
            if expected_reason and first.get("reason_code") != expected_reason:
                raise AssertionError(
                    f"{fixture.name}: expected reason {expected_reason}, got {first.get('reason_code')}"
                )
            if first.get("record_core_sha256") != second.get("record_core_sha256"):
                raise AssertionError(f"{fixture.name}: record_core_sha256 is nondeterministic")
            print(f"PASS {fixture.name}: {expected} / {first.get('reason_code')}")
        except Exception as e:  # noqa: BLE001
            failures.append(str(e))

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    print(f"\nconformance passed ({len(_fixture_paths())} fixtures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
