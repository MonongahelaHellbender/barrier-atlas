#!/usr/bin/env python3
"""Reference runner for Barrier Atlas Spec v0.1.

This wraps the existing in-process atlas checkers with runner-owned gates:
artifact containment/hash checks, atomic rung ceilings, min-trust composition, and
stable verdict records. It intentionally does not implement external plugins.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import barrier_check  # noqa: E402

ATLAS_ROOT = Path(__file__).resolve().parent.parent

CERTIFIED = "CERTIFIED"
REFUSED = "REFUSED"
DEFERRED = "DEFERRED"
UNVERIFIABLE = "UNVERIFIABLE-HERE"
VALID_VERDICTS = {CERTIFIED, REFUSED, DEFERRED, UNVERIFIABLE}

RUNG_ORDER = ["R0", "R1", "R2", "R3", "R4", "R5"]
ATOMIC_CEILINGS = {
    "lean-axioms": "R0",
    "lratcheck": "R2",
    "rup-python": "R3",
    "external-rup": "R3",
    "hybrid-schur-vdw-exhaustive": "R3",
    "claim-stress": "R4",
}
REASON_CODES = {
    "OK",
    "ARTIFACT_HASH_MISMATCH",
    "ARTIFACT_MISSING",
    "PATH_REJECTED",
    "RUNG_CEILING_EXCEEDED",
    "RUNG_LAUNDERING",
    "WEAK_ANSWER",
    "INCOMPLETE_ANSWERS",
    "LLM_NOT_A_GATE",
    "UNKNOWN_CHECKER",
    "CHECKER_ERROR",
    "MANIFEST_INVALID",
    "CHECKER_HASH_MISMATCH",
    "CHECKER_TIMEOUT",
    "DEFERRED_PENDING_HUMAN",
    "WEAK_SUBBARRIER",
}
CHECKER_IMPL_FILES = {
    "lean-axioms": "tools/barrier_check.py",
    "lratcheck": "tools/barrier_check.py",
    "rup-python": "tools/rup_check.py",
    "hybrid-schur-vdw-exhaustive": "tools/hybrid_schur_vdw_check.py",
    "claim-stress": "tools/claim_stress_check.py",
    "composed": "tools/spec_runner.py",
    "multi-region": "tools/spec_runner.py",
    "manual": "tools/spec_runner.py",
}

class Result:
    def __init__(self, final_verdict, reason_code, detail, raw_verdict=None,
                 final_rung=None, artifacts=None):
        self.final_verdict = final_verdict
        self.reason_code = reason_code
        self.detail = detail
        self.raw_verdict = raw_verdict or final_verdict
        self.final_rung = final_rung
        self.artifacts = artifacts or []


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _stronger_than(a: str, b: str) -> bool:
    return RUNG_ORDER.index(a) < RUNG_ORDER.index(b)


def _weaker(a: str, b: str) -> str:
    return a if RUNG_ORDER.index(a) >= RUNG_ORDER.index(b) else b


def _artifact_specs(env: dict) -> list[dict]:
    if env.get("artifacts"):
        return list(env["artifacts"])
    cert = env.get("certificate", {})
    if cert.get("path"):
        return [{
            "id": "certificate",
            "type": cert.get("kind", "certificate"),
            "role": "certificate",
            "path": cert["path"],
            "sha256": cert.get("sha256", ""),
        }]
    return []


def _resolve_artifact_path(raw_path: str, envelope_path: Path) -> tuple[Path | None, str | None]:
    if not raw_path or "://" in raw_path:
        return None, "artifact path is absent or remote"
    if raw_path.startswith("~") or raw_path[1:3] in (":\\", ":/"):
        return None, "artifact path must not be a home-relative or drive-absolute path"
    p = Path(raw_path)
    if p.is_absolute() or ".." in p.parts:
        return None, "artifact path must be relative and must not contain '..'"

    for base in (ATLAS_ROOT, envelope_path.parent):
        base = base.resolve()
        candidate = (base / p).resolve()
        if candidate.exists():
            if not _is_relative_to(candidate, base):
                return None, "artifact path escapes its allowed base"
            return candidate, None

    return (ATLAS_ROOT / p).resolve(), None


def _verify_artifacts(env: dict, envelope_path: Path) -> tuple[Result | None, list[dict]]:
    verified = []
    for spec in _artifact_specs(env):
        raw_path = str(spec.get("path", ""))
        resolved, error = _resolve_artifact_path(raw_path, envelope_path)
        artifact_id = spec.get("id") or spec.get("role") or "artifact"
        if error:
            return Result(REFUSED, "PATH_REJECTED", error, artifacts=verified), verified
        if resolved is None or not resolved.exists():
            return Result(REFUSED, "ARTIFACT_MISSING",
                          f"artifact '{artifact_id}' missing at {raw_path}",
                          artifacts=verified), verified
        want = str(spec.get("sha256", "")).strip()
        if not want:
            return Result(REFUSED, "ARTIFACT_HASH_MISMATCH",
                          f"artifact '{artifact_id}' has no declared sha256",
                          artifacts=verified), verified
        got = _sha256_file(resolved)
        if got != want:
            return Result(REFUSED, "ARTIFACT_HASH_MISMATCH",
                          f"artifact '{artifact_id}' sha256 mismatch: {got[:16]}...",
                          artifacts=verified), verified
        verified.append({
            "id": artifact_id,
            "path": raw_path,
            "sha256": got,
            "verified": True,
        })
    return None, verified


def _checker_info(env: dict) -> dict:
    checker = env.get("checker", {})
    kind = checker.get("kind", "unknown")
    impl = CHECKER_IMPL_FILES.get(kind)
    impl_hash = ""
    if impl and (ATLAS_ROOT / impl).exists():
        impl_hash = _sha256_file(ATLAS_ROOT / impl)
    return {
        "kind": kind,
        "name": checker.get("name", f"barrier-atlas:{kind}"),
        "version": checker.get("version", "0.1"),
        "hash": checker.get("hash", impl_hash),
    }


def _classify_checker_result(kind: str, status: str, detail: str) -> str:
    blob = detail.lower()
    if status == CERTIFIED:
        return "OK"
    if kind == "claim-stress":
        if "completeness" in blob:
            return "INCOMPLETE_ANSWERS"
        if "adequacy" in blob:
            return "WEAK_ANSWER"
        if "not a correctness gate" in blob:
            return "LLM_NOT_A_GATE"
        if status == DEFERRED:
            return "DEFERRED_PENDING_HUMAN"
    if kind == "manual" and status == DEFERRED:
        return "DEFERRED_PENDING_HUMAN"
    if status == UNVERIFIABLE:
        if "unknown checker" in blob:
            return "UNKNOWN_CHECKER"
        return "CHECKER_ERROR"
    return "CHECKER_ERROR"


def _load_index(envelope_path: Path) -> dict[str, tuple[dict, Path]]:
    fixtures_root = ATLAS_ROOT / "spec" / "conformance" / "fixtures"
    if _is_relative_to(envelope_path.resolve(), fixtures_root.resolve()):
        paths = sorted(fixtures_root.rglob("*.barrier.json"))
    else:
        paths = sorted((ATLAS_ROOT / "barriers").glob("*.barrier.json"))
    index = {}
    for p in paths:
        if p.name.startswith("_test_"):
            continue
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "id" in env:
            index[env["id"]] = (env, p)
    return index


def _evaluate_composed(env: dict, envelope_path: Path, index: dict, stack: set[str]) -> Result:
    comp = env.get("checker", {}).get("composition", {})
    declared = env.get("rung", {}).get("level")
    weakest = comp.get("step", {}).get("rung", declared)
    artifacts = []

    if env.get("id") in stack:
        return Result(REFUSED, "RUNG_LAUNDERING", "composition cycle", final_rung=declared)
    stack.add(env.get("id"))
    try:
        parts = []
        for sid in comp.get("sub_barriers", []):
            if sid not in index:
                return Result(UNVERIFIABLE, "WEAK_SUBBARRIER",
                              f"sub-barrier '{sid}' not found", final_rung=declared,
                              artifacts=artifacts)
            sub_env, sub_path = index[sid]
            sub = evaluate(sub_env, sub_path, index, stack)
            parts.append((sid, sub_env.get("rung", {}).get("level", "?"), sub.final_verdict))
            for art in sub.artifacts:
                art2 = dict(art)
                art2["id"] = f"{sid}:{art2['id']}"
                artifacts.append(art2)
            if sub.final_verdict != CERTIFIED:
                return Result(sub.final_verdict, "WEAK_SUBBARRIER",
                              f"sub '{sid}' is {sub.final_verdict}: {sub.detail}",
                              raw_verdict=sub.raw_verdict, final_rung=declared,
                              artifacts=artifacts)
            weakest = _weaker(weakest, sub_env["rung"]["level"])
    finally:
        stack.discard(env.get("id"))

    if declared != weakest:
        chain = "; ".join(f"{sid}={rung}:{status}" for sid, rung, status in parts)
        return Result(REFUSED, "RUNG_LAUNDERING",
                      f"declared {declared} != min-trust {weakest} ({chain})",
                      final_rung=declared, artifacts=artifacts)
    return Result(CERTIFIED, "OK", f"min-trust {weakest}", final_rung=weakest,
                  artifacts=artifacts)


def _evaluate_multi_region(env: dict, envelope_path: Path, index: dict, stack: set[str]) -> Result:
    declared = env.get("rung", {}).get("level")
    weakest = None
    artifacts = []
    results = []
    for region in env.get("checker", {}).get("regions", []):
        mini = {
            "id": f"{env.get('id')}#{region.get('region', '?')}",
            "schema_version": env.get("schema_version", "0.1"),
            "claim": env.get("claim", {}),
            "domain": env.get("domain", "multi-region"),
            "rung": {"level": region["rung"], "name": "region", "trusted_base": []},
            "certificate": region.get("certificate", {"kind": "region"}),
            "checker": region["checker"],
            "status": "live",
            "provenance": env.get("provenance", {"source_package": "multi-region"}),
            "one_directional": env.get("one_directional", "multi-region sub-check"),
        }
        res = evaluate(mini, envelope_path, index, stack)
        results.append((region.get("region", "?"), region["rung"], res.final_verdict))
        for art in res.artifacts:
            art2 = dict(art)
            art2["id"] = f"{region.get('region', '?')}:{art2['id']}"
            artifacts.append(art2)
        if res.final_verdict != CERTIFIED:
            return Result(res.final_verdict, "WEAK_SUBBARRIER",
                          f"region '{region.get('region', '?')}' is {res.final_verdict}: {res.detail}",
                          raw_verdict=res.raw_verdict, final_rung=declared,
                          artifacts=artifacts)
        weakest = region["rung"] if weakest is None else _weaker(weakest, region["rung"])

    if declared != weakest:
        chain = "; ".join(f"{name}={rung}:{status}" for name, rung, status in results)
        return Result(REFUSED, "RUNG_LAUNDERING",
                      f"declared {declared} != min-trust {weakest} ({chain})",
                      final_rung=declared, artifacts=artifacts)
    return Result(CERTIFIED, "OK", f"min-trust {weakest}", final_rung=weakest,
                  artifacts=artifacts)


def evaluate(env: dict, envelope_path: Path, index: dict, stack: set[str] | None = None) -> Result:
    stack = stack or set()
    declared = env.get("rung", {}).get("level")
    kind = env.get("checker", {}).get("kind", "")

    preflight, artifacts = _verify_artifacts(env, envelope_path)
    if preflight:
        preflight.final_rung = declared
        return preflight

    if kind == "composed":
        return _evaluate_composed(env, envelope_path, index, stack)
    if kind == "multi-region":
        return _evaluate_multi_region(env, envelope_path, index, stack)
    if kind == "manual":
        return Result(DEFERRED, "DEFERRED_PENDING_HUMAN",
                      env.get("checker", {}).get("promote_recipe", "manual/deferred barrier"),
                      final_rung=declared, artifacts=artifacts)
    if kind not in barrier_check.CHECKERS:
        return Result(UNVERIFIABLE, "UNKNOWN_CHECKER",
                      f"unknown checker kind '{kind}'", final_rung=declared,
                      artifacts=artifacts)

    ceiling = ATOMIC_CEILINGS.get(kind)
    if ceiling and declared and _stronger_than(declared, ceiling):
        return Result(REFUSED, "RUNG_CEILING_EXCEEDED",
                      f"declared {declared} is stronger than {kind} ceiling {ceiling}",
                      final_rung=declared, artifacts=artifacts)

    try:
        raw_status, detail = barrier_check.run(copy.deepcopy(env))
    except Exception as e:  # noqa: BLE001
        return Result(UNVERIFIABLE, "CHECKER_ERROR", f"checker crashed: {e}",
                      raw_verdict=UNVERIFIABLE, final_rung=declared, artifacts=artifacts)
    if raw_status not in VALID_VERDICTS:
        return Result(UNVERIFIABLE, "CHECKER_ERROR",
                      f"checker emitted illegal verdict {raw_status!r}",
                      raw_verdict=UNVERIFIABLE, final_rung=declared, artifacts=artifacts)
    reason = _classify_checker_result(kind, raw_status, detail)
    return Result(raw_status, reason, detail, raw_verdict=raw_status,
                  final_rung=declared, artifacts=artifacts)


def _record_core(record: dict) -> dict:
    artifacts = sorted(
        ({"id": a["id"], "sha256": a["sha256"], "verified": bool(a["verified"])}
         for a in record.get("artifacts", [])),
        key=lambda a: a["id"],
    )
    return {
        "schema_version": record["schema_version"],
        "envelope_id": record["envelope_id"],
        "envelope_sha256": record["envelope_sha256"],
        "artifacts": artifacts,
        "checker": {
            "kind": record["checker"]["kind"],
            "name": record["checker"]["name"],
            "version": record["checker"]["version"],
            "hash": record["checker"]["hash"],
        },
        "raw_checker_verdict": record["raw_checker_verdict"],
        "final_verdict": record["final_verdict"],
        "final_rung": record["final_rung"],
        "reason_code": record["reason_code"],
    }


def _core_hash(record: dict) -> str:
    blob = json.dumps(_record_core(record), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return _sha256_text(blob)


def make_record(env: dict, envelope_path: Path, result: Result) -> dict:
    checker = _checker_info(env)
    text = envelope_path.read_text(encoding="utf-8")
    record = {
        "schema_version": "0.1",
        "envelope_id": env.get("id", ""),
        "envelope_sha256": _sha256_text(text),
        "artifacts": result.artifacts,
        "checker": checker,
        "raw_checker_verdict": result.raw_verdict,
        "final_verdict": result.final_verdict,
        "final_rung": result.final_rung or env.get("rung", {}).get("level", ""),
        "reason_code": result.reason_code,
        "detail": result.detail,
    }
    if record["reason_code"] not in REASON_CODES:
        record["final_verdict"] = UNVERIFIABLE
        record["reason_code"] = "CHECKER_ERROR"
        record["detail"] = "runner produced an unknown reason code"
    record["record_core_sha256"] = _core_hash(record)
    return record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--envelope", required=True, help="barrier envelope JSON")
    args = ap.parse_args(argv)

    envelope_path = Path(args.envelope).resolve()
    try:
        env = json.loads(envelope_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fallback = {
            "id": "",
            "rung": {"level": ""},
            "checker": {"kind": "unknown"},
        }
        result = Result(UNVERIFIABLE, "CHECKER_ERROR", f"could not read envelope: {e}")
        print(json.dumps(make_record(fallback, envelope_path, result), sort_keys=True))
        return 0

    index = _load_index(envelope_path)
    result = evaluate(env, envelope_path, index)
    print(json.dumps(make_record(env, envelope_path, result), sort_keys=True,
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
