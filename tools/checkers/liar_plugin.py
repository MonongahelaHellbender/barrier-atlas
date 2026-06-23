#!/usr/bin/env python3
"""Adversarial test plugin.

This intentionally ignores its inputs and always claims CERTIFIED at R0. It exists
only to prove the runner refuses tampered artifacts and illegal rung claims even
when an external checker lies.
"""
import argparse
import json
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--envelope", required=True)
    ap.add_argument("--artifacts-dir", required=True)
    ap.parse_args(argv)
    print(json.dumps({
        "verdict": "CERTIFIED",
        "detail": "liar plugin always certifies",
        "rung": "R0",
        "checker": {"name": "barrier-atlas-liar", "version": "0.1"},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
