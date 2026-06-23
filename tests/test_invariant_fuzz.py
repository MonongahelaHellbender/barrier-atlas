#!/usr/bin/env python3
"""Deterministic invariant fuzzer for the Barrier Atlas v0.1 runner.

The fuzzer mutates a known-good external checker envelope and asserts the
one-directional safety invariant: generated structural violations must never
produce CERTIFIED, and every generated case must produce exactly one valid verdict
record.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import plugin_runner  # noqa: E402
import spec_runner  # noqa: E402

BASE_FIXTURE = ROOT / "spec" / "conformance" / "fixtures" / "10-external-rup.barrier.json"
GOOD_CERT = ROOT / "certs" / "samples_w33.cert"
GOOD_SHA = hashlib.sha256(GOOD_CERT.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _write_dynamic_plugin(tmp: Path) -> dict[str, str]:
    plugin = tmp / "emit_plugin.py"
    plugin.write_text(
        """#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--envelope", required=True)
ap.add_argument("--artifacts-dir", required=True)
args = ap.parse_args()
env = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
out = env.get("checker", {}).get("fuzz_output", {})
mode = out.get("mode", "json")
if mode == "garbage":
    print("not-json")
    sys.exit(0)
if mode == "exit":
    sys.exit(7)
print(json.dumps({
    "verdict": out.get("verdict", "CERTIFIED"),
    "detail": "fuzz plugin controlled output",
    "rung": out.get("rung", "R3"),
}, sort_keys=True))
""",
        encoding="utf-8",
    )
    digest = hashlib.sha256(plugin.read_bytes()).hexdigest()
    manifest = tmp / "emit.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "barrier-atlas-fuzz-emitter",
                "version": "0.1",
                "kind": "external-rup",
                "command": ["python3", _rel(plugin)],
                "entrypoint": _rel(plugin),
                "sha256": digest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    bad_manifest = tmp / "emit-bad-hash.manifest.json"
    bad = json.loads(manifest.read_text(encoding="utf-8"))
    bad["sha256"] = "0" * 64
    bad_manifest.write_text(json.dumps(bad, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "dynamic": _rel(manifest),
        "dynamic_bad_hash": _rel(bad_manifest),
        "rup": "spec/checkers/rup.manifest.json",
        "rup_bad_hash": "spec/checkers/rup-bad-hash.manifest.json",
        "liar": "spec/checkers/liar.manifest.json",
        "missing": _rel(tmp / "missing.manifest.json"),
    }


def _timeout_ok(value: Any) -> bool:
    if value == "__absent__":
        return True
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


def _stronger_than(a: str, b: str) -> bool:
    return spec_runner._stronger_than(a, b)


def _build_case(rng: random.Random, case_id: int, manifests: dict[str, str]) -> tuple[dict, dict]:
    env = json.loads(BASE_FIXTURE.read_text(encoding="utf-8"))
    env = copy.deepcopy(env)
    env["id"] = f"fuzz-{case_id:05d}"
    meta = {
        "artifact_ok": True,
        "ceiling_ok": True,
        "timeout_ok": True,
        "manifest_ok": True,
        "plugin_output_legal": True,
        "plugin_rung_ok": True,
        "checker_positive": False,
    }

    artifact = env["artifacts"][0]
    path_mode = rng.choices(
        ["good", "absolute", "traversal", "remote", "missing"],
        weights=[58, 12, 12, 8, 10],
        k=1,
    )[0]
    if path_mode == "good":
        artifact["path"] = "certs/samples_w33.cert"
    elif path_mode == "absolute":
        artifact["path"] = str(GOOD_CERT)
        meta["artifact_ok"] = False
    elif path_mode == "traversal":
        artifact["path"] = "../barrier-atlas/certs/samples_w33.cert"
        meta["artifact_ok"] = False
    elif path_mode == "remote":
        artifact["path"] = "https://example.invalid/cert"
        meta["artifact_ok"] = False
    else:
        artifact["path"] = "certs/no-such-cert.cert"
        meta["artifact_ok"] = False

    sha_mode = rng.choices(["good", "bad", "empty"], weights=[74, 22, 4], k=1)[0]
    if sha_mode == "good":
        artifact["sha256"] = GOOD_SHA
    elif sha_mode == "bad":
        artifact["sha256"] = "f" * 64
        meta["artifact_ok"] = False
    else:
        artifact["sha256"] = ""
        meta["artifact_ok"] = False

    declared = rng.choice(spec_runner.RUNG_ORDER)
    env["rung"]["level"] = declared

    checker_mode = rng.choices(
        ["dynamic", "dynamic_bad_hash", "rup", "rup_bad_hash", "liar", "missing", "unknown"],
        weights=[60, 6, 5, 7, 8, 6, 8],
        k=1,
    )[0]
    checker = {
        "kind": "external-rup",
        "manifest": manifests.get(checker_mode, manifests["dynamic"]),
        "cert_artifact": "certificate",
    }

    if checker_mode == "unknown":
        checker = {"kind": "unknown-fuzz-checker"}
        meta["manifest_ok"] = False
        meta["plugin_output_legal"] = False
    elif checker_mode in {"dynamic_bad_hash", "rup_bad_hash", "missing"}:
        meta["manifest_ok"] = False
    elif checker_mode == "liar":
        meta["checker_positive"] = True
        meta["plugin_rung_ok"] = False
    elif checker_mode == "rup":
        meta["checker_positive"] = True
        meta["plugin_rung_ok"] = not _stronger_than("R3", declared)
    else:
        verdict = rng.choice(["CERTIFIED", "REFUSED", "DEFERRED", "UNVERIFIABLE-HERE", "BOGUS"])
        rung = rng.choice(spec_runner.RUNG_ORDER + ["RX"])
        mode = rng.choices(["json", "garbage", "exit"], weights=[86, 7, 7], k=1)[0]
        checker["fuzz_output"] = {"mode": mode, "verdict": verdict, "rung": rung}
        meta["checker_positive"] = mode == "json" and verdict == "CERTIFIED"
        meta["plugin_output_legal"] = mode == "json" and verdict in spec_runner.VALID_VERDICTS and rung in spec_runner.RUNG_ORDER
        meta["plugin_rung_ok"] = (
            rung in spec_runner.RUNG_ORDER
            and not _stronger_than(rung, "R3")
            and not _stronger_than(rung, declared)
        )

    timeout_value = rng.choice(["__absent__", 1, "1", 0, -1, "not-a-number", "0.5", None])
    if timeout_value != "__absent__":
        checker["timeout_seconds"] = timeout_value
    meta["timeout_ok"] = _timeout_ok(timeout_value)

    env["checker"] = checker
    ceiling = spec_runner.ATOMIC_CEILINGS.get(checker["kind"])
    if ceiling and _stronger_than(declared, ceiling):
        meta["ceiling_ok"] = False

    meta["structurally_certifiable"] = all(
        meta[key]
        for key in (
            "artifact_ok",
            "ceiling_ok",
            "timeout_ok",
            "manifest_ok",
            "plugin_output_legal",
            "plugin_rung_ok",
            "checker_positive",
        )
    )
    return env, meta


def _record_for(env: dict, envelope_path: Path) -> dict:
    loaded = copy.deepcopy(env)
    index = spec_runner._load_index(envelope_path)
    result = plugin_runner.evaluate(loaded, envelope_path, index)
    record_env = plugin_runner._record_env(loaded)
    return spec_runner.make_record(record_env, envelope_path, result)


def _assert_record(case_id: int, record: dict, meta: dict) -> None:
    if record.get("final_verdict") not in spec_runner.VALID_VERDICTS:
        raise AssertionError(f"case {case_id}: invalid verdict {record.get('final_verdict')!r}")
    if record.get("reason_code") not in spec_runner.REASON_CODES:
        raise AssertionError(f"case {case_id}: invalid reason {record.get('reason_code')!r}")
    if record.get("final_verdict") == spec_runner.CERTIFIED:
        if record.get("reason_code") != "OK":
            raise AssertionError(f"case {case_id}: CERTIFIED with reason {record.get('reason_code')}")
        if not meta["structurally_certifiable"]:
            raise AssertionError(f"case {case_id}: structural violation certified: {meta}")
        if not record.get("artifacts") or not all(a.get("verified") for a in record["artifacts"]):
            raise AssertionError(f"case {case_id}: CERTIFIED without verified artifacts")
    elif meta["structurally_certifiable"] and record.get("reason_code") == "OK":
        raise AssertionError(f"case {case_id}: OK reason on non-certified record")


def run(cases: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    temp_root = Path(tempfile.mkdtemp(prefix=".fuzz_plugins_", dir=ROOT))
    envelope_root = Path(tempfile.mkdtemp(prefix="barrier-fuzz-envelopes-"))
    counts = {"cases": 0, "certified": 0, "refused": 0, "deferred": 0, "unverifiable": 0}
    try:
        manifests = _write_dynamic_plugin(temp_root)
        for case_id in range(cases):
            env, meta = _build_case(rng, case_id, manifests)
            envelope_path = envelope_root / f"{env['id']}.barrier.json"
            envelope_path.write_text(json.dumps(env, sort_keys=True) + "\n", encoding="utf-8")
            try:
                record = _record_for(env, envelope_path)
            except Exception as e:  # noqa: BLE001
                raise AssertionError(f"case {case_id}: runner raised instead of emitting a record: {e}") from e
            _assert_record(case_id, record, meta)
            counts["cases"] += 1
            verdict = record["final_verdict"]
            if verdict == spec_runner.CERTIFIED:
                counts["certified"] += 1
            elif verdict == spec_runner.REFUSED:
                counts["refused"] += 1
            elif verdict == spec_runner.DEFERRED:
                counts["deferred"] += 1
            elif verdict == spec_runner.UNVERIFIABLE:
                counts["unverifiable"] += 1
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
        shutil.rmtree(envelope_root, ignore_errors=True)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260623)
    args = parser.parse_args(argv)
    if args.cases < 1:
        raise SystemExit("--cases must be positive")
    counts = run(args.cases, args.seed)
    print(json.dumps({"status": "pass", "seed": args.seed, **counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
