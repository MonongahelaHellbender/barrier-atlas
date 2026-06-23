#!/usr/bin/env python3
"""Shared helpers for signed Barrier Atlas verdict records.

The runner remains stdlib-only. This module is used by post-run attestation tools
and depends on `cryptography` for Ed25519 signatures.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

import spec_runner

ALG = "ed25519"
SIGNATURE_VERSION = "0.1"

OK = "OK"
RECORD_CORE_MISMATCH = "RECORD_CORE_MISMATCH"
SIGNATURE_INVALID = "SIGNATURE_INVALID"


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def record_core(record: dict) -> dict:
    return spec_runner._record_core(record)


def record_core_bytes(record: dict) -> bytes:
    return canonical_json_bytes(record_core(record))


def record_core_sha256(record: dict) -> str:
    return sha256_bytes(record_core_bytes(record))


def _raw_public_key(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def key_id(public_key: Ed25519PublicKey) -> str:
    return f"ed25519:{sha256_bytes(_raw_public_key(public_key))}"


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("private key must be Ed25519")
    return key


def load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("public key must be Ed25519")
    return key


def write_keypair(private_path: Path, public_path: Path) -> str:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return key_id(public_key)


def assert_record_core_matches(record: dict) -> str:
    computed = record_core_sha256(record)
    declared = str(record.get("record_core_sha256", ""))
    if declared != computed:
        raise ValueError(f"{RECORD_CORE_MISMATCH}: declared {declared}, computed {computed}")
    return computed


def sign_record(record: dict, private_key: Ed25519PrivateKey, signed_at: str | None = None) -> dict:
    digest = assert_record_core_matches(record)
    sig = private_key.sign(record_core_bytes(record))
    return {
        "signature_version": SIGNATURE_VERSION,
        "alg": ALG,
        "record_core_sha256": digest,
        "sig": base64.b64encode(sig).decode("ascii"),
        "key_id": key_id(private_key.public_key()),
        "signed_at": signed_at or now_utc(),
    }


def verify_record_signature(record: dict, signature: dict, public_key: Ed25519PublicKey) -> tuple[bool, str, str]:
    try:
        digest = assert_record_core_matches(record)
    except ValueError as e:
        return False, RECORD_CORE_MISMATCH, str(e)
    if signature.get("alg") != ALG:
        return False, SIGNATURE_INVALID, "signature alg is not ed25519"
    if signature.get("record_core_sha256") != digest:
        return False, RECORD_CORE_MISMATCH, "signature digest does not match recomputed record core"
    if signature.get("key_id") != key_id(public_key):
        return False, SIGNATURE_INVALID, "signature key_id does not match public key"
    try:
        sig = base64.b64decode(str(signature.get("sig", "")), validate=True)
        public_key.verify(sig, record_core_bytes(record))
    except (InvalidSignature, ValueError):
        return False, SIGNATURE_INVALID, "ed25519 signature verification failed"
    return True, OK, "signature verified"


def checkpoint_payload(tree_size: int, root_hash: str) -> dict:
    return {
        "checkpoint_version": SIGNATURE_VERSION,
        "tree_size": int(tree_size),
        "root_hash": root_hash,
    }


def sign_checkpoint(tree_size: int, root_hash: str, private_key: Ed25519PrivateKey,
                    signed_at: str | None = None) -> dict:
    payload = checkpoint_payload(tree_size, root_hash)
    sig = private_key.sign(canonical_json_bytes(payload))
    return {
        **payload,
        "alg": ALG,
        "key_id": key_id(private_key.public_key()),
        "sig": base64.b64encode(sig).decode("ascii"),
        "signed_at": signed_at or now_utc(),
    }


def verify_checkpoint(checkpoint: dict, public_key: Ed25519PublicKey) -> tuple[bool, str]:
    try:
        tree_size = int(checkpoint.get("tree_size", -1))
    except (TypeError, ValueError):
        return False, "checkpoint tree_size is invalid"
    payload = checkpoint_payload(tree_size, str(checkpoint.get("root_hash", "")))
    if checkpoint.get("alg") != ALG or checkpoint.get("key_id") != key_id(public_key):
        return False, "checkpoint signature metadata is invalid"
    try:
        sig = base64.b64decode(str(checkpoint.get("sig", "")), validate=True)
        public_key.verify(sig, canonical_json_bytes(payload))
    except (InvalidSignature, ValueError):
        return False, "checkpoint signature verification failed"
    return True, "checkpoint verified"
