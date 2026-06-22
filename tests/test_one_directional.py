#!/usr/bin/env python3
"""Regression guard for the atlas's core safety property: checkers fail CLOSED.

These tests encode the negative cases that shaped the design. The atlas is only
trustworthy if a tampered certificate or a lie about the trusted base can NEVER
produce CERTIFIED. Run: python3 tests/test_one_directional.py
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
CHECK = str(ROOT / "tools" / "barrier_check.py")


def _run(envelope: dict, name: str):
    p = ROOT / "barriers" / f"_test_{name}.barrier.json"
    p.write_text(json.dumps(envelope))
    try:
        r = subprocess.run([PY, CHECK, str(p)], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr
    finally:
        p.unlink(missing_ok=True)


def test_tampered_cert_refused():
    """Mangling cert bytes must REFUSE (sha256 binding), never falsely certify."""
    bad = ROOT / "certs" / "_test_bad.cert"
    shutil.copy(ROOT / "certs" / "samples_w33.cert", bad)
    bad.write_text(re.sub(r"^\d+", "999999", bad.read_text(), count=1))
    env = json.loads((ROOT / "barriers" / "vdw-3-3.barrier.json").read_text())
    env["checker"]["cert"] = "certs/_test_bad.cert"
    env["certificate"]["path"] = "certs/_test_bad.cert"
    try:
        rc, out = _run(env, "tamper")
    finally:
        bad.unlink(missing_ok=True)
    # sha256 binding is environment-independent: this MUST refuse, toolchain or not.
    assert rc == 1 and "REFUSED" in out and "CERTIFIED" not in out, out
    print("PASS  tampered cert -> REFUSED (fails closed, no toolchain needed)")


def test_axiom_lie_refused():
    """Understating the trusted base (a silent rung-slide) must REFUSE."""
    env = json.loads((ROOT / "barriers" / "nn-robust-2relu.barrier.json").read_text())
    env["checker"]["expected_axioms"] = ["propext", "Quot.sound"]  # omit Classical.choice
    rc, out = _run(env, "axiomlie")
    if "UNVERIFIABLE-HERE" in out:  # no Lean toolchain on this runner -> honest skip
        print("SKIP  axiom understatement (Lean toolchain absent here)")
        return
    assert rc == 1 and "REFUSED" in out and "CERTIFIED" not in out, out
    print("PASS  axiom understatement -> REFUSED (catches rung-slide)")


def test_rung_laundering_refused():
    """A composite cannot be declared STRONGER than its weakest part."""
    env = json.loads((ROOT / "barriers" / "combinatorics-two-bounds.barrier.json").read_text())
    env["rung"]["level"] = "R0"  # the LIE: claim kernel-only over two R2 parts
    rc, out = _run(env, "launder")
    if "UNVERIFIABLE-HERE" in out:  # sub-barriers need the Lean toolchain
        print("SKIP  rung-laundering (toolchain absent here)")
        return
    assert rc == 1 and "REFUSED" in out and "CERTIFIED" not in out, out
    print("PASS  rung laundering (R0 over R2 parts) -> REFUSED")


def test_rup_python_refuses_broken_proof():
    """The independent R3 checker must fail closed on a broken certificate."""
    sys.path.insert(0, str(ROOT / "tools"))
    import rup_check
    f, steps = rup_check.parse_cert((ROOT / "certs" / "samples_w33.cert").read_text())
    assert rup_check.check_proof(f, steps)[0] is True            # honest -> True
    assert rup_check.check_proof(f, steps[:-1])[0] is False      # drop final -> no []
    broken = list(steps); cl, h = broken[-1]; broken[-1] = (cl, h[:-1])
    assert rup_check.check_proof(f, broken)[0] is False          # bad hints -> refuse
    print("PASS  independent RUP checker refuses broken/truncated proofs")


def test_honest_run_certifies():
    """The real, unmodified entries must still certify (no false negatives)."""
    r = subprocess.run([PY, CHECK], capture_output=True, text=True)
    assert r.returncode == 0 and "0 refused" in r.stdout, r.stdout + r.stderr
    print("PASS  honest atlas -> 0 refused")


if __name__ == "__main__":
    test_tampered_cert_refused()
    test_axiom_lie_refused()
    test_rung_laundering_refused()
    test_rup_python_refuses_broken_proof()
    test_honest_run_certifies()
    print("\nAll one-directional safety tests passed.")
