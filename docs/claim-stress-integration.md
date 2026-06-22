# The empirical-rung engine: claim-stress integration (LIVE)

The atlas's formal rungs (R0–R2) are mechanically checkable. The **empirical** rungs
(R3–R5) were the weak spot: "is this *empirical-robust*?" was a judgment call, exactly
the "adjudication creep" risk flagged in [`PLAN.md`](../PLAN.md) §5. This integration
turns that judgment into a **checkable completeness contract**, by wiring in the
[claim-stress-tester](https://github.com/MonongahelaHellbender/claim-stress-tester)
(`tools/claim_bridge.py` + `data/`, vendored).

The governing principle is unchanged: **one-directional**. Every stage can only
*refuse* or *defer* — none can grant a rung from automation alone.

## Three stages (`checker.kind: "claim-stress"`)

A skeptical reviewer of an empirical claim does three separable jobs. They automate
very differently, so the checker keeps them separate (`tools/claim_stress_check.py`):

### Stage 1 — Completeness *(fully automated)*
Run `claim_bridge` on the claim. It generates the structural questions a reviewer
would ask, from a constraint library (model degeneracy, hidden variable, energy/order,
population scope, …). **Every generated question (constraint score ≥ 2) must have a
recorded answer** in `checker.stress_answers`. Any blank → **REFUSE**.

### Stage 2 — Adequacy: the "skeptical reviewer" *(mostly automated)*
Each answer must have the *shape* of a real answer, not a dodge:
- long enough (≥ 25 chars),
- cites **concrete evidence** — a number, an observable (e.g. `Σλ`), an artifact,
- is **not circular** — adds content beyond the question and the claim,
- if the claim has a flagged **universal quantifier**, the answer is **hedged** to a tested scope.

A hand-wave ("yes, it's been checked and is fine") → **REFUSE**. This catches the
failure mode where every question has *an* answer but the answers are empty.

### Stage 3 — Correctness: a **named** verdict *(never automated)*
Whether an answer is *true* is the irreducible inch. The checker requires
`checker.human_review = {kind, by, date, verdict}`:
- `kind: "human"`, `verdict: "adequate"`, with `by` + `date` → **CERTIFY** at the declared rung.
- no/incomplete review → **DEFER** ("automated contract satisfied; awaiting named sign-off").
- `kind: "llm"` (or any non-human) **SCREENS but never CERTIFIES** → it returns **DEFERRED**,
  recording that the answers passed an automated review but still await a *named human*
  verdict. The calibration ([`review-calibration.md`](review-calibration.md)) measured
  llm false-accepts, so automation is an *assist*, not a gate. **Only `kind: "human"`
  certifies.** (Enforced in `claim_stress_check.py` Stage 3; tested.)

**Why correctness can't be automated away:** if you let a model judge correctness and
fold its verdict silently into CERTIFIED, you've added a large, unnamed, unverifiable
trusted base and slid the rung up — the exact move the atlas exists to refuse
("who verifies the verifier?"). For an empirical claim there is no small *proved*
checker possible (that's *why* it's R4 and not R0); the honest anchor is a named human.
Automating it doesn't shrink the trusted base — it hides it. So: **automate the
reviewer's questions, name the reviewer's verdict.**

## Worked example — and why it's the point

The first live R4 entry is [`chaos-01-test-no-separation`](../barriers/chaos-01-test-no-separation.barrier.json):
*"the 0-1 test does not separate conservative from dissipative chaos; Σλ does."*

Run through `claim_bridge`, that claim generates (among others) the
`model_degeneracy` question:

> **"Has the model been tested on data not used to tune it?"**

That is **exactly the robustness check whose absence caused the real 0-1-test
retraction** (the short-trajectory artifact). Under this contract the chaos no-go
*cannot* claim R4 without first answering it — so the stress contract would have
**caught the retraction before it shipped.** The entry answers all 12 generated
questions from the published findings (Σλ across 8 Hamiltonian + 11 dissipative
systems; Green-Kubo r = 0.955; the retracted artifact), passes Stages 1–2, and sits
honestly at **DEFERRED — awaiting a named human sign-off**. One line (`by`, `date`,
`verdict: "adequate"`) promotes it to CERTIFIED R4. *(It is left pending on purpose:
the author's verdict is not something the tooling fabricates.)*

## What it unlocks

- **R4/R5 barriers become genuinely CERTIFIED**, not perpetually deferred — so the
  min-trust **composition** calculus can include empirical barriers as first-class inputs.
- The **adjudication-creep risk is closed**: the rung is now "did you answer every
  generated question, with real answers, signed by a named reviewer," not a vibe.
- Other no-gos (the OMD contract failures, a 3n+1 conjecture, more chaos diagnostics)
  load the same way.

## Honest limits

- `claim_bridge` is keyword/pattern-based; its question coverage is heuristic, not
  exhaustive. So `claim-stress` certifies **answer-completeness + answer-shape + a named
  verdict** — *not* that the empirical claim is true. The named human (or disclosed llm)
  carries truth. That is a bounded, honest guarantee, and strictly better than an
  unchecked "trust me, it's R4." The trusted base is printed in each envelope.
- Roadmap: a calibrated **llm-reviewed vs human-reviewed** comparison on the same
  barriers — itself a publishable artifact about where automated review is trustworthy.
