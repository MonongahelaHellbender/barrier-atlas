# Composition: the min-rung calculus (LIVE — auto-checked)

This is the frontier idea of the atlas — barriers that **compose**, with a trust
rung that propagates. It is now **implemented and checked**: the `composed` checker
in `tools/barrier_check.py` recursively re-checks sub-barriers and enforces the
min-trust rung. Two live composed barriers exercise it:

- `combinatorics-two-bounds` — conjoins the two R2 combinatorics barriers; min-trust
  rung `max(R2,R2,R0)=R2`; **CERTIFIED** after both parts re-check.
- `mixed-rung-bundle` — mixes the deferred R4 barrier with a live R2 one;
  honestly **DEFERRED** (the weak link propagates).

What is *deliberately still roadmap* (Pass 4 scope guard, to avoid adjudication
creep): **multi-region** rungs — a single barrier holding at different rungs on
different regions of its domain. The example below uses an atomic, single-rung join.

## The rule

> A barrier built from sub-barriers earns the **minimum** rung of its parts (the
> weakest link), *unless the composition step is itself certified at a higher rung.*

Formally, if barrier `C` is derived from `A` and `B` by an inference step `s`, then
`rung(C) = min(rung(A), rung(B), rung(s))`. The composition step `s` is itself a
claim that needs its own rung — it is not free.

## Worked example

Suppose we want barrier **C**: *"no configuration of type X exists."* We have:

- **A** (rung **R0**, kernel-checked): "every X reduces to a finite CNF `φ_X`."
  *(a Lean-proved reduction lemma — trusted base: propext, Quot.sound)*
- **B** (rung **R2**, verified-checker-program): "`φ_X` is UNSAT."
  *(an `lratcheck` certificate — trusted base: + compiler + parser)*
- **s** (the composition): "A and B together give C." If `s` is a one-line Lean
  `exact`/`modus ponens` that the kernel checks, `rung(s) = R0`.

Then `rung(C) = min(R0, R2, R0) = R2`. **C is an R2 barrier** — you cannot honestly
advertise the kernel-only strength of A once the UNSAT half rode in on a compiled
program. The atlas would record C with `trusted_base` = the *union* of A's, B's, and
s's trusted bases, and `rung` = R2.

## Why min, and why the step isn't free

The two failure modes this prevents:

1. **Laundering rungs upward.** Without the rule, you could cite the R0 reduction
   and quietly imply the whole result is kernel-only, hiding the R2 dependency. Min
   forbids it: the weakest link sets the strength.
2. **Forgetting the glue.** The composition step `s` is itself a claim. A hand-wave
   "and therefore C" is at best R5. The rule makes the glue carry a rung too, so an
   informal join can't silently upgrade a chain of formal parts.

## Partial / regional barriers

A barrier can hold at **different rungs on different regions** — e.g. a barrier
that is rigorous on a subspace but only R4-numerical elsewhere. The envelope would
carry a `regions: [{domain, rung}, …]` list, and
the *overall* rung is the min across regions. v0 represents this only narratively in
the deferred entry; the regional schema and its checker are roadmap (PLAN.md §4.3).

## What an automated checker would do

Given a composed envelope listing sub-barrier ids + the step's evidence, the checker
would: (1) recursively re-check each sub-barrier, (2) check the step's own
certificate, (3) compute `min` of the resulting rungs, (4) assert it equals the
declared rung — failing closed if any part is weaker than advertised. Same
one-directional discipline as the atomic checkers; this is the natural next build.
