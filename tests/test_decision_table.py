#!/usr/bin/env python3
"""Bridge tests for the Lean-proved Phase F decision core."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decide  # noqa: E402


TABLE_PATH = ROOT / "spec" / "decision_table.json"
DEFAULT_LEAN_REPO = ROOT.parent / "dist" / "lean-verification-journey"
LEAN_REPO_EXPLICIT = "BARRIER_ATLAS_LEAN_REPO" in os.environ
LEAN_REPO = Path(os.environ.get("BARRIER_ATLAS_LEAN_REPO", DEFAULT_LEAN_REPO))
LEAN_EXPORTER = LEAN_REPO / "RunnerDecisionTable.lean"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_table() -> dict:
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))


def _require_lean_export() -> bool:
    return os.environ.get("BARRIER_ATLAS_REQUIRE_LEAN_EXPORT", "").lower() in {"1", "true", "yes"}


def _can_run_lean_export() -> tuple[bool, str]:
    if not LEAN_REPO.exists():
        return False, f"lean repo missing: {LEAN_REPO}"
    if not LEAN_EXPORTER.exists():
        return False, f"Lean exporter missing: {LEAN_EXPORTER}"
    if shutil.which("lake") is None:
        return False, "lake executable missing"
    return True, "available"


def _fresh_lean_export() -> dict:
    proc = subprocess.run(
        ["lake", "env", "lean", "--run", str(LEAN_EXPORTER.name)],
        cwd=LEAN_REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def _positive_common() -> dict[str, bool]:
    return {
        "path_ok": True,
        "artifact_present": True,
        "artifact_hash_ok": True,
        "manifest_ok": True,
        "manifest_hash_ok": True,
        "timeout_ok": True,
        "sandbox_ok": True,
        "rung_within_ceiling": True,
        "plugin_output_legal": True,
        "plugin_rung_le_ceiling": True,
        "plugin_rung_le_declared": True,
        "checker_positive": True,
        "all_parts_certified": True,
        "declared_eq_weakest": True,
        "quorum_count_ge_required": True,
        "quorum_distinct_count_ge_required": True,
    }


def _row(kind: str, **overrides: bool) -> tuple[decide.Verdict, str]:
    facts = _positive_common()
    facts.update(overrides)
    facts["kind"] = kind
    k, code = decide.code_from_facts(**facts)
    return decide.decide(decide.facts_from_code(k, code))


def _runner_verdict(fixture: str) -> str:
    path = ROOT / "spec" / "conformance" / "fixtures" / fixture
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "plugin_runner.py"), "--envelope", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)["final_verdict"]


def test_committed_table_matches_python_mirror() -> None:
    table = _load_table()
    _assert(table["schema_version"] == "0.1", "unexpected table schema")
    _assert(table["field_names"] == decide.FIELD_NAMES, "field-name drift")
    _assert(table["kinds"] == decide.KINDS, "kind-order drift")
    _assert(table["row_format"] == ["kind", "code", "verdict", "reason_code"], "row format drift")

    expected_count = len(decide.KINDS) * decide.FACT_SPACE_SIZE
    rows = table["rows"]
    _assert(len(rows) == expected_count, f"expected {expected_count} rows, got {len(rows)}")

    for i, (actual, expected) in enumerate(zip(rows, decide.iter_rows(), strict=True)):
        if actual != expected:
            raise AssertionError(f"decision table row {i} drifted: actual={actual}, expected={expected}")


def test_committed_table_matches_fresh_lean_export() -> str:
    available, reason = _can_run_lean_export()
    if not available:
        if LEAN_REPO.exists() and not LEAN_EXPORTER.exists():
            raise AssertionError(reason)
        if LEAN_REPO_EXPLICIT:
            raise AssertionError(reason)
        if _require_lean_export():
            raise AssertionError(f"cannot run Lean decision-table export: {reason}")
        return f"skipped ({reason})"

    committed = _load_table()
    exported = _fresh_lean_export()
    _assert(exported == committed, "committed decision table drifted from fresh Lean export")
    return "checked"


def test_representative_runner_branches_match_decision_core() -> None:
    cases = [
        ("01-valid-rup.barrier.json", _row("atomic")),
        ("02-tampered-artifact.barrier.json", _row("atomic", artifact_hash_ok=False)),
        ("03-missing-artifact.barrier.json", _row("atomic", artifact_present=False)),
        ("06-rung-laundering.barrier.json", _row("composed", declared_eq_weakest=False)),
        ("07-weak-subbarrier.barrier.json", _row("composed", all_parts_certified=False)),
        ("08-unknown-checker.barrier.json", _row("unknown")),
        ("10-external-rup.barrier.json", _row("external")),
        ("11-checker-hash-mismatch.barrier.json", _row("external", manifest_hash_ok=False)),
        ("14-malformed-timeout.barrier.json", _row("external", timeout_ok=False)),
        ("15-quorum-met.barrier.json", _row("quorum")),
        (
            "16-quorum-not-met.barrier.json",
            _row("quorum", checker_positive=False, quorum_count_ge_required=False, quorum_distinct_count_ge_required=False),
        ),
        ("17-quorum-not-independent.barrier.json", _row("quorum", quorum_distinct_count_ge_required=False)),
        ("18-sandbox-required-unavailable.barrier.json", _row("external", sandbox_ok=False)),
    ]
    for fixture, (verdict, _reason) in cases:
        runner = _runner_verdict(fixture)
        _assert(runner == verdict.value, f"{fixture}: runner={runner}, decision-core={verdict.value}")


def run() -> dict:
    lean_export = test_committed_table_matches_fresh_lean_export()
    test_committed_table_matches_python_mirror()
    test_representative_runner_branches_match_decision_core()
    table = _load_table()
    return {
        "lean_export": lean_export,
        "status": "pass",
        "rows": len(table["rows"]),
        "spot_checked_runner_branches": 13,
    }


def main() -> int:
    print(json.dumps(run(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
