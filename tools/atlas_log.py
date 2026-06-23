#!/usr/bin/env python3
"""Append and verify signed Barrier Atlas verdict records in a Merkle ledger."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing_common as sc  # noqa: E402

ENTRIES = "entries.jsonl"
CHECKPOINT = "checkpoint.json"
PROOFS = "proofs"

LOG_OK = "OK"
LOG_INCLUSION_MISSING = "LOG_INCLUSION_MISSING"
LOG_ROOT_MISMATCH = "LOG_ROOT_MISMATCH"
CHECKPOINT_SIGNATURE_INVALID = "CHECKPOINT_SIGNATURE_INVALID"


def _entry_for(record: dict, signature: dict) -> dict:
    return {
        "record_core_sha256": signature["record_core_sha256"],
        "record": record,
        "signature": signature,
    }


def _leaf_hash(entry: dict) -> str:
    return sc.sha256_bytes(b"\x00" + sc.canonical_json_bytes(entry))


def _node_hash(left: str, right: str) -> str:
    return sc.sha256_bytes(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right))


def _levels(leaf_hashes: list[str]) -> list[list[str]]:
    if not leaf_hashes:
        return [[""]]
    levels = [leaf_hashes]
    current = leaf_hashes
    while len(current) > 1:
        nxt = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                nxt.append(_node_hash(current[i], current[i + 1]))
            else:
                nxt.append(current[i])
        levels.append(nxt)
        current = nxt
    return levels


def merkle_root(leaf_hashes: list[str]) -> str:
    if not leaf_hashes:
        return sc.sha256_bytes(b"")
    return _levels(leaf_hashes)[-1][0]


def inclusion_proof(leaf_hashes: list[str], leaf_index: int) -> list[dict]:
    proof = []
    idx = leaf_index
    for level in _levels(leaf_hashes)[:-1]:
        if idx % 2 == 0:
            sibling = idx + 1
            side = "right"
        else:
            sibling = idx - 1
            side = "left"
        if sibling < len(level):
            proof.append({"side": side, "hash": level[sibling]})
        idx //= 2
    return proof


def verify_proof(leaf_hash: str, leaf_index: int, tree_size: int, proof: list[dict], root_hash: str) -> bool:
    if leaf_index < 0 or leaf_index >= tree_size:
        return False
    current = leaf_hash
    idx = leaf_index
    for item in proof:
        h = item.get("hash", "")
        if item.get("side") == "left":
            current = _node_hash(h, current)
        elif item.get("side") == "right":
            current = _node_hash(current, h)
        else:
            return False
        idx //= 2
    return current == root_hash


def _entries_path(ledger: Path) -> Path:
    return ledger / ENTRIES


def _checkpoint_path(ledger: Path) -> Path:
    return ledger / CHECKPOINT


def _proof_path(ledger: Path, digest: str) -> Path:
    return ledger / PROOFS / f"{digest}.proof.json"


def load_entries(ledger: Path) -> list[dict]:
    path = _entries_path(ledger)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_entries(ledger: Path, entries: list[dict]) -> None:
    ledger.mkdir(parents=True, exist_ok=True)
    _entries_path(ledger).write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in entries),
        encoding="utf-8",
    )


def _leaf_hashes(entries: list[dict]) -> list[str]:
    return [_leaf_hash(row["entry"]) for row in entries]


def append_record(record: dict, signature: dict, ledger: Path, public_key, checkpoint_key,
                  signed_at: str | None = None) -> dict:
    ok, reason, detail = sc.verify_record_signature(record, signature, public_key)
    if not ok:
        raise ValueError(f"{reason}: {detail}")
    entries = load_entries(ledger)
    entry = _entry_for(record, signature)
    entries.append({"leaf_index": len(entries), "entry": entry})
    leaves = _leaf_hashes(entries)
    root = merkle_root(leaves)
    checkpoint = sc.sign_checkpoint(len(entries), root, checkpoint_key, signed_at)
    proof = {
        "proof_version": sc.SIGNATURE_VERSION,
        "record_core_sha256": signature["record_core_sha256"],
        "leaf_index": len(entries) - 1,
        "leaf_hash": leaves[-1],
        "tree_size": len(entries),
        "root_hash": root,
        "proof": inclusion_proof(leaves, len(entries) - 1),
    }
    _write_entries(ledger, entries)
    sc.write_json(_checkpoint_path(ledger), checkpoint)
    sc.write_json(_proof_path(ledger, signature["record_core_sha256"]), proof)
    return {"checkpoint": checkpoint, "proof": proof}


def verify_ledger(ledger: Path, public_key) -> tuple[bool, str, str]:
    checkpoint_path = _checkpoint_path(ledger)
    if not checkpoint_path.exists():
        return False, LOG_INCLUSION_MISSING, "checkpoint missing"
    checkpoint = sc.read_json(checkpoint_path)
    ok, detail = sc.verify_checkpoint(checkpoint, public_key)
    if not ok:
        return False, CHECKPOINT_SIGNATURE_INVALID, detail
    entries = load_entries(ledger)
    root = merkle_root(_leaf_hashes(entries))
    try:
        tree_size = int(checkpoint.get("tree_size", -1))
    except (TypeError, ValueError):
        return False, LOG_ROOT_MISMATCH, "checkpoint tree_size is invalid"
    if tree_size != len(entries) or checkpoint.get("root_hash") != root:
        return False, LOG_ROOT_MISMATCH, "entries do not match signed checkpoint"
    return True, LOG_OK, "ledger root matches checkpoint"


def verify_record_inclusion(record: dict, signature: dict, ledger: Path, public_key) -> tuple[bool, str, str]:
    ok, reason, detail = sc.verify_record_signature(record, signature, public_key)
    if not ok:
        return ok, reason, detail
    ok, reason, detail = verify_ledger(ledger, public_key)
    if not ok:
        return ok, reason, detail
    digest = signature.get("record_core_sha256", "")
    proof_path = _proof_path(ledger, digest)
    if not proof_path.exists():
        return False, LOG_INCLUSION_MISSING, "record proof missing"
    proof = sc.read_json(proof_path)
    checkpoint = sc.read_json(_checkpoint_path(ledger))
    entry = _entry_for(record, signature)
    leaf_hash = _leaf_hash(entry)
    if proof.get("leaf_hash") != leaf_hash:
        return False, LOG_INCLUSION_MISSING, "proof leaf does not match record and signature"
    if proof.get("tree_size") != checkpoint.get("tree_size") or proof.get("root_hash") != checkpoint.get("root_hash"):
        return False, LOG_ROOT_MISMATCH, "proof checkpoint fields are stale"
    try:
        leaf_index = int(proof.get("leaf_index", -1))
        tree_size = int(proof.get("tree_size", -1))
    except (TypeError, ValueError):
        return False, LOG_ROOT_MISMATCH, "proof index fields are invalid"
    if not verify_proof(leaf_hash, leaf_index, tree_size, list(proof.get("proof", [])), str(proof.get("root_hash", ""))):
        return False, LOG_ROOT_MISMATCH, "inclusion proof does not reach checkpoint root"
    return True, LOG_OK, "record included in signed ledger checkpoint"


def _emit(ok: bool, reason_code: str, detail: str, extra: dict | None = None) -> int:
    payload = {
        "status": "pass" if ok else "fail",
        "reason_code": reason_code,
        "detail": detail,
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    append = sub.add_parser("append", help="append a signed record and refresh checkpoint")
    append.add_argument("--record", required=True)
    append.add_argument("--signature", required=True)
    append.add_argument("--public-key", required=True)
    append.add_argument("--checkpoint-key", required=True)
    append.add_argument("--ledger", default="LEDGER")
    append.add_argument("--signed-at")

    verify = sub.add_parser("verify-ledger", help="verify entries against signed checkpoint")
    verify.add_argument("--ledger", default="LEDGER")
    verify.add_argument("--public-key", required=True)

    incl = sub.add_parser("verify-inclusion", help="verify a signed record is included")
    incl.add_argument("--record", required=True)
    incl.add_argument("--signature", required=True)
    incl.add_argument("--ledger", default="LEDGER")
    incl.add_argument("--public-key", required=True)

    args = parser.parse_args(argv)
    public_key = sc.load_public_key(Path(args.public_key))

    if args.cmd == "append":
        checkpoint_key = sc.load_private_key(Path(args.checkpoint_key))
        record = sc.read_json(Path(args.record))
        signature = sc.read_json(Path(args.signature))
        result = append_record(record, signature, Path(args.ledger), public_key, checkpoint_key, args.signed_at)
        return _emit(True, LOG_OK, "record appended", {
            "tree_size": result["checkpoint"]["tree_size"],
            "root_hash": result["checkpoint"]["root_hash"],
        })
    if args.cmd == "verify-ledger":
        ok, reason, detail = verify_ledger(Path(args.ledger), public_key)
        return _emit(ok, reason, detail)
    if args.cmd == "verify-inclusion":
        record = sc.read_json(Path(args.record))
        signature = sc.read_json(Path(args.signature))
        ok, reason, detail = verify_record_inclusion(record, signature, Path(args.ledger), public_key)
        return _emit(ok, reason, detail)
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
