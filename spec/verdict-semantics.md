# Verdict Semantics

Barrier Atlas v0.1 uses four verdicts.

| verdict | meaning |
|---|---|
| `CERTIFIED` | Runner-owned gates passed and the checker supplied positive evidence for the declared bounded claim at the declared rung. |
| `REFUSED` | The envelope or evidence failed: hash mismatch, missing artifact, malformed evidence, failed checker, rung laundering, weak answer, or contradiction. |
| `DEFERRED` | Automation reached a boundary that intentionally requires later human or higher-rung work. No certification is minted. |
| `UNVERIFIABLE-HERE` | This environment could not run the check: absent toolchain, crashed checker, or unsupported checker. This is not evidence for or against the claim. |

Severity propagation:

1. `REFUSED` dominates because the evidence contradicted the declared gate.
2. `UNVERIFIABLE-HERE` propagates as local uncertainty.
3. `DEFERRED` propagates when a required gate is intentionally incomplete.
4. `CERTIFIED` is possible only if every required sub-check certifies and the runner's structural gates pass.

The checker may return a raw verdict. The runner emits the final verdict. The runner never upgrades a checker verdict.

Reason codes are closed so a conformance implementation cannot pass by failing for the wrong reason: `OK`, `ARTIFACT_HASH_MISMATCH`, `ARTIFACT_MISSING`, `PATH_REJECTED`, `RUNG_CEILING_EXCEEDED`, `RUNG_LAUNDERING`, `WEAK_ANSWER`, `INCOMPLETE_ANSWERS`, `LLM_NOT_A_GATE`, `UNKNOWN_CHECKER`, `CHECKER_ERROR`, `MANIFEST_INVALID`, `CHECKER_HASH_MISMATCH`, `CHECKER_TIMEOUT`, `DEFERRED_PENDING_HUMAN`, and `WEAK_SUBBARRIER`.
