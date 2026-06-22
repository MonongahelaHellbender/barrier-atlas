#!/usr/bin/env python3
"""rup_check.py -- an INDEPENDENT, untrusted pure-Python LRAT/RUP checker.

This is the R3 rung: a *second implementation* of the same check the Lean-proved
`checkProofArr` performs, written from scratch in Python. It re-verifies the exact
same flat certificate. Two independent checkers agreeing on the same cert is
strictly weaker than a kernel-proved checker (you now trust THIS code), but it is
real, cheap, cross-implementation corroboration -- the classic "independent
recomputation" rung.

Cert format (mirrors `parseCert` in LratScale.lean):
  "<numClauses> <formula: 0-delimited clauses> <steps: clause 0 hints 0 ...>"
  literals are DIMACS ints (sign = negation); hints are 1-based db indices.

Semantics (mirrors Lrat.lean): grow a clause database; each step's clause must be
RUP-entailed by the current db (assume its negation, unit-propagate along the hint
clauses to a conflict); append it; success iff the empty clause is learned.

Usage: python3 tools/rup_check.py <cert-file>   ->  prints VERIFIED / REFUSED
"""
import sys

# A literal is (var:int, neg:bool). Negation flips neg.
def _lit(i):        return (abs(i), i < 0)
def _flip(l):       return (l[0], not l[1])


def split_on_zero(xs):
    """Split a flat int list into 0-delimited groups, matching splitOnZeroF:
    no trailing empty group when the list ends in 0 (interior empties kept)."""
    groups, cur = [], []
    for v in xs:
        if v == 0:
            groups.append(cur); cur = []
        else:
            cur.append(v)
    if cur:                      # only a non-empty remainder becomes a final group
        groups.append(cur)
    return groups


def parse_cert(text):
    toks = []
    for t in text.split():
        try:
            toks.append(int(t))
        except ValueError:
            pass
    if not toks:
        return [], []
    c, rest = toks[0], toks[1:]
    groups = split_on_zero(rest)
    formula = [[_lit(i) for i in g] for g in groups[:c]]
    steps = []
    sg = groups[c:]
    for k in range(0, len(sg) - 1, 2):          # pair (clause, hints); drop odd tail
        clause = [_lit(i) for i in sg[k]]
        hints = [i - 1 for i in sg[k + 1]]      # 1-based -> 0-based db index
        steps.append((clause, hints))
    return formula, steps


def rup_loop(db, init_trail, hints):
    """Walk hint clauses; each must be unit (propagate) until a conflict (return
    True). Bad index, non-unit, or running out of hints => False (fails closed)."""
    trail = set(init_trail)
    for i in hints:
        if not (0 <= i < len(db)):
            return False                        # bad hint index
        unf = [l for l in db[i] if _flip(l) not in trail]
        if len(unf) == 0:
            return True                         # conflict: refutation complete
        if len(unf) == 1:
            trail.add(unf[0])                   # unit: propagate
        else:
            return False                        # not unit: malformed hint
    return False                                # no conflict reached


def check_rup(db, clause, hints):
    return rup_loop(db, [_flip(l) for l in clause], hints)


def check_proof(formula, steps):
    db = [list(c) for c in formula]
    for n, (clause, hints) in enumerate(steps):
        if not check_rup(db, clause, hints):
            return False, f"step {n} (clause {clause}) is not RUP-entailed"
        db.append(clause)
    if any(len(c) == 0 for c in db):
        return True, f"empty clause derived; {len(formula)} clauses, {len(steps)} steps"
    return False, "ran all steps but never learned the empty clause"


def verify(path):
    formula, steps = parse_cert(open(path, encoding="utf-8").read())
    return check_proof(formula, steps)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: rup_check.py <cert-file>", file=sys.stderr); sys.exit(2)
    ok, detail = verify(sys.argv[1])
    print(f"parsed+checked: {detail}")
    print("VERIFIED" if ok else "REFUSED")
    sys.exit(0 if ok else 1)
