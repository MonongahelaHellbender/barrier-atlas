# Frontier Target Packet

Verdict: `FRONTIER_TARGET_PACKET_READY_NEW_RESULT_NOT_CLAIMED`

Recommendation: do not market Barrier Atlas as a new-math result. Market it as a
working evidence discipline. The next substantive leap is a genuinely new or
previously un-machine-checked certified impossibility, but that is a research
project and must enter through the same fail-closed gate as the existing barriers.

## Claim Boundary

This packet supports:

- a ranked path toward a future new certified-impossibility entry;
- the exact evidence required before such an entry may be promoted;
- falsifiers that would block promotion.

This packet does not support:

- a new theorem;
- a new bound;
- a new public claim that an unsolved problem is settled;
- any production AI-safety guarantee.

## First Target Shape

Start with a finite combinatorics barrier where the complete loop is small enough
to run publicly:

1. define a human-readable forbidden-object claim;
2. implement the encoder in `tools/encoder_check.py`;
3. generate a SAT/UNSAT boundary pair;
4. produce a RUP/LRAT certificate for the UNSAT side;
5. add an atlas envelope with sha256, parsed shape, and encoder exact-match;
6. add a negative lower-bound witness if the claim is an exact threshold;
7. add one fuzzer or tamper test that tries to break the new checker path.

The first good candidate should be "new to this atlas" before it tries to be
"new to mathematics." A clean, public, certificate-backed result in a neglected
small finite family is more valuable than a speculative large target.

## Promotion Gate

A future frontier entry may become `live` only if all of the following pass:

| gate | requirement |
|---|---|
| encoder | regenerated CNF exactly matches the original clauses embedded in the cert |
| cert bytes | sha256 pinned and matched |
| shape | original clause count and proof-step count match the envelope |
| checker | at least one verifier returns `CERTIFIED` |
| refusal | at least one mutation/tamper case returns `REFUSED` |
| claim text | statement names the exact finite object and does not imply a broader theorem |
| provenance | command path from encoder to cert is documented |

## Falsifiers

Promotion is refused if:

- the encoder produces the right clause count but a different ordered formula;
- a lower-bound witness contradicts the proposed threshold;
- the proof only verifies after manual editing that is not recorded;
- the result depends on unpublished/private project data;
- the claim requires a theorem stronger than the finite SAT instance proves;
- the negative tests cannot make the checker refuse.

## Next Concrete Work

Add `tools/frontier_probe.py` only after selecting one finite family. It should
emit a machine-readable packet with:

- candidate claim;
- encoder spec;
- SAT/UNSAT boundary;
- generated CNF hash;
- proof command;
- expected atlas rung;
- refusal tests to add with the entry.

Until then, this packet is the honest frontier status: ready to execute, not yet
a discovery.
