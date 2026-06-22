# Barrier Atlas

**A certified, composable map of impossibility claims** — what provably *cannot*
happen, with each entry carrying a machine-checkable certificate at an explicit
**trust rung**. The impossibility-oriented counterpart to a proof library.

> Sister project to [`lean-verification-journey`](https://github.com/MonongahelaHellbender/lean-verification-journey).
> The thesis there is *verification is the durable skill*. This is its negative
> image: most claims you actually want from AI ("there is **no** input that leaks
> the secret") are *impossibilities*, and an impossibility needs a certificate, not
> a demo. A proved barrier is durable knowledge: once checked, it permanently
> removes a region of the search space from consideration.
>
> For a reviewer-facing map of the surrounding public work, see
> [`PORTFOLIO.md`](PORTFOLIO.md).

## What's here (v0.2)

Nine real barriers, re-checkable from a single envelope format across **five
different evidence kinds**, with the lower-rung ones honestly deferred:

| barrier | claim | rung | checker | status |
|---|---|---|---|---|
| `vdw-3-3-le-27` | every 3-coloring of {1..27} has a mono 3-term AP | R2 | `lratcheck` | ✅ live |
| `vdw-3-3-le-27-r3` | *same claim*, independent re-derivation | R3 | `rup-python` | ✅ live |
| `ramsey-3-4-le-9` | every 2-coloring of K9 has a red K3 or blue K4 | R2 | `lratcheck` | ✅ live |
| `nn-robust-2relu-box` | no adversarial example in [-1,1]² flips the class | R0 | `lean-axioms` | ✅ live |
| `hybrid-schur-vdw-3color-le-13-r2` | no 3-coloring of [13] avoids both Schur triples and 3-term APs | R2 | `lratcheck` | ✅ live |
| `hybrid-schur-vdw-3color-le-13` | no 3-coloring of [13] avoids both Schur triples and 3-term APs | R3 | `hybrid-schur-vdw-exhaustive` | ✅ live |
| `combinatorics-two-bounds` | both W(3,3)≤27 **and** R(3,4)≤9 (composed) | R2 | `composed` | ✅ live |
| `mixed-rung-bundle` | mixed bundle — demonstrates min-trust propagation | R4 | `composed` | ⏸ deferred (propagated) |
| `private-empirical-barrier` | an unpublished empirical barrier (details withheld) | R4 | `manual` | ⏸ deferred (honest) |

```
$ python3 tools/barrier_check.py
  summary: 7 certified, 0 refused, 0 unverifiable-here, 2 deferred
  OK: every LIVE barrier re-checked (or honestly degraded).
```

## The three ideas that make it more than a registry

1. **A rung ladder, declared and *checked*.** Every barrier names its trusted base
   (R0 kernel-only … R4 empirical … R5 conjectural) and the checker *enforces* it.
   The `lean-axioms` checker fails if the theorem leans on even one axiom beyond its
   declared base — it catches a silent rung-slide automatically. See [`PLAN.md`](PLAN.md) §2.1.

2. **The same impossibility at multiple rungs, and a min-trust calculus that composes
   them.** W(3,3)≤27 is certified at R2 by the Lean-proved checker *and* at R3 by an
   independent from-scratch Python checker ([`tools/rup_check.py`](tools/rup_check.py))
   — two implementations agreeing on the same bytes. Composed barriers (`composed`
   checker) recursively re-check their parts and earn the **weakest** rung among them;
   you cannot launder a composite up to a rung none of its parts earned. See
   [`docs/composition-example.md`](docs/composition-example.md).

3. **One-directional by construction.** A checker can only move an entry to
   `REFUSED` or `UNVERIFIABLE-HERE`; the sole path to `CERTIFIED` is a positive check
   passing. Tampered cert, missing tool, extra axiom, laundered rung — all fail
   *closed*. This is the same asymmetric safety the barriers themselves have, and it's
   regression-guarded in [`tests/test_one_directional.py`](tests/test_one_directional.py)
   (11 tests, incl. rung-laundering, encoder-lie refusal, and deterministic RUP
   mutation fuzzing and generated small-cert differential fuzzing against
   `lratcheck` when the sibling binary is available).

## Trust boundary (stated, not hidden)

The `lratcheck` checker proves *the parsed CNF is UNSAT*. The v0 combinatorics
entries now also regenerate the claim CNF from a declared encoder spec and require
an exact match to the original clauses embedded in the cert. The atlas therefore
binds:

- exact certificate bytes by SHA-256;
- parsed clause/step counts;
- the W(3,3), R(3,4), and hybrid Schur/vdW claim-to-CNF encoders.

If any of those drift, the entry is `REFUSED`. What remains trusted is the small
encoder-checking code itself plus the checker trusted base named by each rung.

The hybrid Schur/van der Waerden result now has two entries for the same finite
claim: an R2 CNF/RUP certificate accepted by the Lean-proved checker, and an R3
exhaustive Python recomputation with a checked lower-bound witness for [12]. It
is a new atlas-certified finite result, not a literature-priority claim and not
yet a Lean-formalized combinatorics theorem.

## Layout

```
PLAN.md      vision, rung ladder, composition calculus, roadmap, refinement log
PORTFOLIO.md public reviewer-facing index across the verification artifacts
SCHEMA.md    the envelope spec        schema/barrier.schema.json  machine schema
barriers/    one .barrier.json per certified impossibility
certs/       bundled certificates (sha256-pinned)
tools/       barrier_check.py — dispatcher; rup_check.py — R3 checker; encoder_check.py — v0 CNF binding; hybrid_schur_vdw_check.py / hybrid_schur_vdw_cert.py — hybrid checker + cert generator
tests/       one-directional safety regression tests
docs/        composition worked-example (min-rung arithmetic)
```

## Run it

```bash
python3 tools/barrier_check.py            # re-check every barrier
python3 tests/test_one_directional.py     # prove the checkers fail closed
python3 tools/encoder_check.py certs/samples_w33.cert w33
python3 tools/encoder_check.py certs/hybrid_schur_vdw_3color_13.cert hybrid13
python3 tools/rup_differential_fuzzer.py  # generated RUP certs vs lratcheck when available
python3 tools/hybrid_schur_vdw_check.py   # R3 finite hybrid barrier
python3 tools/hybrid_schur_vdw_cert.py    # R2 hybrid CNF/RUP cert generator
```

Needs Python 3 (stdlib only). The `lratcheck` entries also need the sibling
`lean-verification-journey` built (`lake build lratcheck`); if it's absent the atlas
honestly reports `UNVERIFIABLE-HERE` rather than passing. Override locations with
`LRATCHECK_BIN` / `LEAN_REPO`.

## Status

v0.5 — public and green: 7 checker kinds (`lratcheck`, `lean-axioms`, `rup-python`,
`hybrid-schur-vdw-exhaustive`, `composed`, `multi-region`, `claim-stress`), 12 barriers,
18 safety tests. Highlights: a finite hybrid barrier certified three ways (R2 CNF/RUP +
R3 exhaustive + Lean 4); the **first CERTIFIED R4 empirical barrier** (the chaos
0-1-test no-go), gated by a three-stage stress contract — completeness → adequacy → a
**named** human sign-off, never automated correctness
([`docs/claim-stress-integration.md`](docs/claim-stress-integration.md)); that R4 flows
through the **min-trust composition** calculus as a first-class input; **multi-region
rungs** — one claim partitioned into regions, each at its own rung, earning the weakest
([`docs/composition-example.md`](docs/composition-example.md)); and a **review-calibration**
artifact measuring llm-vs-human false-accept rate, justifying why correctness stays human
([`docs/review-calibration.md`](docs/review-calibration.md)). See [`PLAN.md`](PLAN.md) §4
for what's left: a dashboard / visual negative-space map.
