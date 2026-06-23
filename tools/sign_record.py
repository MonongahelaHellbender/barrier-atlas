#!/usr/bin/env python3
"""Sign a Barrier Atlas verdict record's canonical core with Ed25519."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing_common as sc  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate-keypair", action="store_true", help="create an Ed25519 keypair and exit")
    parser.add_argument("--private-key", required=True, help="private key path for signing or generation")
    parser.add_argument("--public-key", help="public key path for --generate-keypair")
    parser.add_argument("--record", help="verdict record JSON to sign")
    parser.add_argument("--out", help="write detached signature JSON here; stdout if omitted")
    parser.add_argument("--signed-at", help="override signature timestamp, for reproducible tests")
    args = parser.parse_args(argv)

    private_path = Path(args.private_key)
    if args.generate_keypair:
        if not args.public_key:
            parser.error("--generate-keypair requires --public-key")
        key_id = sc.write_keypair(private_path, Path(args.public_key))
        print(json.dumps({"status": "pass", "key_id": key_id}, sort_keys=True))
        return 0

    if not args.record:
        parser.error("signing requires --record")
    record = sc.read_json(Path(args.record))
    private_key = sc.load_private_key(private_path)
    signature = sc.sign_record(record, private_key, args.signed_at)
    if args.out:
        sc.write_json(Path(args.out), signature)
    else:
        print(json.dumps(signature, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
