# Frontier Target Packet

Verdict: `FIRST_FRONTIER_RESULT_EARNED_R2_R3_NEXT_FORMALIZATION_OPEN`

Recommendation: market Barrier Atlas as a working evidence discipline with one
bounded new finite atlas result. Do not market it as a new-math priority claim.
The hybrid barrier is now certified two ways: R2 by a CNF/RUP certificate accepted
by the Lean-proved checker, and R3 by exhaustive Python recomputation. The next
substantive leap is a Lean formalization of the finite checker/spec.

## Claim Boundary

This packet supports:

- the first new finite Barrier Atlas entry:
  `hybrid-schur-vdw-3color-le-13`;
- the exact evidence that earned its R2 and R3 promotions;
- the next formalization gate before any stronger claim is made.

This packet does not support:

- a new theorem;
- a literature-priority claim;
- a new public claim that an unsolved problem is settled;
- any production AI-safety guarantee.

## First Earned Target

The first target is now live:

> Every 3-coloring of `[13]` contains either a monochromatic Schur triple
> `x+y=z` or a monochromatic 3-term arithmetic progression.

Evidence:

- R2 checker: `lratcheck` over `certs/hybrid_schur_vdw_3color_13.cert`;
- R2 envelope: `barriers/hybrid-schur-vdw-3color-le-13-r2.barrier.json`;
- R2 binding: `hybrid_schur_vdw_cnf` regenerates 274 clauses and exact-matches
  the cert formula;
- R3 checker: `tools/hybrid_schur_vdw_check.py`;
- R3 envelope: `barriers/hybrid-schur-vdw-3color-le-13.barrier.json`;
- target search: no valid 3-coloring of `[13]`;
- lower-bound witness: a valid 3-coloring of `[12]`, so the threshold is tight
  for the declared hybrid spec;
- boundary: new atlas-certified finite hybrid barrier, not a Lean-formalized
  theorem and not a literature-priority assertion.

## Promotion Gate Used

The frontier entry became `live` only after the following passed:

| gate | requirement |
|---|---|
| finite spec | Schur triples and 3-term AP triples are generated directly from `[n]` |
| CNF binding | the hybrid CNF is regenerated from the spec and exact-matches the cert formula |
| RUP certificate | bundled flat cert has 274 original clauses and 2443 proof steps |
| R2 checker | `lratcheck` accepts the cert with `VERIFIED` |
| lower witness | `[12]` witness validates against both obstruction families |
| target search | exhaustive pruned search finds no valid coloring of `[13]` |
| R3 checker | `barrier_check.py` returns `CERTIFIED` through `hybrid-schur-vdw-exhaustive` |
| claim text | statement names the exact finite object and does not imply a broader theorem |
| provenance | discovery and checker path are documented in the envelope |

## Falsifiers

Promotion is refused if:

- a lower-bound witness contradicts the proposed threshold;
- the checker finds a `[13]` coloring that avoids both obstruction families;
- the result depends on private data or unpublished hand edits;
- the claim requires a theorem stronger than the finite exhaustive search proves;
- the regenerated hybrid CNF differs from the cert formula;
- `lratcheck` refuses or is unavailable for an R2 promotion;
- a future independent checker disagrees.

## Next Concrete Work

Strengthen the new hybrid barrier in one of two ways:

1. formalize the finite checker/spec in Lean;
2. add a second non-Python implementation of the finite checker if a reviewer
   specifically wants broader independent corroboration.

The R2/R3 state is enough for the atlas demo. A Lean path is the next real
confidence jump; anything else is polish or reviewer-specific corroboration.
