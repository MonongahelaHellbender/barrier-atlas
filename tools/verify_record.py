#!/usr/bin/env python3
"""Verify a signed Barrier Atlas verdict record and optional ledger inclusion."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_log  # noqa: E402
import signing_common as sc  # noqa: E402


def _emit(ok: bool, reason_code: str, detail: str) -> int:
    print(json.dumps({
        "status": "pass" if ok else "fail",
        "reason_code": reason_code,
        "detail": detail,
    }, sort_keys=True))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, help="verdict record JSON")
    parser.add_argument("--signature", required=True, help="detached signature JSON")
    parser.add_argument("--public-key", required=True, help="Ed25519 public key PEM")
    parser.add_argument("--in-log", action="store_true", help="also verify inclusion in --ledger")
    parser.add_argument("--ledger", default="LEDGER", help="ledger directory for --in-log")
    args = parser.parse_args(argv)

    record = sc.read_json(Path(args.record))
    signature = sc.read_json(Path(args.signature))
    public_key = sc.load_public_key(Path(args.public_key))
    ok, reason, detail = sc.verify_record_signature(record, signature, public_key)
    if not ok:
        return _emit(False, reason, detail)
    if args.in_log:
        ok, reason, detail = atlas_log.verify_record_inclusion(record, signature, Path(args.ledger), public_key)
        if not ok:
            return _emit(False, reason, detail)
    return _emit(True, sc.OK, "signature verified" + (" and included in ledger" if args.in_log else ""))


if __name__ == "__main__":
    raise SystemExit(main())
