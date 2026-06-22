# Frontier Target Packet

Verdict: `FIRST_FRONTIER_RESULT_EARNED_R3_NEXT_FORMALIZATION_OPEN`

Recommendation: market Barrier Atlas as a working evidence discipline with one
bounded new finite atlas result. Do not market it as a new-math priority claim.
The next substantive leap is to strengthen the new hybrid barrier from R3
exhaustive recomputation toward an independent SAT/LRAT certificate or a Lean
formalization of the finite checker/spec.

## Claim Boundary

This packet supports:

- the first new finite Barrier Atlas entry:
  `hybrid-schur-vdw-3color-le-13`;
- the exact evidence that earned its R3 promotion;
- the next strengthening gates before any stronger claim is made.

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

- checker: `tools/hybrid_schur_vdw_check.py`;
- envelope: `barriers/hybrid-schur-vdw-3color-le-13.barrier.json`;
- rung: `R3` exhaustive recomputation;
- target search: no valid 3-coloring of `[13]`;
- lower-bound witness: a valid 3-coloring of `[12]`, so the threshold is tight
  for the declared hybrid spec;
- boundary: new atlas-certified finite hybrid barrier, not a formal proof and
  not a literature-priority assertion.

## Promotion Gate Used

The frontier entry became `live` only after the following passed:

| gate | requirement |
|---|---|
| finite spec | Schur triples and 3-term AP triples are generated directly from `[n]` |
| lower witness | `[12]` witness validates against both obstruction families |
| target search | exhaustive pruned search finds no valid coloring of `[13]` |
| checker | `barrier_check.py` returns `CERTIFIED` through `hybrid-schur-vdw-exhaustive` |
| claim text | statement names the exact finite object and does not imply a broader theorem |
| provenance | discovery and checker path are documented in the envelope |

## Falsifiers

Promotion is refused if:

- a lower-bound witness contradicts the proposed threshold;
- the checker finds a `[13]` coloring that avoids both obstruction families;
- the result depends on private data or unpublished hand edits;
- the claim requires a theorem stronger than the finite exhaustive search proves;
- a future independent checker disagrees.

## Next Concrete Work

Strengthen the new hybrid barrier in one of three ways:

1. add an independent second implementation of the finite checker;
2. encode the hybrid spec as CNF and produce an LRAT/RUP certificate;
3. formalize the finite checker/spec in Lean.

Any one of these would raise confidence. Only the second or third can move the
result toward a stronger rung.
