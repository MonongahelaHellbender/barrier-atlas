#!/usr/bin/env python3
"""review_calibration.py -- where is automated (llm) review trustworthy?

The `claim-stress` engine keeps *correctness* with a named human, and allows an
`llm` sign-off only at a disclosed, weaker tier. This harness measures *how much*
weaker, on the only axis that matters for a one-directional gate:

    FALSE-ACCEPT RATE = P(llm verdict = adequate | human verdict = inadequate)

A false accept means an llm reviewer would certify an answer a human would reject --
the one failure that can mint a barrier it shouldn't. A false *reject* (llm too
harsh) is only a cost; it over-defers, which is safe. So an llm sign-off is safe as a
GATE iff its false-accept rate is ~0; otherwise it is an ASSIST only -- exactly the
atlas's design (`llm` certifies disclosed-weaker, never wears the human badge).

Input: a JSONL where each line is {id, question, answer, human_verdict, llm_verdict}
with verdicts in {"adequate","inadequate"}. Usage:
    python3 tools/review_calibration.py [data/review_calibration_seed.jsonl]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data" / "review_calibration_seed.jsonl"
VERDICTS = {"adequate", "inadequate"}


def load(path: Path):
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        it = json.loads(line)
        if it["human_verdict"] not in VERDICTS or it["llm_verdict"] not in VERDICTS:
            raise ValueError(f"bad verdict in item {it.get('id')}")
        items.append(it)
    return items


def score(items):
    cm = {(h, l): 0 for h in VERDICTS for l in VERDICTS}
    for it in items:
        cm[(it["human_verdict"], it["llm_verdict"])] += 1
    human_inadequate = cm[("inadequate", "adequate")] + cm[("inadequate", "inadequate")]
    human_adequate = cm[("adequate", "adequate")] + cm[("adequate", "inadequate")]
    false_accept = cm[("inadequate", "adequate")]
    false_reject = cm[("adequate", "inadequate")]
    n = len(items) or 1
    return {
        "n": len(items),
        "agreement_rate": round((cm[("adequate", "adequate")] + cm[("inadequate", "inadequate")]) / n, 3),
        "false_accept": false_accept,
        "false_accept_rate": round(false_accept / human_inadequate, 3) if human_inadequate else None,
        "false_reject": false_reject,
        "false_reject_rate": round(false_reject / human_adequate, 3) if human_adequate else None,
        "confusion": {f"human={h},llm={l}": cm[(h, l)] for h, l in cm},
        "llm_safe_as_gate": false_accept == 0,
    }


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT
    if not path.exists():
        print(f"no calibration set at {path}", file=sys.stderr)
        return 2
    items = load(path)
    s = score(items)
    print("\n  LLM-vs-human review calibration\n")
    print(f"  items: {s['n']}   agreement: {s['agreement_rate']}")
    print(f"  confusion: {s['confusion']}")
    print(f"  FALSE-ACCEPT (llm passes what human fails): {s['false_accept']} "
          f"(rate {s['false_accept_rate']})   <- the safety-critical number")
    print(f"  false-reject (llm harsher than human):     {s['false_reject']} "
          f"(rate {s['false_reject_rate']})   <- only a cost")
    if s["llm_safe_as_gate"]:
        print("\n  VERDICT: 0 false accepts on this set -- llm review could act as a gate here.\n")
    else:
        print("\n  VERDICT: llm review has >0 false accepts -- NOT safe as a correctness gate;\n"
              "  it stays a disclosed-weaker ASSIST, and the named human keeps the verdict.\n"
              "  (This is the empirical justification for the claim-stress Stage-3 design.)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
