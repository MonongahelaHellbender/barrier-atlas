# Barrier Atlas — Plan & Scaffold

> A certified, composable map of the **negative space**: what provably *cannot*
> happen, each entry carrying a machine-checkable certificate at an explicit
> **trust rung**. The impossibility dual of a proof library.

Sister project to `lean-verification-journey` / `certified-combinatorics-verification`.
Status: **v0.1 public, green, and claim-boundary hardened.**

---

## 1. Why this exists (the bet)

The failure mode of cheap AI generation is not lying — it's **thrashing**:
re-deriving and re-trying things that are already ruled out, because the map of
"ruled out, and how solidly" lives in researchers' heads and dead threads, in a
form no agent can *check and trust*.

A certified barrier atlas is the antidote, and it has a property a good AI future
needs: **negative knowledge compounds and never decays.** A proved impossibility
is true forever; a barrier certified today still prunes the search tree decades on.
And nearly every safety property anyone actually wants from AI ("there is **no**
input that makes it leak the secret") is an *impossibility* claim — exactly the
shape that needs a certificate, not a demo.

The insight that seeded this: the existing portfolio is *already* a pile of
certified impossibilities — UNSAT bounds (no valid coloring), NN robustness (no
adversarial example in the box), and several barriers from ongoing unpublished
research. They were never named as one thing. This project names them, gives them a
shared envelope, and makes them re-checkable by a stranger.

## 2. Core objects

### 2.1 The trust ladder (rungs), strongest first

| rung | name | what you trust | example |
|---|---|---|---|
| **R0** | kernel-checked | Lean kernel only (`propext, Quot.sound`) | S(2) ≤ 4 by `decide` |
| **R1** | compiler-assisted | + Lean compiler (`ofReduceBool`) / classical String API (`Classical.choice`) | W(2,4) ≤ 35 by `native_decide` |
| **R2** | verified-checker-program | + a *proven-correct* checker compiled to a program, run on a cert from file; output is a program run | W(2,5) ≤ 178 via `lratcheck` / `cake_lpr` |
| **R3** | independent recomputation | + an *untrusted* re-implementation that independently agrees | RUP re-check in Python agreeing with the solver |
| **R4** | empirical-robust | + a numerical/eval argument with stress tests; explicitly *not* a proof | a numerically robust floor no tested perturbation breaches |
| **R5** | conjectural | argued, uncertified | an argued-but-uncertified barrier from ongoing work |

The skill is never "make the trusted base zero" — it's **knowing exactly which
rung you are on and refusing to silently slide up one.** The atlas makes the rung
a first-class, declared, *checked* field.

### 2.2 The composition calculus (the frontier piece)

Barriers compose. A barrier built from sub-barriers earns the **min** rung of its
parts (weakest link) — *unless* the composition step is itself certified at a
higher rung. Partial barriers ("rigorous on a subspace, R4-numerical elsewhere")
are first-class, not footnotes: they carry a *per-region* rung. This rung-arithmetic
is the genuinely new object — the negative dual of a proof's dependency graph.

> **Deliberate v0.1 scope guard:** the live composition calculus is limited to
> conjunctive composition with explicit sub-barriers and a checked min-trust rung.
> Multi-region or fuzzy empirical composition stays out of the live set until it
> has its own refusal cases.

### 2.3 The envelope

One JSON file per barrier: `{ claim, domain, rung, certificate, checker, status,
provenance, one_directional }`. Spec in [`SCHEMA.md`](SCHEMA.md); machine schema in
[`schema/barrier.schema.json`](schema/barrier.schema.json).

### 2.4 The dispatcher

`tools/barrier_check.py` reads envelopes, dispatches by `checker.kind`, and reports
`CERTIFIED | REFUSED | DEFERRED | UNVERIFIABLE-HERE`. It is **one-directional like
the barriers it checks**: a missing tool or bad cert can only *fail to certify* —
never a false CERTIFIED.

## 3. v0 deliverable (this execution)

A runnable atlas that re-checks **real** barriers across **≥2 different evidence
kinds** from one envelope format, with honest deferrals for the rest:

- **LIVE / R2** — `vdw-3-3` (W(3,3) ≤ 27) and `ramsey-3-4` (R(3,4) ≤ 9) via the
  `lratcheck` compiled checker on bundled certs. *(checker kind: `lratcheck`)*
- **LIVE / R0–R1** — `nn-robust-2relu` (no adversarial example flips the class on
  `[-1,1]²`) via the Lean `#print axioms` audit of `net_robust`.
  *(checker kind: `lean-axioms` — a genuinely different evidence kind)*
- **DEFERRED / R4** — `private-empirical-barrier` (an unpublished empirical barrier,
  specifics withheld): a real barrier with no automated checker yet; registered
  honestly with the exact recipe to promote it. This *is* the demonstration of the
  lower rungs.

Success = `barrier_check.py barriers/*.barrier.json` runs green on the LIVE set,
honestly reports the deferred entries, and checks bytes + shape + v0 encoders for
the certificate-backed combinatorics claims.

## 4. Milestones

1. ✅ **DONE** — `lean-axioms` checker asserts the *exact* declared axiom set, failing
   on any extra axiom (auto-detects a silent rung-slide).
2. ✅ **DONE** — R3 independent re-derivation: a from-scratch pure-Python LRAT checker
   (`tools/rup_check.py`) re-verifies the *same* cert the Lean checker does. Same claim
   (W(3,3)≤27) now lives at **two rungs** (R2 `lratcheck` + R3 `rup-python`).
3. ✅ **DONE** — the composition calculus: a `composed` checker recursively re-checks
   sub-barriers and enforces min-trust (weakest-link) rung arithmetic; rung-laundering
   fails closed. Two live composed barriers (one CERTIFIED, one DEFERRED-by-propagation).
4. ✅ **DONE** — v0 encoder binding: W(3,3) and R(3,4) CNFs are regenerated from
   declared specs and must exactly match the original clauses embedded in the cert.
5. ✅ **DONE** — portfolio index and stronger safety tests: reviewer-facing
   [`PORTFOLIO.md`](PORTFOLIO.md), encoder-lie refusal, and deterministic RUP
   mutation fuzzing.
6. ⏭ Multi-*region* rungs (a barrier holding at different rungs on different regions;
   schema `regions: [...]` + a regional checker).
7. ⏭ A web/`/barrier-atlas` view on the Foundation dashboard (visual negative-space map).
8. ✅ **DONE (R3, bounded)** — first new finite atlas barrier:
   `hybrid-schur-vdw-3color-le-13` certifies that no 3-coloring of `[13]`
   avoids both monochromatic Schur triples and monochromatic 3-term APs, while a
   checked `[12]` witness keeps the threshold tight for this declared spec. This
   is an atlas-certified exhaustive-computation result, not a formal proof or
   literature-priority claim.
9. ⏭ Strengthen the new hybrid barrier: independent implementation, SAT/LRAT
   certificate, or Lean formalization of the finite checker/spec.

## 5. Honest risks

- **Adjudication creep.** Lower rungs (R3–R5) are judgment calls. Mitigation:
  keep R3 live only when it is an explicit independent recomputation, keep R4+
  entries registered/deferred unless they have an automated checker, and require
  refusal tests for every new checker path.
- **Solo maintenance.** Each entry needs a real artifact. Mitigation: seed only from
  results that already exist and are already certified elsewhere.
- **"Just a registry" critique.** The novelty is the *rung calculus + heterogeneity*,
  not the JSON. v0 must show ≥2 evidence kinds or it doesn't make the point.

---

## Refinement log (the loop)

- **Pass 1 — naive scaffold.** Envelope + dispatcher + the two `lratcheck` combinatorics
  entries. *Problem found:* both entries are the **same evidence kind**, so they don't
  demonstrate the core thesis (one protocol, *heterogeneous* evidence).
- **Pass 2 — heterogeneity requirement.** Added the hard rule: v0 must wire **≥2 distinct
  checker kinds.** Promoted NN-robustness to LIVE via a new `lean-axioms` checker after
  verifying `lake env lean` re-emits the `#print axioms` audit reliably (it does).
- **Pass 3 — make the tool itself one-directional.** Required graceful degradation: if a
  checker binary/toolchain is absent, the entry downgrades to `UNVERIFIABLE-HERE`, never a
  silent pass. The dispatcher inherits the same asymmetric-safety property as the barriers
  it checks — a pleasing recursion, and the honest behavior.
- **Pass 4 — scope discipline on composition.** The rung-calculus is the frontier idea but
  the adjudication risk is real, so it is *specified* but explicitly **excluded from the v0
  live set** (one `docs/` worked example, no auto-checker). Ship atomic, honest, green.
- **Pass 5 — negative testing exposed a real overclaim, now fixed.** Running a tamper test
  (mangle the cert's count token) made `lratcheck` certify a *different* formula as VERIFIED —
  no soundness break (`checkProofArr_unsat` is kernel-proved), but the cert wasn't bound to the
  *claim*. The `one_directional` field was overstated. Fix: pin each cert by **sha256** + cross-
  check the parser's reported clause/step counts against declared meta, both failing closed; and
  reword `one_directional` to name the remaining trusted link honestly (the **encoder**: that the
  CNF really encodes the combinatorial claim — trusted, not re-checked here). The two negative
  cases are now permanent regression tests (`tests/test_one_directional.py`). Lesson: the safety
  *claim* was cheap; the safety *property* only became real once a negative test tried to break it.
- **Pass 6 — two independent checkers > one, and trust must compose.** Added the R3
  `rup-python` re-derivation (same cert, second implementation — it agreed in <0.1s) and the
  `composed` min-trust calculus. The composition checker is itself one-directional: a laundered
  rung (declaring a composite stronger than its weakest part) fails closed, now a permanent test.
  Design choice held from Pass 4: composition shipped *atomic+conjunctive* only — the worked min-
  trust example is real and checked, multi-region rungs stay roadmap to avoid adjudication creep.
- **Pass 7 — close the v0 encoder gap.** Added `tools/encoder_check.py`, declared
  encoder specs in the W(3,3) and R(3,4) envelopes, and made `barrier_check.py`
  require exact formula matches before certification. The former "trusted encoder"
  boundary is now a checked v0 boundary for these two families. A deliberately
  wrong encoder spec is a permanent refusal test.
- **Pass 8 — reviewer leverage without overclaiming.** Added `PORTFOLIO.md` as a
  public index across the verification artifacts and `docs/frontier-targets.md` as
  the next-result packet. The latter is explicitly `NEW_RESULT_NOT_CLAIMED`: it
  defines the gate for a future frontier entry without pretending one has been earned.
- **Pass 9 — first new finite atlas barrier.** Added a live R3 exhaustive checker
  for the hybrid Schur/van der Waerden spec: avoid monochromatic Schur triples
  `x+y=z` and monochromatic 3-term APs simultaneously. The checker validates a
  `[12]` witness and exhaustively refuses all `[13]` colorings. The claim is new
  to the atlas and not merely another known-value SAT replay; it remains bounded
  as R3 because the Python checker/spec are trusted.
