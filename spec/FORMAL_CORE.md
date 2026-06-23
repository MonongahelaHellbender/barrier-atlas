# Formal Core Boundary

Phase F adds a small Lean model of the Barrier Atlas verdict decision core. The
purpose is narrow: prove that the modeled decision gate cannot return
`CERTIFIED` without the positive evidence signal required by its checker,
composition, or quorum path.

## Proved

`LeanVerificationJourney.RunnerFailClosed` defines a finite `Facts` structure and
a verdict function over those facts. Lean proves:

- `RunnerFailClosed.runner_no_fail_open`: if `checker_positive = false`, the
  decision core cannot return `CERTIFIED`;
- `RunnerFailClosed.only_positive_certifies`: a `CERTIFIED` decision entails the
  modeled positive conjunction;
- per-gate lemmas for artifact binding, external-plugin manifest/timeout/sandbox
  gates, rung ceilings, composition min-trust, and quorum threshold/independence.

The atlas dogfoods this proof through
`barriers/runner-fail-closed-core.barrier.json`, using the existing
`lean-axioms` checker. The declared axiom base is exactly `propext`.

## Bridged By Test

`lean-verification-journey/RunnerDecisionTable.lean` exports
`spec/decision_table.json`, a complete table over:

- 7 decision paths: atomic, external, composed, multi-region, quorum, manual, and
  unknown;
- 16 finite Boolean facts;
- 458752 total rows.

`tests/test_decision_table.py` regenerates that table from Lean when the sibling
Lean repo and `lake` are present, checks that the committed table still matches
the fresh export, checks that `tools/decide.py` agrees with the Lean-exported
table row-for-row, then drives representative conformance fixtures through the
real runner and compares their final verdicts to the corresponding table rows.
Set `BARRIER_ATLAS_REQUIRE_LEAN_EXPORT=1` to make the Lean export mandatory in
review environments.

This is a tested bridge from model to implementation, not a proof of the Python
runner implementation.

## Still Trusted

Phase F does not prove:

- Ed25519 signatures, Merkle logging, key custody, or in-toto mapping;
- plugin honesty beyond manifest identity and rung ceilings;
- that distinct checker hashes are semantically independent;
- that human empirical review is correct;
- the fact-extraction layer that maps concrete runner state into the finite
  `Facts` booleans.

The honest trust boundary is: **proved decision core + tested bridge + trusted
fact extraction**.
