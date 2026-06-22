#!/usr/bin/env python3
"""claim_stress_check.py -- the R4/R5 rung engine for empirical barriers.

Turns the fuzzy "is this empirical-robust?" judgment into a CHECKABLE completeness
contract, in three one-directional stages. None of them can *grant* a rung from
automation alone; each can only cap or refuse.

  Stage 1 -- COMPLETENESS. Run the claim-stress-tester (`claim_bridge`) on the
    claim; it generates the structural questions a skeptical reviewer would ask
    (from a constraint library: model degeneracy, hidden variable, ...). Every
    generated question must have a recorded answer in the envelope. Missing -> REFUSE.

  Stage 2 -- ADEQUACY (the "skeptical reviewer"). Each answer must have the SHAPE
    of a real answer: long enough, cites concrete evidence (a number/observable/
    artifact), is not circular (adds content beyond the question/claim), and -- for
    a flagged universal quantifier -- is hedged. A dodge/hand-wave -> REFUSE.

  Stage 3 -- CORRECTNESS. NOT automated. Requires a NAMED human sign-off
    (`human_review.kind == "human"`, `by`, `date`, `verdict == "adequate"`) to
    certify R4. An `llm` or other non-human review can screen answers, but returns
    DEFERRED; it never certifies. No human sign-off -> DEFER (automated contract
    met, awaiting the named verdict). Automating the correctness verdict with a
    model would be rung-laundering -- the one thing the atlas refuses.

Returns (status, detail) where status in {CERTIFIED, REFUSED, UNVERIFIABLE, DEFERRED}.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claim_bridge  # noqa: E402  (vendored claim-stress-tester)

CERTIFIED, REFUSED, UNVERIFIABLE, DEFERRED = (
    "CERTIFIED", "REFUSED", "UNVERIFIABLE-HERE", "DEFERRED")

THRESHOLD = 2          # a truth-constraint's gap_questions become required at score >= this
MIN_ANSWER_LEN = 25    # below this an answer is too thin to be real

# A concrete answer cites SOMETHING checkable: a number, an observable, an artifact.
_CONCRETE = re.compile(
    r"\d|Σλ|sigma|lyapunov|green[- ]?kubo|dataset|held[- ]?out|trajector|run[- ]?length|"
    r"replicat|independent|measured|verified|retract|n\s*=|sample|systems|parameter|observable",
    re.I)
# Hedge words that keep a universal claim honest about its scope.
_HEDGE = re.compile(
    r"restrict|within|tested family|not claimed beyond|subset|only|bounded|scope|autonomous|studied",
    re.I)
_STOP = set((
    "the a an of to in is are it that this and or no not does do did with for on as by we "
    "be been has have had was were which what where when how why who whom whose any all every "
    "would could should may might can will its their there here than then so such into out").split())


def _content(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 2}


def required_questions(report):
    """The questions that MUST be answered, keyed `<constraint-id>::<question>`."""
    req = {}
    for c in report.get("truth_constraints", []):
        if c.get("score", 0) >= THRESHOLD:
            for q in c.get("gap_questions", []):
                req[f"{c['id']}::{q}"] = c["id"]
    for flag in report.get("unknown_flags", []):
        if "Universal quantifier" in flag:
            req["scope::universal-quantifier"] = "scope"
    return req


def evaluate(env: dict):
    chk = env.get("checker", {})
    claim = (chk.get("claim_text") or "").strip()
    if not claim:
        return REFUSED, "no claim_text to stress-test"
    try:
        report = claim_bridge.build_claim_bridge(claim, save=False)
    except Exception as e:  # noqa: BLE001
        return UNVERIFIABLE, f"claim_bridge unavailable: {e}"

    req = required_questions(report)
    if not req:
        return UNVERIFIABLE, "no stress questions generated (claim too sparse to contract)"
    answers = chk.get("stress_answers", {}) or {}

    # Stage 1 -- completeness
    missing = [q for q in req if not str(answers.get(q, "")).strip()]
    if missing:
        return REFUSED, (f"completeness: {len(missing)}/{len(req)} stress questions unanswered "
                         f"(e.g. {missing[0]})")

    # Stage 2 -- adequacy (skeptical reviewer)
    weak = []
    claim_content = _content(claim)
    for q in req:
        a = str(answers[q]).strip()
        qtext = q.split("::", 1)[-1]
        if len(a) < MIN_ANSWER_LEN:
            weak.append((q, "too short")); continue
        if not _CONCRETE.search(a):
            weak.append((q, "no concrete evidence (number/observable/artifact)")); continue
        if len(_content(a) - _content(qtext) - claim_content) < 3:
            weak.append((q, "circular: restates the question/claim, adds no content")); continue
        if q == "scope::universal-quantifier" and not _HEDGE.search(a):
            weak.append((q, "universal quantifier not hedged to a tested scope")); continue
    if weak:
        return REFUSED, f"adequacy: {len(weak)} weak answer(s) (e.g. {weak[0][0]} -> {weak[0][1]})"

    # Stage 3 -- correctness: ONLY a named human sign-off certifies. An automated
    # (llm) reviewer can SCREEN but never CERTIFY, because llm review false-accepts
    # (measured in docs/review-calibration.md) -- so it is an assist, not a gate.
    # Letting automation certify would be the rung-laundering the atlas refuses.
    hr = chk.get("human_review", {}) or {}
    kind = hr.get("kind", "human")
    by, date, verdict = hr.get("by", ""), hr.get("date", ""), hr.get("verdict", "")
    if verdict != "adequate" or not by or not date:
        return DEFERRED, (f"automated stress contract satisfied ({len(req)} answered + adequate); "
                          f"awaiting named human sign-off (verdict={verdict or 'pending'!r})")
    if kind != "human":
        return DEFERRED, (f"{len(req)} answered + adequate; {kind}-SCREENED adequate by {by} ({date}) "
                          f"-- but {kind} review is NOT a correctness gate (measured false-accept; "
                          f"see docs/review-calibration.md). Awaiting a NAMED HUMAN sign-off to certify.")
    return CERTIFIED, (f"{len(req)} stress Qs answered + adequacy-screened; "
                       f"human sign-off by {by} ({date})")
