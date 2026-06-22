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
| `checker.kind` | ✓ | how to re-check: `lratcheck`, `lean-axioms`, `manual` (deferred) |
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
`accept_pattern`. If the binary is absent → `UNVERIFIABLE-HERE`.

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
(`tools/rup_check.py`), with the same sha256 + parsed-count binding. `CERTIFIED` iff
the independent checker agrees. R3, not R2: you now trust this Python, so it sits one
rung below the kernel-proved checker — its value is cross-implementation corroboration.

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
