# Verification Portfolio Index

This is the public, reviewer-facing map of the verification work around Barrier
Atlas. The theme is deliberately narrow: replace informal assurance with claims
that name their trusted base, re-run their evidence, and refuse when a claim
boundary is not earned.

## Public Artifacts

| artifact | what it demonstrates | strongest honest claim | link |
|---|---|---|---|
| Barrier Atlas | A shared envelope for certified impossibilities, independent checkers, min-trust composition, and fail-closed negative tests. | A working protocol demo for checkable negative knowledge, not a production safety guarantee. | <https://github.com/MonongahelaHellbender/barrier-atlas> |
| Lean Verification Journey | Lean 4 proofs, a compiled LRAT checker, public CI, and reproducible certificate checks for known finite combinatorics and a bounded NN robustness theorem. | Formal/computer-assisted verification skill on known results and bounded example properties. | <https://github.com/MonongahelaHellbender/lean-verification-journey> |
| Certified Combinatorics Verification | A self-contained SAT/RUP pipeline for known Schur and van der Waerden values, with self-verified witnesses and optional formally checked layers. | Reproducible certification machinery for known values, not new mathematics. | <https://github.com/MonongahelaHellbender/certified-combinatorics-verification> |

## What Changed After Public Release

- The combinatorics barriers now check the claim-to-CNF binding: W(3,3),
  R(3,4), and the hybrid Schur/vdW clauses are regenerated from declared encoder
  specs and must exactly match the original clauses embedded in the bundled cert.
- The independent Python RUP checker is guarded by deterministic mutation fuzzing
  over both bundled certificates.
- The atlas now includes a new finite hybrid barrier: no 3-coloring of `[13]`
  avoids both monochromatic Schur triples and monochromatic 3-term arithmetic
  progressions, with a checked `[12]` lower-bound witness. This now has an R2
  CNF/RUP certificate accepted by `lratcheck` plus an R3 exhaustive recomputation.
  It is still not a Lean-formalized theorem or literature-priority claim.
- The composition calculus remains one-directional: a composite cannot claim a
  stronger rung than its weakest checked part.

## Claim Boundary

Supported:

- known finite combinatorics certificates can be replayed and cross-checked;
- two independent implementations agree on the W(3,3) certificate;
- cert bytes, parsed shape, and v0 combinatorics encoders are bound to the claims;
- the finite hybrid Schur/AP barrier is certified by a bound CNF/RUP cert and
  independently exhaustively rechecked from a declared spec;
- composed barriers propagate their weakest rung and refuse rung laundering.

Not supported:

- new mathematical discoveries;
- production AI-safety guarantees;
- real-world model-behavior guarantees;
- empirical or unpublished barriers promoted as proofs;
- hidden private project details.

## Best Use

For MATS/ARIA/research-role review, the strongest reading is not "I proved a new
theorem." It is: "I can build small, runnable evidence systems that preserve the
difference between proof, independent recomputation, empirical support, and
refusal."
