#!/usr/bin/env python3
"""Phase E tests for signed and transparency-logged verdict records."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import atlas_log  # noqa: E402
import plugin_runner  # noqa: E402
import signing_common as sc  # noqa: E402
import spec_runner  # noqa: E402
import to_intoto  # noqa: E402


def _record_for(relative_envelope: str) -> dict:
    envelope_path = ROOT / relative_envelope
    env = json.loads(envelope_path.read_text(encoding="utf-8"))
    result = plugin_runner.evaluate(env, envelope_path, spec_runner._load_index(envelope_path))
    record_env = plugin_runner._record_env(env)
    return spec_runner.make_record(record_env, envelope_path, result)


def _write(path: Path, obj: dict) -> None:
    sc.write_json(path, obj)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> dict:
    temp = Path(tempfile.mkdtemp(prefix="barrier-phase-e-"))
    try:
        private_key_path = temp / "keys" / "signing-private.pem"
        public_key_path = temp / "keys" / "signing-public.pem"
        wrong_private_path = temp / "keys" / "wrong-private.pem"
        wrong_public_path = temp / "keys" / "wrong-public.pem"
        sc.write_keypair(private_key_path, public_key_path)
        sc.write_keypair(wrong_private_path, wrong_public_path)
        private_key = sc.load_private_key(private_key_path)
        public_key = sc.load_public_key(public_key_path)
        wrong_private_key = sc.load_private_key(wrong_private_path)
        wrong_public_key = sc.load_public_key(wrong_public_path)

        record = _record_for("spec/conformance/fixtures/10-external-rup.barrier.json")
        _assert(record["final_verdict"] == spec_runner.CERTIFIED, "fixture 10 should certify")
        signature = sc.sign_record(record, private_key, signed_at="2026-06-23T00:00:00Z")

        ok, reason, _detail = sc.verify_record_signature(record, signature, public_key)
        _assert(ok and reason == sc.OK, "valid signature should verify")

        tampered = copy.deepcopy(record)
        tampered["final_verdict"] = spec_runner.REFUSED
        ok, reason, _detail = sc.verify_record_signature(tampered, signature, public_key)
        _assert((not ok) and reason == sc.RECORD_CORE_MISMATCH, "core tamper must fail as RECORD_CORE_MISMATCH")

        ok, reason, _detail = sc.verify_record_signature(record, signature, wrong_public_key)
        _assert((not ok) and reason == sc.SIGNATURE_INVALID, "wrong key must fail as SIGNATURE_INVALID")

        record_path = temp / "record.json"
        signature_path = temp / "signature.json"
        cli_signature_path = temp / "cli-signature.json"
        _write(record_path, record)
        _write(signature_path, signature)

        sign_cli = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "sign_record.py"),
                "--record",
                str(record_path),
                "--private-key",
                str(private_key_path),
                "--out",
                str(cli_signature_path),
                "--signed-at",
                "2026-06-23T00:00:00Z",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _assert(sign_cli.returncode == 0, f"sign_record CLI failed: {sign_cli.stderr}")
        verify_cli = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "verify_record.py"),
                "--record",
                str(record_path),
                "--signature",
                str(cli_signature_path),
                "--public-key",
                str(public_key_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _assert(verify_cli.returncode == 0, f"verify_record CLI failed: {verify_cli.stdout} {verify_cli.stderr}")

        ledger = temp / "LEDGER"
        atlas_log.append_record(record, signature, ledger, public_key, private_key, signed_at="2026-06-23T00:00:01Z")
        ok, reason, _detail = atlas_log.verify_record_inclusion(record, signature, ledger, public_key)
        _assert(ok and reason == atlas_log.LOG_OK, "logged record should verify inclusion")

        second_record = _record_for("spec/conformance/fixtures/01-valid-rup.barrier.json")
        second_signature = sc.sign_record(second_record, private_key, signed_at="2026-06-23T00:00:02Z")
        atlas_log.append_record(
            second_record,
            second_signature,
            ledger,
            public_key,
            private_key,
            signed_at="2026-06-23T00:00:03Z",
        )
        ok, reason, _detail = atlas_log.verify_record_inclusion(second_record, second_signature, ledger, public_key)
        _assert(ok and reason == atlas_log.LOG_OK, "latest logged record should verify inclusion")
        ok, reason, _detail = atlas_log.verify_record_inclusion(record, signature, ledger, public_key)
        _assert(ok and reason == atlas_log.LOG_OK, "earlier logged record should keep a current inclusion proof")

        try:
            atlas_log.append_record(record, signature, ledger, public_key, private_key, signed_at="2026-06-23T00:00:04Z")
        except ValueError as e:
            _assert(str(e).startswith(atlas_log.LOG_DUPLICATE_RECORD), "duplicate record core must be refused")
        else:
            raise AssertionError("duplicate record core must be refused")

        try:
            atlas_log.append_record(
                record,
                signature,
                temp / "BAD_LEDGER",
                public_key,
                wrong_private_key,
                signed_at="2026-06-23T00:00:04Z",
            )
        except ValueError as e:
            _assert(
                str(e).startswith(atlas_log.CHECKPOINT_SIGNATURE_INVALID),
                "checkpoint key mismatch must be refused before writing ledger state",
            )
        else:
            raise AssertionError("checkpoint key mismatch must be refused")

        never_logged = _record_for("spec/conformance/fixtures/11-checker-hash-mismatch.barrier.json")
        never_signature = sc.sign_record(never_logged, private_key, signed_at="2026-06-23T00:00:05Z")
        ok, reason, _detail = atlas_log.verify_record_inclusion(never_logged, never_signature, ledger, public_key)
        _assert((not ok) and reason == atlas_log.LOG_INCLUSION_MISSING, "never-logged record must fail inclusion")

        entries_path = ledger / atlas_log.ENTRIES
        lines = entries_path.read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[0])
        entry["entry"]["record"]["detail"] = "tampered ledger entry"
        lines[0] = json.dumps(entry, sort_keys=True)
        entries_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, reason, _detail = atlas_log.verify_ledger(ledger, public_key)
        _assert((not ok) and reason == atlas_log.LOG_ROOT_MISMATCH, "ledger tamper must break checkpoint root")

        statement = to_intoto.statement_for_record(record)
        subject_digests = {row["name"]: row["digest"]["sha256"] for row in statement["subject"]}
        artifact_digests = {row["id"]: row["sha256"] for row in record["artifacts"]}
        _assert(subject_digests == artifact_digests, "in-toto subjects must match artifact hashes")
        _assert(statement["predicate"]["record_core"] == sc.record_core(record), "predicate must carry record core")

        return {
            "status": "pass",
            "signed_record": record["record_core_sha256"],
            "ledger_root": sc.read_json(ledger / atlas_log.CHECKPOINT)["root_hash"],
            "in_toto_subjects": len(statement["subject"]),
        }
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def main() -> int:
    print(json.dumps(run(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
