#!/usr/bin/env python3
"""Deterministic invariant fuzzer for the Barrier Atlas v0.1 runner.

The fuzzer mutates atomic plugin envelopes and now also generates composed,
multi-region, and quorum envelopes. Its oracle is intentionally independent and
coarse: a generated case may certify only when the structural conditions needed
for certification are present. Any generated structural violation must never
produce CERTIFIED, and every generated case must produce one valid verdict record.
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

GOOD_CERT = ROOT / "certs" / "samples_w33.cert"
GOOD_SHA = hashlib.sha256(GOOD_CERT.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _stronger_than(a: str, b: str) -> bool:
    return spec_runner._stronger_than(a, b)


def _weaker(a: str, b: str) -> str:
    return spec_runner._weaker(a, b)


def _rung_at_least(earned: str, declared: str) -> bool:
    return earned in spec_runner.RUNG_ORDER and not _stronger_than(declared, earned)


def _base_env(case_id: str, checker: dict, rung: str = "R3") -> dict:
    return {
        "id": case_id,
        "schema_version": "0.1",
        "claim": {
            "statement": "A generated fuzz claim exercises runner-owned structural gates.",
            "kind": "impossibility",
            "negation_of": "a fail-open certification path",
            "scope": "deterministic fuzz case",
        },
        "domain": "fuzz/generated",
        "rung": {
            "level": rung,
            "name": "generated-rung",
            "trusted_base": ["fuzzer oracle"],
        },
        "certificate": {"kind": "fuzz-rup"},
        "artifacts": [
            {
                "id": "certificate",
                "type": "lrat-flat",
                "role": "certificate",
                "path": "certs/samples_w33.cert",
                "sha256": GOOD_SHA,
            }
        ],
        "checker": checker,
        "status": "live",
        "provenance": {"source_package": "deterministic invariant fuzzer"},
        "one_directional": "generated case must never certify a structural violation",
    }


def _write_dynamic_plugin(tmp: Path) -> dict[str, dict[str, str]]:
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

    known = {
        "dynamic": _rel(manifest),
        "dynamic_bad_hash": _rel(bad_manifest),
        "rup": "spec/checkers/rup.manifest.json",
        "rup_alt": "spec/checkers/rup-alt.manifest.json",
        "rup_bad_hash": "spec/checkers/rup-bad-hash.manifest.json",
        "liar": "spec/checkers/liar.manifest.json",
        "missing": _rel(tmp / "missing.manifest.json"),
    }
    hashes = {
        "dynamic": digest,
        "dynamic_bad_hash": digest,
        "rup": hashlib.sha256((ROOT / "tools/checkers/rup_plugin.py").read_bytes()).hexdigest(),
        "rup_alt": hashlib.sha256((ROOT / "tools/checkers/rup_plugin_alt.py").read_bytes()).hexdigest(),
        "liar": hashlib.sha256((ROOT / "tools/checkers/liar_plugin.py").read_bytes()).hexdigest(),
        "rup_bad_hash": hashlib.sha256((ROOT / "tools/checkers/rup_plugin.py").read_bytes()).hexdigest(),
        "missing": "",
    }
    return {key: {"path": value, "hash": hashes[key]} for key, value in known.items()}


def _timeout_ok(value: Any) -> bool:
    if value == "__absent__":
        return True
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


def _external_checker(
    rng: random.Random,
    manifests: dict[str, dict[str, str]],
    *,
    mostly_good: bool = False,
) -> tuple[dict, dict]:
    meta = {
        "artifact_ok": True,
        "ceiling_ok": True,
        "timeout_ok": True,
        "manifest_ok": True,
        "plugin_output_legal": True,
        "plugin_rung_ok": True,
        "checker_positive": False,
        "earned_rung": "R3",
        "checker_hash": "",
    }
    checker_mode = rng.choices(
        ["dynamic", "dynamic_bad_hash", "rup", "rup_alt", "rup_bad_hash", "liar", "missing", "unknown"],
        weights=[45, 5, 16, 12, 5, 7, 5, 5] if mostly_good else [60, 6, 5, 4, 7, 8, 5, 5],
        k=1,
    )[0]
    if checker_mode == "unknown":
        checker = {"kind": "unknown-fuzz-checker"}
        meta["manifest_ok"] = False
        meta["plugin_output_legal"] = False
        return checker, meta

    checker = {
        "kind": "external-rup",
        "manifest": manifests[checker_mode]["path"],
        "cert_artifact": "certificate",
    }
    meta["checker_hash"] = manifests[checker_mode]["hash"]
    if checker_mode in {"dynamic_bad_hash", "rup_bad_hash", "missing"}:
        meta["manifest_ok"] = False
    elif checker_mode == "liar":
        meta["checker_positive"] = True
        meta["plugin_rung_ok"] = False
    elif checker_mode in {"rup", "rup_alt"}:
        meta["checker_positive"] = True
    else:
        verdict = rng.choice(["CERTIFIED", "REFUSED", "DEFERRED", "UNVERIFIABLE-HERE", "BOGUS"])
        rung = rng.choice(spec_runner.RUNG_ORDER + ["RX"])
        mode = rng.choices(["json", "garbage", "exit"], weights=[86, 7, 7], k=1)[0]
        checker["fuzz_output"] = {"mode": mode, "verdict": verdict, "rung": rung}
        meta["checker_positive"] = mode == "json" and verdict == "CERTIFIED"
        meta["plugin_output_legal"] = mode == "json" and verdict in spec_runner.VALID_VERDICTS and rung in spec_runner.RUNG_ORDER
        meta["plugin_rung_ok"] = rung in spec_runner.RUNG_ORDER and not _stronger_than(rung, "R3")
        meta["earned_rung"] = rung if rung in spec_runner.RUNG_ORDER else "R5"

    timeout_value = rng.choice(["__absent__", 1, "1", 0, -1, "not-a-number", "0.5", None])
    if mostly_good and rng.random() < 0.85:
        timeout_value = "__absent__"
    if timeout_value != "__absent__":
        checker["timeout_seconds"] = timeout_value
    meta["timeout_ok"] = _timeout_ok(timeout_value)
    return checker, meta


def _external_case(
    rng: random.Random,
    case_id: str,
    manifests: dict[str, dict[str, str]],
) -> tuple[dict, dict]:
    checker, meta = _external_checker(rng, manifests)
    declared = rng.choice(spec_runner.RUNG_ORDER)
    env = _base_env(case_id, checker, declared)

    path_mode = rng.choices(["good", "absolute", "traversal", "remote", "missing"], weights=[58, 12, 12, 8, 10], k=1)[0]
    if path_mode == "absolute":
        env["artifacts"][0]["path"] = str(GOOD_CERT)
        meta["artifact_ok"] = False
    elif path_mode == "traversal":
        env["artifacts"][0]["path"] = "../barrier-atlas/certs/samples_w33.cert"
        meta["artifact_ok"] = False
    elif path_mode == "remote":
        env["artifacts"][0]["path"] = "https://example.invalid/cert"
        meta["artifact_ok"] = False
    elif path_mode == "missing":
        env["artifacts"][0]["path"] = "certs/no-such-cert.cert"
        meta["artifact_ok"] = False

    sha_mode = rng.choices(["good", "bad", "empty"], weights=[74, 22, 4], k=1)[0]
    if sha_mode == "bad":
        env["artifacts"][0]["sha256"] = "f" * 64
        meta["artifact_ok"] = False
    elif sha_mode == "empty":
        env["artifacts"][0]["sha256"] = ""
        meta["artifact_ok"] = False

    ceiling = spec_runner.ATOMIC_CEILINGS.get(checker["kind"])
    if ceiling and _stronger_than(declared, ceiling):
        meta["ceiling_ok"] = False
    if meta["earned_rung"] in spec_runner.RUNG_ORDER and _stronger_than(meta["earned_rung"], "R3"):
        meta["plugin_rung_ok"] = False
    if meta["earned_rung"] in spec_runner.RUNG_ORDER and _stronger_than(meta["earned_rung"], declared):
        meta["plugin_rung_ok"] = False
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


def _atom_pool(root: Path, manifests: dict[str, dict[str, str]]) -> dict[str, dict]:
    atoms: dict[str, dict] = {}

    def write(name: str, env: dict, certifiable: bool, rung: str, checker_hash: str = "") -> None:
        path = root / f"{name}.barrier.json"
        path.write_text(json.dumps(env, sort_keys=True) + "\n", encoding="utf-8")
        atoms[name] = {
            "env": env,
            "path": path,
            "certifiable": certifiable,
            "rung": rung,
            "hash": checker_hash,
        }

    good_a = _base_env(
        "fuzz-atom-good-a",
        {"kind": "external-rup", "manifest": manifests["rup"]["path"], "cert_artifact": "certificate"},
        "R3",
    )
    write("good-a", good_a, True, "R3", manifests["rup"]["hash"])

    good_b = _base_env(
        "fuzz-atom-good-b",
        {"kind": "external-rup", "manifest": manifests["rup_alt"]["path"], "cert_artifact": "certificate"},
        "R3",
    )
    write("good-b", good_b, True, "R3", manifests["rup_alt"]["hash"])

    bad_hash = copy.deepcopy(good_a)
    bad_hash["id"] = "fuzz-atom-bad-hash"
    bad_hash["artifacts"][0]["sha256"] = "f" * 64
    write("bad-hash", bad_hash, False, "R3", manifests["rup"]["hash"])

    deferred = _base_env(
        "fuzz-atom-deferred",
        {
            "kind": "external-rup",
            "manifest": manifests["dynamic"]["path"],
            "cert_artifact": "certificate",
            "fuzz_output": {"mode": "json", "verdict": "DEFERRED", "rung": "R3"},
        },
        "R3",
    )
    write("deferred", deferred, False, "R3", manifests["dynamic"]["hash"])

    over_ceiling = copy.deepcopy(good_a)
    over_ceiling["id"] = "fuzz-atom-over-ceiling"
    over_ceiling["rung"]["level"] = "R2"
    write("over-ceiling", over_ceiling, False, "R2", manifests["rup"]["hash"])
    return atoms


def _composed_case(rng: random.Random, case_id: str, atoms: dict[str, dict]) -> tuple[dict, dict]:
    parts = rng.sample(list(atoms), rng.choice([1, 2, 3]))
    step_rung = rng.choice(spec_runner.RUNG_ORDER[:4])
    weakest = step_rung
    all_certifiable = True
    for name in parts:
        all_certifiable = all_certifiable and atoms[name]["certifiable"]
        weakest = _weaker(weakest, atoms[name]["rung"])
    declared = rng.choice(spec_runner.RUNG_ORDER)
    env = _base_env(
        case_id,
        {"kind": "composed", "composition": {"sub_barriers": [atoms[name]["env"]["id"] for name in parts], "step": {"rung": step_rung}}},
        declared,
    )
    env["certificate"] = {"kind": "composition"}
    env.pop("artifacts", None)
    return env, {"structurally_certifiable": all_certifiable and declared == weakest}


def _multi_region_case(rng: random.Random, case_id: str) -> tuple[dict, dict]:
    region_pool = [
        {
            "region": "rup-a",
            "rung": "R3",
            "checker": {"kind": "rup-python", "cert": "certs/samples_w33.cert"},
            "certificate": {"kind": "lrat-flat", "path": "certs/samples_w33.cert", "sha256": GOOD_SHA},
            "certifiable": True,
        },
        {
            "region": "manual-tail",
            "rung": "R4",
            "checker": {"kind": "manual", "promote_recipe": "fuzz deferred region"},
            "certificate": {"kind": "manual"},
            "certifiable": False,
        },
        {
            "region": "over-ceiling",
            "rung": "R2",
            "checker": {"kind": "rup-python", "cert": "certs/samples_w33.cert"},
            "certificate": {"kind": "lrat-flat", "path": "certs/samples_w33.cert", "sha256": GOOD_SHA},
            "certifiable": False,
        },
    ]
    regions = rng.sample(region_pool, rng.choice([1, 2, 3]))
    weakest = regions[0]["rung"]
    all_certifiable = True
    for region in regions:
        all_certifiable = all_certifiable and region["certifiable"]
        weakest = _weaker(weakest, region["rung"])
    declared = rng.choice(spec_runner.RUNG_ORDER)
    env = _base_env(case_id, {"kind": "multi-region", "regions": regions}, declared)
    env["certificate"] = {"kind": "multi-region"}
    env.pop("artifacts", None)
    return env, {"structurally_certifiable": all_certifiable and declared == weakest}


def _quorum_case(
    rng: random.Random,
    case_id: str,
    manifests: dict[str, dict[str, str]],
) -> tuple[dict, dict]:
    member_specs = [
        ("rup", True, "R3", manifests["rup"]["hash"]),
        ("rup_alt", True, "R3", manifests["rup_alt"]["hash"]),
        ("liar", False, "R3", manifests["liar"]["hash"]),
        ("rup_bad_hash", False, "R3", manifests["rup_bad_hash"]["hash"]),
        ("dynamic_bad_hash", False, "R3", manifests["dynamic_bad_hash"]["hash"]),
    ]
    chosen = rng.choices(member_specs, k=rng.choice([1, 2, 3]))
    required = rng.randint(1, max(1, len(chosen)))
    declared = rng.choice(spec_runner.RUNG_ORDER)
    members = [{"kind": "external-rup", "manifest": manifests[name]["path"], "cert_artifact": "certificate"} for name, *_ in chosen]
    env = _base_env(case_id, {"kind": "quorum", "quorum": {"required": required, "members": members}}, declared)
    counted = [
        {"hash": h, "rung": rung}
        for _name, certifies, rung, h in chosen
        if certifies and _rung_at_least(rung, declared) and not _stronger_than(declared, "R3")
    ]
    distinct_count = len({row["hash"] for row in counted})
    return env, {"structurally_certifiable": distinct_count >= required}


def _build_case(
    rng: random.Random,
    case_id: int,
    manifests: dict[str, dict[str, str]],
    atoms: dict[str, dict],
) -> tuple[dict, dict]:
    mode = rng.choices(["external", "composed", "multi-region", "quorum"], weights=[60, 14, 12, 14], k=1)[0]
    cid = f"fuzz-{case_id:05d}"
    if mode == "composed":
        return _composed_case(rng, cid, atoms)
    if mode == "multi-region":
        return _multi_region_case(rng, cid)
    if mode == "quorum":
        return _quorum_case(rng, cid, manifests)
    return _external_case(rng, cid, manifests)


def _record_for(env: dict, envelope_path: Path, index: dict) -> dict:
    loaded = copy.deepcopy(env)
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
        if "artifacts" in record and any(not a.get("verified") for a in record["artifacts"]):
            raise AssertionError(f"case {case_id}: CERTIFIED with unverified artifact")
    elif meta["structurally_certifiable"] and record.get("reason_code") == "OK":
        raise AssertionError(f"case {case_id}: OK reason on non-certified record")


def run(cases: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    temp_root = Path(tempfile.mkdtemp(prefix=".fuzz_plugins_", dir=ROOT))
    envelope_root = Path(tempfile.mkdtemp(prefix="barrier-fuzz-envelopes-"))
    counts = {"cases": 0, "certified": 0, "refused": 0, "deferred": 0, "unverifiable": 0}
    try:
        manifests = _write_dynamic_plugin(temp_root)
        atoms = _atom_pool(envelope_root, manifests)
        index = {row["env"]["id"]: (row["env"], row["path"]) for row in atoms.values()}
        for case_id in range(cases):
            env, meta = _build_case(rng, case_id, manifests, atoms)
            envelope_path = envelope_root / f"{env['id']}.barrier.json"
            envelope_path.write_text(json.dumps(env, sort_keys=True) + "\n", encoding="utf-8")
            try:
                record = _record_for(env, envelope_path, index)
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
