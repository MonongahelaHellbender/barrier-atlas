#!/usr/bin/env python3
"""Convert a Barrier Atlas verdict record into an in-toto Statement shape."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing_common as sc  # noqa: E402

STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://github.com/MonongahelaHellbender/barrier-atlas/spec/predicate/verdict/v0.1"


def statement_for_record(record: dict) -> dict:
    sc.assert_record_core_matches(record)
    subject = [
        {
            "name": artifact["id"],
            "digest": {"sha256": artifact["sha256"]},
        }
        for artifact in record.get("artifacts", [])
    ]
    return {
        "_type": STATEMENT_TYPE,
        "subject": subject,
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "record_core_sha256": record["record_core_sha256"],
            "record_core": sc.record_core(record),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    statement = statement_for_record(sc.read_json(Path(args.record)))
    if args.out:
        sc.write_json(Path(args.out), statement)
    else:
        print(json.dumps(statement, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
