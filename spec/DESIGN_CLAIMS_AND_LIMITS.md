# Design Claims And Limits

This document states what Barrier Atlas Spec v0.1 earns, what it trusts, and what
it does not claim.

## Purpose

Barrier Atlas v0.1 is a small runner/envelope/conformance seed for bounded claims.
It is designed to make claim boundaries inspectable:

- what artifact is being checked;
- which checker or plugin is allowed to interpret it;
- which trust rung the result can earn;
- which failures must refuse or defer;
- what remains inside the trusted base.

## Claims The Spec Earns

### 1. Artifact binding is runner-owned

The runner verifies `artifacts[].path` containment and SHA-256 before dispatch.
Missing artifacts, path escapes, and hash mismatches produce runner-owned refusal
reason codes.

Evidence:

- `02-tampered-artifact.barrier.json`
- `03-missing-artifact.barrier.json`
- `12-liar-tampered-artifact.barrier.json`

### 2. Rung discipline is runner-owned

Atomic checker kinds have maximum rungs. `rup-python` and `external-rup` cannot
certify above R3. Composed and multi-region claims compute their final rung from
their weakest part.

Evidence:

- `06-rung-laundering.barrier.json`
- `09-atomic-rung-over-ceiling.barrier.json`
- `13-liar-illegal-rung.barrier.json`

### 3. Conformance checks reason, not only verdict

Each conformance fixture may assert both `expected_verdict` and
`expected_reason_code`. This prevents an implementation from passing by failing
for the wrong reason.

Example: a tampered artifact must be `ARTIFACT_HASH_MISMATCH`, not merely a generic
`REFUSED`.

### 4. Verdict records are stable at the structured core

The runner emits a verdict record with `record_core_sha256`. The core hash binds
structured fields: envelope id/hash, artifact ids/hashes, checker identity, raw and
final verdicts, final rung, and reason code.

It intentionally excludes free-text `detail` and timestamps, so explanatory prose
can vary without changing the audit core.

### 5. External plugins can be hash-pinned without becoming final authority

External checker plugins run as separate executables. The runner verifies the
manifest, computes the entrypoint hash itself, stages only verified artifacts, runs
the plugin, validates the plugin output, and then emits the final verdict.

Evidence:

- `10-external-rup.barrier.json`
- `11-checker-hash-mismatch.barrier.json`
- `12-liar-tampered-artifact.barrier.json`
- `13-liar-illegal-rung.barrier.json`

## Trusted Base

The trusted base is explicit, not hidden.

| component | role | trust status |
|---|---|---|
| `tools/spec_runner.py` | Phase A runner: artifacts, rung ceilings, composition, verdict records | trusted v0.1 runner code |
| `tools/plugin_runner.py` | Phase B external plugin dispatch and identity checks | trusted v0.1 runner code |
| in-process checkers | interpret specific evidence kinds | trusted according to declared rung |
| external plugins | propose evidence verdicts | trusted only by manifest identity and rung |
| `tools/barrier_check.py` | atlas dispatcher for live barriers | trusted by checker kind and tests |
| named human review | empirical correctness anchor for R4 | attributable, not mechanically verified |

The runner is not yet formally verified. Its credibility comes from small scope,
readability, explicit conformance fixtures, and adversarial negative tests.

## Important Non-Claims

Barrier Atlas v0.1 does not claim:

- production certification readiness;
- broad standards authority;
- real-world model-behavior guarantees;
- formal verification of the runner;
- sandboxing for external plugins;
- proof that a hash-pinned plugin is honest;
- theorem-like truth for empirical R4 claims;
- literature priority for the finite hybrid Schur/vdW result.

The plugin boundary is especially important: a hash-pinned malicious plugin cannot
certify a tampered artifact or a rung stronger than it is allowed to earn, but it
can still return `CERTIFIED` on a structurally valid envelope. The controls are
identity, artifact binding, and rung discipline, not magical plugin honesty.

## Failure Modes Reviewers Should Probe

Good reviews should try to break these invariants:

- change artifact bytes without changing the declared hash;
- point an artifact at an absolute, home-relative, remote, or traversal path;
- declare an atomic checker at a stronger rung than its ceiling;
- return a plugin rung stronger than the declared rung;
- corrupt the checker manifest hash;
- make a plugin emit garbage JSON, illegal verdicts, or timeout;
- replace a named human review with a non-human reviewer;
- compose a certified strong barrier with a deferred weak one and try to keep the
  stronger rung.

None of those should produce `CERTIFIED`.

## Current Evidence

The current public artifact has:

- 12 atlas barriers;
- 9 certified, 0 refused, 3 deferred in the local full-toolchain run;
- 18 one-directional safety tests;
- 14 spec conformance fixtures;
- 3 checker manifests;
- CI coverage for atlas checks and spec conformance.

## Next Review Priorities

The highest-value next reviews are:

1. adversarial review of `tools/plugin_runner.py`, because it is now part of the
   trusted base;
2. independent implementation of the conformance runner contract;
3. tightening reason-code classification so fewer cases depend on checker-detail
   text;
4. a small formal model of the rung ceiling and min-trust calculus;
5. later, sandboxing or signing, if external plugin execution becomes more than a
   local prototype.
