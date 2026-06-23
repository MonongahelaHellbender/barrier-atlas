#!/usr/bin/env python3
"""External RUP checker plugin for the Barrier Atlas v0.1 contract."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import rup_check  # noqa: E402


def emit(verdict: str, detail: str, rung: str = "R3") -> int:
    print(json.dumps({
        "verdict": verdict,
        "detail": detail,
        "rung": rung,
        "checker": {"name": "barrier-atlas-rup", "version": "0.1"},
    }, sort_keys=True))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--envelope", required=True)
    ap.add_argument("--artifacts-dir", required=True)
    args = ap.parse_args(argv)

    env = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
    artifact_id = env.get("checker", {}).get("cert_artifact", "certificate")
    cert = Path(args.artifacts_dir) / artifact_id
    if not cert.exists():
        return emit("REFUSED", f"staged artifact {artifact_id!r} missing")
    try:
        formula, steps = rup_check.parse_cert(cert.read_text(encoding="utf-8"))
        ok, detail = rup_check.check_proof(formula, steps)
    except Exception as e:  # noqa: BLE001
        return emit("REFUSED", f"RUP check crashed: {e}")
    return emit("CERTIFIED" if ok else "REFUSED", detail)


if __name__ == "__main__":
    sys.exit(main())
