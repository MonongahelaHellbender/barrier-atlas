#!/usr/bin/env python3
"""Regression guard for the atlas's core safety property: checkers fail CLOSED.

These tests encode the negative cases that shaped the design. The atlas is only
trustworthy if a tampered certificate or a lie about the trusted base can NEVER
produce CERTIFIED. Run: python3 tests/test_one_directional.py
"""
import json
import pathlib
import random
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


def test_encoder_lie_refused():
    """The claim->CNF binding must fail closed if the declared encoder is wrong."""
    env = json.loads((ROOT / "barriers" / "vdw-3-3-r3.barrier.json").read_text())
    env["certificate"]["encoder"]["n"] = 26
    rc, out = _run(env, "encoderlie")
    assert rc == 1 and "encoder mismatch" in out and "CERTIFIED" not in out, out
    print("PASS  wrong encoder spec -> REFUSED (claim/CNF binding fails closed)")


def test_hybrid_encoder_lie_refused():
    """The hybrid R2 entry must refuse if the finite claim/CNF binding is wrong."""
    env = json.loads((ROOT / "barriers" / "hybrid-schur-vdw-3color-le-13-r2.barrier.json").read_text())
    env["certificate"]["encoder"]["n"] = 12
    rc, out = _run(env, "hybridencoderlie")
    assert rc == 1 and "encoder mismatch" in out and "CERTIFIED" not in out, out
    print("PASS  hybrid wrong encoder spec -> REFUSED")


def test_hybrid_rup_certificate_generator():
    """The deterministic hybrid cert generator must reproduce a self-verifying proof."""
    r = subprocess.run(
        [PY, str(ROOT / "tools" / "hybrid_schur_vdw_cert.py"), "--json"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)
    assert data["verified"] is True and data["original_clauses"] == 274 and data["proof_steps"] == 2443, data

    r = subprocess.run(
        [PY, str(ROOT / "tools" / "encoder_check.py"), str(ROOT / "certs" / "hybrid_schur_vdw_3color_13.cert"), "hybrid13"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and "encoder exact-match" in r.stdout, r.stdout + r.stderr
    print("PASS  hybrid RUP cert generator and encoder binding")


def test_rup_python_deterministic_mutation_fuzzer():
    """A small deterministic mutation fuzzer guards the independent RUP checker."""
    sys.path.insert(0, str(ROOT / "tools"))
    import rup_check

    rng = random.Random(20260622)
    certs = ["samples_w33.cert", "samples_r34.cert"]
    cases = 0
    for cert in certs:
        formula, steps = rup_check.parse_cert((ROOT / "certs" / cert).read_text())
        assert rup_check.check_proof(formula, steps)[0] is True
        bad_hint = len(formula) + len(steps) + 1000
        hintful = [i for i, (_clause, hints) in enumerate(steps) if hints]
        for _ in range(25):
            mode = rng.choice(["truncate", "bad_first_hint", "no_empty_clause"])
            mutated = [(list(clause), list(hints)) for clause, hints in steps]
            if mode == "truncate":
                mutated = mutated[:rng.randrange(0, len(mutated))]
            elif mode == "bad_first_hint":
                idx = rng.choice(hintful)
                mutated[idx][1][0] = bad_hint
            else:
                mutated[-1] = ([(bad_hint, False)], list(mutated[-1][1]))
            ok, detail = rup_check.check_proof(formula, mutated)
            assert ok is False, f"{cert} {mode} unexpectedly verified: {detail}"
            cases += 1
    print(f"PASS  deterministic RUP mutation fuzzer refused {cases} mutated proofs")


def test_rup_python_differential_fuzzer():
    """Random small generated certs must agree with lratcheck when available."""
    r = subprocess.run(
        [PY, str(ROOT / "tools" / "rup_differential_fuzzer.py"), "--cases", "32"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    print(r.stdout.strip())


def test_hybrid_schur_vdw_certifies_and_refuses_bad_witness():
    """The new hybrid barrier must certify honestly and reject a bad lower witness."""
    sys.path.insert(0, str(ROOT / "tools"))
    import hybrid_schur_vdw_check

    witness = [0, 1, 0, 2, 1, 2, 2, 0, 2, 0, 1, 1]
    ok, detail, result = hybrid_schur_vdw_check.check_barrier(13, 3, lower_witness=witness)
    assert ok is True, (detail, result)

    env = json.loads((ROOT / "barriers" / "hybrid-schur-vdw-3color-le-13.barrier.json").read_text())
    env["certificate"]["meta"]["lower_bound_witness"] = [0] * 12
    rc, out = _run(env, "hybridbadwitness")
    assert rc == 1 and "REFUSED" in out and "CERTIFIED" not in out, out
    print("PASS  hybrid Schur-vdW certifies and rejects a bad lower witness")


def _chaos_env():
    return json.loads((ROOT / "barriers" / "chaos-01-test-no-separation.barrier.json").read_text())


def test_claim_stress_incomplete_refused():
    """Stage 1: an unanswered stress question must REFUSE (completeness contract)."""
    env = _chaos_env()
    k = next(iter(env["checker"]["stress_answers"]))
    env["checker"]["stress_answers"][k] = ""          # blank one answer
    rc, out = _run(env, "stressincomplete")
    assert rc == 1 and "completeness" in out and "CERTIFIED" not in out, out
    print("PASS  claim-stress incomplete answer -> REFUSED (completeness)")


def test_claim_stress_weak_answer_refused():
    """Stage 2: a vague/dodging answer with no concrete evidence must REFUSE."""
    env = _chaos_env()
    k = next(iter(env["checker"]["stress_answers"]))
    env["checker"]["stress_answers"][k] = "Yes, this has been carefully checked and is fine."
    rc, out = _run(env, "stressweak")
    assert rc == 1 and "adequacy" in out and "CERTIFIED" not in out, out
    print("PASS  claim-stress dodging answer -> REFUSED (adequacy)")


def test_claim_stress_named_signoff_certifies():
    """Stage 3: a NAMED human sign-off flips the satisfied contract to CERTIFIED."""
    env = _chaos_env()
    env["checker"]["human_review"] = {"kind": "human", "by": "Test Reviewer",
                                      "date": "2026-06-22", "verdict": "adequate"}
    rc, out = _run(env, "stresssignoff")
    assert rc == 0 and "CERTIFIED" in out and "human sign-off by Test Reviewer" in out, out
    print("PASS  claim-stress named human sign-off -> CERTIFIED")


def test_claim_stress_llm_review_does_not_certify():
    """An llm sign-off SCREENS but never CERTIFIES -- automation is not a correctness
    gate (the calibration measured llm false-accepts). Only a named human certifies."""
    env = _chaos_env()
    env["checker"]["human_review"] = {"kind": "llm", "by": "some-model",
                                      "date": "2026-06-22", "verdict": "adequate"}
    rc, out = _run(env, "stressllm")
    assert "CERTIFIED" not in out and "DEFERRED" in out and "NOT a correctness gate" in out, out
    print("PASS  claim-stress llm sign-off -> DEFERRED (screened, never a correctness gate)")


def test_empirical_r4_through_composition():
    """A CERTIFIED claim-stress R4 is a first-class min-trust input; the formal R2
    co-part cannot launder the composite above R4."""
    env = json.loads((ROOT / "barriers" / "empirical-and-combinatorial-bundle.barrier.json").read_text())
    rc, out = _run(env, "empcompose")
    if "UNVERIFIABLE-HERE" in out:                       # lratcheck sub absent on a bare runner
        print("SKIP  R4-through-composition (toolchain absent here)")
        return
    assert rc == 0 and "CERTIFIED" in out and "min-trust R4" in out, out
    env["rung"]["level"] = "R2"                           # the LIE: claim formal-strength over an R4 part
    rc2, out2 = _run(env, "empcomposeR2")
    assert rc2 == 1 and "REFUSED" in out2 and "CERTIFIED" not in out2, out2
    print("PASS  R4 flows through composition; declaring it R2 -> REFUSED")


def test_multi_region_min_trust():
    """A multi-region barrier earns the weakest region's rung; a strong region
    cannot launder the claim up."""
    vdw = json.loads((ROOT / "barriers" / "vdw-3-3.barrier.json").read_text())
    ram = json.loads((ROOT / "barriers" / "ramsey-3-4.barrier.json").read_text())
    env = {
        "id": "_mr_test", "schema_version": "0.1",
        "claim": {"statement": "two R2 regions of one claim", "kind": "impossibility",
                  "negation_of": "a counterexample in either region"},
        "domain": "test/multi-region", "rung": {"level": "R2", "name": "multi-region",
                                                "trusted_base": ["min-trust across regions"]},
        "certificate": {"kind": "multi-region"},
        "checker": {"kind": "multi-region", "regions": [
            {"region": "A", "rung": "R2", "checker": vdw["checker"], "certificate": vdw["certificate"]},
            {"region": "B", "rung": "R2", "checker": ram["checker"], "certificate": ram["certificate"]},
        ]},
        "status": "live", "provenance": {"source_package": "test"},
        "one_directional": "test fixture",
    }
    rc, out = _run(env, "multiregion")
    if "UNVERIFIABLE-HERE" in out:                       # lratcheck regions need the toolchain
        print("SKIP  multi-region (toolchain absent here)")
        return
    assert rc == 0 and "CERTIFIED" in out and "min-trust R2" in out, out
    env["rung"]["level"] = "R0"                           # the LIE: claim kernel-strength over R2 regions
    rc2, out2 = _run(env, "multiregionR0")
    assert rc2 == 1 and "REFUSED" in out2 and "declared R0 != min-trust R2" in out2, out2
    print("PASS  multi-region min-trust R2; declaring R0 -> REFUSED")


def test_review_calibration_reports_false_accept():
    """The calibration artifact must surface the false-accept risk it documents:
    on the adversarial seed the llm reviewer is fooled, so it is not gate-safe."""
    sys.path.insert(0, str(ROOT / "tools"))
    import review_calibration as rc
    s = rc.score(rc.load(ROOT / "data" / "review_calibration_seed.jsonl"))
    assert s["false_accept"] >= 1 and s["llm_safe_as_gate"] is False, s
    print(f"PASS  review calibration surfaces false-accept={s['false_accept']} "
          f"(rate {s['false_accept_rate']}) -> llm not gate-safe")


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
    test_encoder_lie_refused()
    test_hybrid_encoder_lie_refused()
    test_hybrid_rup_certificate_generator()
    test_rup_python_deterministic_mutation_fuzzer()
    test_rup_python_differential_fuzzer()
    test_hybrid_schur_vdw_certifies_and_refuses_bad_witness()
    test_claim_stress_incomplete_refused()
    test_claim_stress_weak_answer_refused()
    test_claim_stress_named_signoff_certifies()
    test_claim_stress_llm_review_does_not_certify()
    test_empirical_r4_through_composition()
    test_multi_region_min_trust()
    test_review_calibration_reports_false_accept()
    test_honest_run_certifies()
    print("\nAll one-directional safety tests passed.")
