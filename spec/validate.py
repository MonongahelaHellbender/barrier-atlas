#!/usr/bin/env python3
"""Validate Barrier Atlas v0.1 envelopes without external dependencies."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALID_VERDICTS = {"CERTIFIED", "REFUSED", "DEFERRED", "UNVERIFIABLE-HERE"}
VALID_REASON_CODES = {
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
RUNGS = {"R0", "R1", "R2", "R3", "R4", "R5"}

def _err(path: Path, msg: str) -> str:
    return f"{path.relative_to(ROOT)}: {msg}"


def _check_artifact_path(path: Path, raw: str) -> str | None:
    if not raw:
        return "artifact path is empty"
    p = Path(raw)
    if p.is_absolute() or ".." in p.parts or "://" in raw or raw.startswith("~") or raw[1:3] in (":\\", ":/"):
        return "artifact path must be local, relative, and contain no '..'"
    return None


def validate_env(path: Path) -> list[str]:
    errors = []
    try:
        env = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [_err(path, f"invalid JSON: {e}")]

    for key in ("id", "schema_version", "claim", "domain", "rung", "certificate",
                "checker", "status", "provenance", "one_directional"):
        if key not in env:
            errors.append(_err(path, f"missing required field {key!r}"))
    if errors:
        return errors

    if env["schema_version"] != "0.1":
        errors.append(_err(path, "schema_version must be '0.1'"))
    if env["status"] not in {"live", "deferred"}:
        errors.append(_err(path, "status must be live or deferred"))
    if env["claim"].get("kind") != "impossibility":
        errors.append(_err(path, "claim.kind must be impossibility"))
    if env["rung"].get("level") not in RUNGS:
        errors.append(_err(path, "rung.level must be R0..R5"))
    if "kind" not in env["certificate"]:
        errors.append(_err(path, "certificate.kind is required"))
    if "kind" not in env["checker"]:
        errors.append(_err(path, "checker.kind is required"))
    if env.get("expected_verdict") and env["expected_verdict"] not in VALID_VERDICTS:
        errors.append(_err(path, "expected_verdict is not a valid verdict"))
    if env.get("expected_reason_code") and env["expected_reason_code"] not in VALID_REASON_CODES:
        errors.append(_err(path, "expected_reason_code is not a valid reason code"))

    for artifact in env.get("artifacts", []):
        for key in ("id", "type", "sha256"):
            if key not in artifact:
                errors.append(_err(path, f"artifact missing {key!r}"))
        if "path" in artifact:
            path_error = _check_artifact_path(path, artifact["path"])
            if path_error:
                errors.append(_err(path, path_error))

    return errors


def validate_manifest(path: Path) -> list[str]:
    errors = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [_err(path, f"invalid JSON: {e}")]
    for key in ("name", "version", "kind", "command", "entrypoint", "sha256"):
        if key not in manifest:
            errors.append(_err(path, f"manifest missing required field {key!r}"))
    if errors:
        return errors
    if not isinstance(manifest["command"], list) or not all(isinstance(x, str) for x in manifest["command"]):
        errors.append(_err(path, "manifest.command must be a string array"))
    entry = manifest["entrypoint"]
    p = Path(entry)
    if p.is_absolute() or ".." in p.parts or "://" in entry or entry.startswith("~") or entry[1:3] in (":\\", ":/"):
        errors.append(_err(path, "manifest.entrypoint must be local, relative, and contain no '..'"))
    return errors


def main() -> int:
    paths = sorted((ROOT / "barriers").glob("*.barrier.json"))
    paths += sorted((ROOT / "spec" / "conformance" / "fixtures").rglob("*.barrier.json"))
    errors = []
    for path in paths:
        errors.extend(validate_env(path))
    manifests = sorted((ROOT / "spec" / "checkers").glob("*.manifest.json"))
    for path in manifests:
        errors.extend(validate_manifest(path))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    suffix = f" and {len(manifests)} checker manifests" if manifests else ""
    print(f"validated {len(paths)} barrier envelopes{suffix} against spec v0.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
