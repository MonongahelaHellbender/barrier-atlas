# The barrier envelope (v0.1)

One JSON file per barrier (`barriers/<id>.barrier.json`). The envelope is the unit
of the atlas: a claim of impossibility plus everything needed to *re-check it* and
*know what you're trusting when you do*.

## Fields

| field | required | meaning |
|---|---|---|
| `id` | ✓ | stable kebab-case identifier |
| `schema_version` | ✓ | `"0.1"` |
| `claim.statement` | ✓ | human-readable impossibility, with the named quantity |
| `claim.kind` | ✓ | always `"impossibility"` in v0 (the negative is the point) |
| `claim.negation_of` | ✓ | the (nonexistent) object whose absence is certified |
| `domain` | ✓ | e.g. `combinatorics/van-der-Waerden`, `ml/robustness` |
| `rung.level` | ✓ | `R0`…`R5` (see PLAN.md §2.1) |
| `rung.name` | ✓ | the rung's name, redundant for legibility |
| `rung.trusted_base` | ✓ | explicit list of what is trusted *beyond the bare minimum* |
| `certificate.kind` | ✓ | format of the evidence (`lrat-flat`, `lean-theorem`, `numeric-report`, …) |
| `certificate.path` |  | path to the cert artifact, if any (relative to atlas root) |
| `certificate.meta` |  | free dict (step counts, sizes, source theorem name, …) |
| `certificate.encoder` |  | optional claim-to-CNF generator spec; when present, the parsed cert formula must exactly match the regenerated clauses |
| `checker.kind` | ✓ | how to re-check: `lratcheck`, `lean-axioms`, `rup-python`, `hybrid-schur-vdw-exhaustive`, `composed`, `multi-region`, `claim-stress`, or `manual` (deferred) |
| `checker.*` | ✓ | kind-specific config (see below) |
| `status` | ✓ | `"live"` (auto-checkable now) or `"deferred"` (registered, recipe given) |
| `provenance` | ✓ | where the artifact came from (source package, generation pipeline) |
| `one_directional` | ✓ | the asymmetric-safety statement: a bug can only cause REFUSED, never false CERTIFIED |

## Checker kinds

### `lratcheck` (rung R2 — verified-checker-program)
```json
"checker": {
  "kind": "lratcheck",
  "cert": "certs/samples_w33.cert",
  "accept_pattern": "VERIFIED",
  "binary_env": "LRATCHECK_BIN",
  "binary_default": "../dist/lean-verification-journey/.lake/build/bin/lratcheck"
}
```
Runs the compiled checker on the cert; `CERTIFIED` iff stdout matches
`accept_pattern`. If the binary is absent → `UNVERIFIABLE-HERE`. When
`certificate.encoder` is present, the encoder match is checked before the binary
is invoked, so an encoder mismatch still `REFUSED` on a bare runner.

For v0 combinatorics entries, `certificate.encoder` supports:

```json
"encoder": {
  "kind": "vdw_progression_cnf",
  "n": 27,
  "colors": 3,
  "progression_length": 3
}
```

and:

```json
"encoder": {
  "kind": "ramsey_edge_coloring_cnf",
  "vertices": 9,
  "red_clique": 3,
  "blue_clique": 4
}
```

and:

```json
"encoder": {
  "kind": "hybrid_schur_vdw_cnf",
  "n": 13,
  "colors": 3
}
```

All three require an exact ordered clause match to the original formula embedded
in the flat cert. This closes the v0 claim/CNF binding for W(3,3), R(3,4), and
the finite hybrid Schur/vdW obstruction.

### `lean-axioms` (rung R0/R1 — kernel-checked)
```json
"checker": {
  "kind": "lean-axioms",
  "repo_env": "LEAN_REPO",
  "repo_default": "../dist/lean-verification-journey",
  "lean_file": "LeanVerificationJourney/Ibp.lean",
  "theorem": "net_robust",
  "expected_axioms": ["propext", "Classical.choice", "Quot.sound"]
}
```
Runs `lake env lean <lean_file>`, parses the `'<theorem>' depends on axioms: [...]`
line, and `CERTIFIED` iff the axiom set **exactly equals** `expected_axioms`. Any
*extra* axiom (a silent rung-slide) → `REFUSED`. Missing toolchain → `UNVERIFIABLE-HERE`.

### `rup-python` (rung R3 — independent recomputation)
```json
"checker": { "kind": "rup-python", "cert": "certs/samples_w33.cert" }
```
Re-checks the *same* cert with an independent from-scratch Python LRAT/RUP checker
(`tools/rup_check.py`), with the same sha256 + parsed-count + optional encoder
binding. `CERTIFIED` iff the independent checker agrees. R3, not R2: you now trust
this Python, so it sits one rung below the kernel-proved checker — its value is
cross-implementation corroboration.

### `hybrid-schur-vdw-exhaustive` (rung R3 — exhaustive finite search)
```json
"checker": {
  "kind": "hybrid-schur-vdw-exhaustive",
  "n": 13,
  "colors": 3,
  "lower_bound_witness": [0, 1, 0, 2, 1, 2, 2, 0, 2, 0, 1, 1]
}
```
Runs `tools/hybrid_schur_vdw_check.py` on the declared finite hybrid spec:
avoid monochromatic Schur triples `x+y=z` and monochromatic 3-term arithmetic
progressions. It also validates the lower-bound witness when supplied. R3, not
R2: you trust the Python exhaustive checker and the declared finite spec. The
same finite claim also has a separate R2 `lratcheck` entry when the CNF/RUP
certificate and `hybrid_schur_vdw_cnf` encoder binding verify.

### `composed` (rung = min-trust of the parts)
```json
"checker": {
  "kind": "composed",
  "composition": {
    "sub_barriers": ["vdw-3-3-le-27", "ramsey-3-4-le-9"],
    "step": { "rung": "R0", "description": "conjunction; kernel-trivial join" }
  }
}
```
Recursively re-checks each sub-barrier by `id`, then `CERTIFIED` iff every part
certifies **and** the declared `rung.level` equals the *weakest* (min-trust) rung
among the parts and the composition step. A failing/deferred part propagates; a
declared rung stronger than the weakest link fails closed (no rung-laundering).

### `multi-region` (rung = min-trust over regions of ONE claim)
```json
"checker": {
  "kind": "multi-region",
  "regions": [
    { "region": "threshold-N13", "rung": "R2", "checker": { "kind": "lratcheck", "...": "..." }, "certificate": { "...": "..." } },
    { "region": "tail-N>=14", "rung": "R5", "checker": { "kind": "manual", "promote_recipe": "..." } }
  ]
}
```
One impossibility claim whose domain is partitioned into regions, each with its own
*inline* checker + rung. Runs every region's checker; the barrier earns the **weakest
(min-trust)** region's rung. Any failed/deferred region propagates (most-severe wins);
a declared rung stronger than the weakest region fails closed. Unlike `composed`
(separate claims by `id`), the regions are inline parts of a single claim.

### `claim-stress` (rung R4/R5 — empirical, named-human gate)
```json
"checker": {
  "kind": "claim-stress",
  "claim_text": "the natural-language impossibility claim",
  "declared_rung": "R4",
  "stress_answers": { "<constraint-id>::<generated question>": "answer citing concrete evidence" },
  "human_review": { "kind": "human", "by": "Name", "date": "YYYY-MM-DD", "verdict": "adequate" }
}
```
Three one-directional stages (see [`docs/claim-stress-integration.md`](docs/claim-stress-integration.md)):
**(1) completeness** — every question `claim_bridge` generates for `claim_text` must be
answered, else `REFUSED`; **(2) adequacy** — each answer must cite concrete evidence,
be non-circular, hedge flagged universals, else `REFUSED`; **(3) correctness** — **only
`human_review.kind == "human"` with `verdict == "adequate"` certifies**. A `kind: "llm"`
(or anything non-human) *screens* but returns `DEFERRED` — automation is never a
correctness gate (see [`docs/review-calibration.md`](docs/review-calibration.md)).

### `manual` (deferred)
```json
"checker": { "kind": "manual", "promote_recipe": "…exact steps to make this live…" }
```
Always reports `DEFERRED` with the recipe. For honest registration of R3–R5
barriers that have a real artifact but no automated checker yet.

## The asymmetry that makes it safe

Every checker is **one-directional**: it can move an entry to `REFUSED` or
`UNVERIFIABLE-HERE`, but the only path to `CERTIFIED` is a positive check passing.
A wrong certificate, a corrupted file, a missing tool, an extra axiom — all fail
*closed*. This is the same property the barriers themselves have, and it is the
whole reason the atlas can be trusted without trusting its authors.
