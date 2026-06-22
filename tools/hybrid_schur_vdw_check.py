#!/usr/bin/env python3
"""Exhaustively check a hybrid Schur / van der Waerden finite barrier.

A coloring of [1..n] is valid when it avoids BOTH:
- monochromatic Schur triples x + y = z, with x <= y;
- monochromatic 3-term arithmetic progressions a, a+d, a+2d.

This checker is deliberately small and exact. It is R3-style exhaustive
recomputation: no solver is trusted, but the Python search code is part of the
trusted base. It also verifies a lower-bound witness when supplied.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TripleSet:
    schur: tuple[tuple[int, int, int], ...]
    ap: tuple[tuple[int, int, int], ...]

    @property
    def all(self) -> tuple[tuple[int, int, int], ...]:
        # Deduplicate because small triples such as (1,2,3) are both Schur and AP.
        return tuple(sorted(set(self.schur + self.ap)))


def triples(n: int) -> TripleSet:
    schur: list[tuple[int, int, int]] = []
    ap: list[tuple[int, int, int]] = []
    for x in range(1, n + 1):
        for y in range(x, n + 1):
            z = x + y
            if z <= n:
                schur.append((x, y, z))
    for a in range(1, n + 1):
        for d in range(1, n + 1):
            b = a + d
            c = a + 2 * d
            if c <= n:
                ap.append((a, b, c))
    return TripleSet(tuple(schur), tuple(ap))


def _bad_triple(coloring: list[int | None], triple: tuple[int, int, int]) -> bool:
    vals = [coloring[i - 1] for i in triple]
    return vals[0] is not None and vals[0] == vals[1] == vals[2]


def validate_coloring(coloring: list[int], colors: int) -> tuple[bool, str]:
    if any((not isinstance(c, int)) or c < 0 or c >= colors for c in coloring):
        return False, "color outside declared range"
    t = triples(len(coloring))
    c2: list[int | None] = list(coloring)
    for triple in t.schur:
        if _bad_triple(c2, triple):
            return False, f"monochromatic Schur triple {triple} in color {c2[triple[0] - 1]}"
    for triple in t.ap:
        if _bad_triple(c2, triple):
            return False, f"monochromatic 3-term AP {triple} in color {c2[triple[0] - 1]}"
    return True, "valid hybrid-avoiding coloring"


def find_coloring(n: int, colors: int, stop_after_first: bool = True) -> dict[str, Any]:
    t = triples(n).all
    by_max: dict[int, list[tuple[int, int, int]]] = {}
    for triple in t:
        by_max.setdefault(max(triple), []).append(triple)

    coloring: list[int | None] = [None] * n
    nodes = 0
    solutions: list[list[int]] = []

    def rec(pos: int) -> bool:
        nonlocal nodes
        nodes += 1
        if pos > n:
            solutions.append([int(c) for c in coloring])
            return stop_after_first
        for color in range(colors):
            coloring[pos - 1] = color
            if not any(_bad_triple(coloring, triple) for triple in by_max.get(pos, [])):
                if rec(pos + 1):
                    return True
            coloring[pos - 1] = None
        return False

    rec(1)
    return {
        "n": n,
        "colors": colors,
        "nodes_visited": nodes,
        "solution_count_recorded": len(solutions),
        "first_solution": solutions[0] if solutions else None,
        "exists": bool(solutions),
        "schur_triple_count": len(triples(n).schur),
        "ap_triple_count": len(triples(n).ap),
        "combined_unique_triple_count": len(t),
    }


def check_barrier(n: int, colors: int, lower_witness: list[int] | None = None) -> tuple[bool, str, dict[str, Any]]:
    lower_detail: dict[str, Any] = {}
    if lower_witness is not None:
        ok, detail = validate_coloring(lower_witness, colors)
        lower_detail = {
            "lower_bound_witness_n": len(lower_witness),
            "lower_bound_witness_valid": ok,
            "lower_bound_witness_detail": detail,
        }
        if not ok:
            report = {"lower_bound": lower_detail}
            return False, f"lower-bound witness invalid: {detail}", report

    search = find_coloring(n, colors, stop_after_first=True)
    report = {"target_search": search, "lower_bound": lower_detail}
    if search["exists"]:
        return False, f"counterexample found: {search['first_solution']}", report
    return True, f"no {colors}-coloring of [1..{n}] avoids both Schur triples and 3-term APs", report


def _parse_witness(text: str | None) -> list[int] | None:
    if not text:
        return None
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=13)
    parser.add_argument("--colors", type=int, default=3)
    parser.add_argument("--lower-witness", default="0,1,0,2,1,2,2,0,2,0,1,1")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    witness = _parse_witness(args.lower_witness)
    ok, detail, report = check_barrier(args.n, args.colors, witness)
    report.update({"ok": ok, "detail": detail})
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(("CERTIFIED" if ok else "REFUSED") + f": {detail}")
        if report.get("lower_bound"):
            print("lower witness:", report["lower_bound"])
        print("target search:", report["target_search"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
