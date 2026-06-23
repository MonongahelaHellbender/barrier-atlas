#!/usr/bin/env python3
"""Plugin-capable runner for Barrier Atlas Spec v0.1.

External checkers are hash-pinned executables that propose verdicts. This runner
reuses the Phase A trusted base in spec_runner for artifact binding, rung
ceilings, verdict records, and in-process dispatch; the new code only handles
manifest identity checks, artifact staging, subprocess invocation, and plugin
output/rung validation.
"""
import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_runner  # noqa: E402

ATLAS_ROOT = spec_runner.ATLAS_ROOT


def _safe_repo_path(raw: str) -> Path | None:
    if not raw or "://" in raw:
        return None
    p = Path(raw)
    if p.is_absolute() or ".." in p.parts or raw.startswith("~") or raw[1:3] in (":\\", ":/"):
        return None
    resolved = (ATLAS_ROOT / p).resolve()
    if not spec_runner._is_relative_to(resolved, ATLAS_ROOT):
        return None
    return resolved


def _command_part(raw: str) -> str | None:
    if "/" not in raw and "\\" not in raw:
        return raw
    resolved = _safe_repo_path(raw)
    if resolved is None or not resolved.exists():
        return None
    return str(resolved)


def _load_registry() -> dict:
    path = ATLAS_ROOT / "spec" / "checker-registry.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _manifest_path_for(env: dict) -> Path | None:
    checker = env.get("checker", {})
    raw = checker.get("manifest")
    if raw:
        return _safe_repo_path(str(raw))
    registry = _load_registry()
    raw = registry.get(checker.get("kind", ""))
    if raw:
        return _safe_repo_path(str(raw))
    return None


def _load_manifest(env: dict) -> tuple[dict | None, spec_runner.Result | None]:
    path = _manifest_path_for(env)
    if path is None or not path.exists():
        return None, spec_runner.Result(
            spec_runner.REFUSED,
            "MANIFEST_INVALID",
            "checker manifest missing or outside repo",
            final_rung=env.get("rung", {}).get("level", ""),
        )
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, spec_runner.Result(
            spec_runner.REFUSED,
            "MANIFEST_INVALID",
            f"checker manifest is not valid JSON: {e}",
            final_rung=env.get("rung", {}).get("level", ""),
        )
    required = ("name", "version", "kind", "command", "entrypoint", "sha256")
    if any(k not in manifest for k in required):
        return None, spec_runner.Result(
            spec_runner.REFUSED,
            "MANIFEST_INVALID",
            "checker manifest missing required fields",
            final_rung=env.get("rung", {}).get("level", ""),
        )
    if manifest.get("kind") != env.get("checker", {}).get("kind"):
        return None, spec_runner.Result(
            spec_runner.REFUSED,
            "MANIFEST_INVALID",
            f"manifest kind {manifest.get('kind')!r} does not match envelope checker kind",
            final_rung=env.get("rung", {}).get("level", ""),
        )
    if not isinstance(manifest.get("command"), list) or not all(isinstance(x, str) for x in manifest["command"]):
        return None, spec_runner.Result(
            spec_runner.REFUSED,
            "MANIFEST_INVALID",
            "manifest command must be a string array",
            final_rung=env.get("rung", {}).get("level", ""),
        )
    entrypoint = _safe_repo_path(str(manifest.get("entrypoint", "")))
    if entrypoint is None or not entrypoint.exists():
        return None, spec_runner.Result(
            spec_runner.REFUSED,
            "MANIFEST_INVALID",
            "manifest entrypoint missing or outside repo",
            final_rung=env.get("rung", {}).get("level", ""),
        )
    got = spec_runner._sha256_file(entrypoint)
    if got != str(manifest.get("sha256", "")).strip():
        manifest = dict(manifest)
        manifest["_entrypoint_hash"] = got
        return manifest, spec_runner.Result(
            spec_runner.REFUSED,
            "CHECKER_HASH_MISMATCH",
            f"checker entrypoint sha256 mismatch: {got[:16]}...",
            final_rung=env.get("rung", {}).get("level", ""),
        )
    manifest = dict(manifest)
    manifest["_entrypoint_hash"] = got
    return manifest, None


def _external_checker(env: dict) -> bool:
    checker = env.get("checker", {})
    return bool(checker.get("manifest")) or checker.get("kind") in _load_registry()


def _artifact_source_map(env: dict, envelope_path: Path) -> dict[str, Path]:
    sources = {}
    for spec in spec_runner._artifact_specs(env):
        artifact_id = spec.get("id") or spec.get("role") or "artifact"
        if "/" in artifact_id or "\\" in artifact_id or artifact_id in ("", ".", ".."):
            continue
        resolved, _error = spec_runner._resolve_artifact_path(str(spec.get("path", "")), envelope_path)
        if resolved is not None:
            sources[artifact_id] = resolved
    return sources


def _sanitized_envelope(env: dict) -> dict:
    sanitized = copy.deepcopy(env)
    for artifact in sanitized.get("artifacts", []):
        artifact.pop("path", None)
        artifact.pop("uri", None)
    if "certificate" in sanitized:
        sanitized["certificate"].pop("path", None)
    return sanitized


def _stage_artifacts(env: dict, envelope_path: Path, temp_dir: Path) -> spec_runner.Result | None:
    sources = _artifact_source_map(env, envelope_path)
    for artifact in env.get("artifacts", []):
        artifact_id = artifact.get("id") or artifact.get("role") or "artifact"
        if artifact_id not in sources:
            return spec_runner.Result(
                spec_runner.REFUSED,
                "PATH_REJECTED",
                f"artifact id {artifact_id!r} cannot be staged safely",
                final_rung=env.get("rung", {}).get("level", ""),
            )
        shutil.copyfile(sources[artifact_id], temp_dir / artifact_id)
    return None


def _run_plugin(env: dict, envelope_path: Path, manifest: dict) -> spec_runner.Result:
    declared = env.get("rung", {}).get("level", "")
    kind = env.get("checker", {}).get("kind", "")

    ceiling = spec_runner.ATOMIC_CEILINGS.get(kind)
    if ceiling and declared and spec_runner._stronger_than(declared, ceiling):
        return spec_runner.Result(
            spec_runner.REFUSED,
            "RUNG_CEILING_EXCEEDED",
            f"declared {declared} is stronger than {kind} ceiling {ceiling}",
            final_rung=declared,
        )

    # A malformed envelope-supplied timeout must emit one fail-closed record,
    # not crash the runner or silently normalize bad checker configuration.
    try:
        timeout = int(env.get("checker", {}).get("timeout_seconds", 60))
    except (TypeError, ValueError):
        return spec_runner.Result(
            spec_runner.UNVERIFIABLE,
            "CHECKER_ERROR",
            "checker timeout_seconds is not an integer",
            raw_verdict=spec_runner.UNVERIFIABLE,
            final_rung=declared,
        )
    if timeout <= 0:
        return spec_runner.Result(
            spec_runner.UNVERIFIABLE,
            "CHECKER_ERROR",
            "checker timeout_seconds must be positive",
            raw_verdict=spec_runner.UNVERIFIABLE,
            final_rung=declared,
        )

    with tempfile.TemporaryDirectory(prefix="barrier-plugin-") as td:
        temp_dir = Path(td)
        staged_error = _stage_artifacts(env, envelope_path, temp_dir)
        if staged_error:
            return staged_error
        staged_envelope = temp_dir / "envelope.json"
        staged_envelope.write_text(json.dumps(_sanitized_envelope(env), sort_keys=True), encoding="utf-8")

        command = []
        for part in manifest["command"]:
            resolved = _command_part(part)
            if resolved is None:
                return spec_runner.Result(
                    spec_runner.REFUSED,
                    "MANIFEST_INVALID",
                    f"manifest command part {part!r} is not runnable",
                    final_rung=declared,
                )
            command.append(resolved)
        command += ["--envelope", str(staged_envelope), "--artifacts-dir", str(temp_dir)]
        try:
            proc = subprocess.run(command, cwd=str(ATLAS_ROOT), capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return spec_runner.Result(
                spec_runner.UNVERIFIABLE,
                "CHECKER_TIMEOUT",
                f"checker timed out after {timeout}s",
                raw_verdict=spec_runner.UNVERIFIABLE,
                final_rung=declared,
            )
        except Exception as e:  # noqa: BLE001
            return spec_runner.Result(
                spec_runner.UNVERIFIABLE,
                "CHECKER_ERROR",
                f"could not run checker: {e}",
                raw_verdict=spec_runner.UNVERIFIABLE,
                final_rung=declared,
            )

    if proc.returncode != 0:
        return spec_runner.Result(
            spec_runner.UNVERIFIABLE,
            "CHECKER_ERROR",
            f"checker exited nonzero ({proc.returncode})",
            raw_verdict=spec_runner.UNVERIFIABLE,
            final_rung=declared,
        )
    try:
        output = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as e:
        return spec_runner.Result(
            spec_runner.UNVERIFIABLE,
            "CHECKER_ERROR",
            f"checker stdout was not one JSON verdict: {e}",
            raw_verdict=spec_runner.UNVERIFIABLE,
            final_rung=declared,
        )

    if not isinstance(output, dict):
        return spec_runner.Result(
            spec_runner.UNVERIFIABLE,
            "CHECKER_ERROR",
            "checker stdout was not a JSON object",
            raw_verdict=spec_runner.UNVERIFIABLE,
            final_rung=declared,
        )
    verdict = output.get("verdict")
    detail = str(output.get("detail", ""))
    returned_rung = output.get("rung")
    if verdict not in spec_runner.VALID_VERDICTS or returned_rung not in spec_runner.RUNG_ORDER:
        return spec_runner.Result(
            spec_runner.UNVERIFIABLE,
            "CHECKER_ERROR",
            "checker emitted an illegal verdict object",
            raw_verdict=spec_runner.UNVERIFIABLE,
            final_rung=declared,
        )
    if ceiling and spec_runner._stronger_than(returned_rung, ceiling):
        return spec_runner.Result(
            spec_runner.REFUSED,
            "RUNG_CEILING_EXCEEDED",
            f"checker returned rung {returned_rung} stronger than {kind} ceiling {ceiling}",
            raw_verdict=verdict,
            final_rung=declared,
        )
    if declared and spec_runner._stronger_than(returned_rung, declared):
        return spec_runner.Result(
            spec_runner.REFUSED,
            "RUNG_LAUNDERING",
            f"checker returned rung {returned_rung} stronger than declared {declared}",
            raw_verdict=verdict,
            final_rung=declared,
        )
    return spec_runner.Result(verdict, "OK" if verdict == spec_runner.CERTIFIED else "CHECKER_ERROR",
                              detail, raw_verdict=verdict, final_rung=declared)


def evaluate(env: dict, envelope_path: Path, index: dict) -> spec_runner.Result:
    if not _external_checker(env):
        return spec_runner.evaluate(env, envelope_path, index)

    declared = env.get("rung", {}).get("level", "")
    manifest, manifest_error = _load_manifest(env)
    if manifest:
        env["_plugin_record"] = {"manifest": manifest}
    if manifest_error:
        return manifest_error

    preflight, artifacts = spec_runner._verify_artifacts(env, envelope_path)
    if preflight:
        preflight.final_rung = declared
        return preflight

    result = _run_plugin(env, envelope_path, manifest)
    result.artifacts = artifacts
    return result


def _record_env(env: dict) -> dict:
    manifest = env.pop("_plugin_record", {}).get("manifest") if "_plugin_record" in env else None
    if not manifest:
        return env
    record_env = copy.deepcopy(env)
    record_env["checker"]["name"] = manifest["name"]
    record_env["checker"]["version"] = manifest["version"]
    record_env["checker"]["hash"] = manifest["_entrypoint_hash"]
    return record_env


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--envelope", required=True, help="barrier envelope JSON")
    args = ap.parse_args(argv)

    envelope_path = Path(args.envelope).resolve()
    try:
        env = json.loads(envelope_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fallback = {"id": "", "rung": {"level": ""}, "checker": {"kind": "unknown"}}
        result = spec_runner.Result(spec_runner.UNVERIFIABLE, "CHECKER_ERROR", f"could not read envelope: {e}")
        print(json.dumps(spec_runner.make_record(fallback, envelope_path, result), sort_keys=True))
        return 0

    index = spec_runner._load_index(envelope_path)
    result = evaluate(env, envelope_path, index)
    record_env = _record_env(env)
    print(json.dumps(spec_runner.make_record(record_env, envelope_path, result),
                     sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
