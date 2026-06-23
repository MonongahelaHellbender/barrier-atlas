# Barrier Atlas Reviewer Brief

Barrier Atlas is a refusal-first verification artifact for bounded scientific and
AI-assurance claims. It is built around one question:

> What can this claim certify, what must it refuse, and what remains outside the
> trusted base?

The project has two layers.

1. The atlas itself: 13 barrier envelopes over formal, computational, empirical,
   composed, and deferred evidence.
2. The v0.1 spec seed: a runner/envelope/conformance contract that makes refusal,
   artifact binding, trust rungs, and checker identity inspectable.

## Current State

```bash
python3 tools/barrier_check.py
# summary: 10 certified, 0 refused, 0 unverifiable-here, 3 deferred

python3 tests/test_one_directional.py
# 18 safety tests

python3 tests/test_invariant_fuzz.py
# 2000 deterministic runner-invariant fuzz cases on push/PR; 50000 on schedule

python3 tests/test_decision_table.py
# 458752 Lean-exported decision rows + representative runner branch checks

python3 spec/validate.py
# validates atlas envelopes, conformance fixtures, and checker manifests

python3 spec/conformance/run_conformance.py --runner "python3 tools/plugin_runner.py"
# 19 conformance fixtures
```

CI runs those load-bearing checks on every push.

## What Is New Here

The main contribution is not any single finite combinatorics result. The point is
the claim discipline:

- every claim names its trust rung;
- certificates and artifacts are hash-bound;
- encoder/spec bindings are checked for the certificate-backed combinatorics claims;
- composed claims inherit their weakest rung;
- non-human empirical review can screen but cannot certify;
- external checker plugins are hash-pinned and can only propose verdicts;
- plugins run with an explicitly recorded sandbox profile (`env-restricted` by
  default; required real sandbox profiles fail closed when unavailable);
- quorum claims require enough independent certifying checker hashes;
- verdict records can be signed after the run, transparency-logged in a Merkle
  ledger, and mapped into an in-toto Statement shape;
- the finite verdict decision core has a Lean theorem and a committed exhaustive
  decision table bridged back to the Python runner;
- conformance fixtures include adversarial cases such as tampered artifacts,
  rung laundering, weak empirical answers, unknown checkers, and a deliberately
  lying plugin.
- a deterministic invariant fuzzer continuously mutates runner inputs and asserts
  that generated structural violations cannot produce `CERTIFIED`.

The runner, not the checker, owns the final verdict vocabulary and structural gates.

## Strongest Honest Claim

Barrier Atlas is a working prototype for checkable, bounded, refusal-first claim
certification. It demonstrates how to separate proof, independent recomputation,
empirical review, composition, deferral, and refusal without silently promoting a
claim above its earned trust base.

## What It Does Not Claim

Barrier Atlas is not a broad standard, not a production certification system, and
not a guarantee about real-world AI-system behavior. Phase F proves a finite
decision-core model and tests the bridge to representative runner branches; it
does not prove the full Python runner implementation or fact extraction. External
plugins run under a recorded `env-restricted` profile, not a real OS sandbox.
Phase E signatures prove key possession over a verdict core, not institutional
trust in the key. Empirical R4 entries remain empirical: they can be made
attributable and stress-tested, but not theorem-like.

## Best 10-Minute Review Path

1. Read [`spec/DESIGN_CLAIMS_AND_LIMITS.md`](spec/DESIGN_CLAIMS_AND_LIMITS.md).
2. Run `python3 spec/conformance/run_conformance.py --runner "python3 tools/plugin_runner.py"`.
3. Inspect fixtures 10-19 in [`spec/conformance/fixtures`](spec/conformance/fixtures):
   external RUP plugin, checker hash mismatch, liar over tampered artifact, and liar
   illegal rung, malformed plugin timeout, quorum met/not-met/not-independent,
   unavailable required sandbox, and duplicate-plus-distinct quorum.
4. Run `python3 tests/test_phase_e_attestation.py` to check signed-record,
   ledger-inclusion, ledger-tamper, and in-toto mapping probes.
5. Run `BARRIER_ATLAS_REQUIRE_LEAN_EXPORT=1 python3 tests/test_decision_table.py`
   when the sibling Lean repo is available, then read
   [`spec/FORMAL_CORE.md`](spec/FORMAL_CORE.md).
6. Read [`tools/plugin_runner.py`](tools/plugin_runner.py), especially the manifest
   hash check, artifact staging, and returned-rung validation.

## Best 30-Minute Review Path

Run the full checks:

```bash
python3 -m py_compile tools/plugin_runner.py tools/spec_runner.py spec/validate.py spec/conformance/run_conformance.py
python3 spec/validate.py
python3 spec/conformance/run_conformance.py --runner "python3 tools/plugin_runner.py"
python3 tests/test_phase_e_attestation.py
BARRIER_ATLAS_REQUIRE_LEAN_EXPORT=1 python3 tests/test_decision_table.py
python3 tests/test_invariant_fuzz.py
python3 tests/test_one_directional.py
python3 tools/barrier_check.py
```

Then try to break the invariant: no tampered artifact, weak sub-barrier, non-human
empirical sign-off, over-strong rung, unknown checker, bad manifest hash, lying
plugin, non-independent quorum, or unavailable required sandbox should produce
`CERTIFIED`.
