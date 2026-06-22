#!/usr/bin/env python3
"""encoder_check.py -- regenerate claim CNFs and bind cert bytes to the claim.

The LRAT/RUP checkers prove that the *parsed CNF* is UNSAT. This module checks
the remaining mechanical link for the v0 combinatorics barriers: regenerate the
CNF from the declared combinatorial specification and require an exact match to
the original clauses embedded at the front of the flat cert.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import rup_check
from hybrid_schur_vdw_check import triples


def _var(point: int, color: int, colors: int) -> int:
    """Point-major, zero-based colors, one-based DIMACS variables."""
    return (point - 1) * colors + color + 1


def _lit_to_int(lit: tuple[int, bool]) -> int:
    var, neg = lit
    return -var if neg else var


def _parsed_formula(cert: Path) -> list[list[int]]:
    formula, _steps = rup_check.parse_cert(cert.read_text(encoding="utf-8"))
    return [[_lit_to_int(lit) for lit in clause] for clause in formula]


def _vdw_progression_cnf(spec: dict) -> list[list[int]]:
    n = int(spec["n"])
    colors = int(spec["colors"])
    length = int(spec["progression_length"])
    clauses: list[list[int]] = []

    for point in range(1, n + 1):
        clauses.append([_var(point, color, colors) for color in range(colors)])
        for c1 in range(colors):
            for c2 in range(c1 + 1, colors):
                clauses.append([-_var(point, c1, colors), -_var(point, c2, colors)])

    for start in range(1, n + 1):
        for step in range(1, (n - start) // (length - 1) + 1):
            progression = [start + offset * step for offset in range(length)]
            for color in range(colors):
                clauses.append([-_var(point, color, colors) for point in progression])
    return clauses


def _edge_vars(vertices: int) -> dict[tuple[int, int], int]:
    edge_to_var: dict[tuple[int, int], int] = {}
    next_var = 1
    for i in range(1, vertices + 1):
        for j in range(i + 1, vertices + 1):
            edge_to_var[(i, j)] = next_var
            next_var += 1
    return edge_to_var


def _ramsey_edge_coloring_cnf(spec: dict) -> list[list[int]]:
    vertices = int(spec["vertices"])
    red_clique = int(spec["red_clique"])
    blue_clique = int(spec["blue_clique"])
    edge = _edge_vars(vertices)
    clauses: list[list[int]] = []

    # Variable true means "edge is red". A red clique is forbidden by a negative
    # clause over its edges; a blue clique is forbidden by a positive clause.
    for clique in itertools.combinations(range(1, vertices + 1), red_clique):
        clauses.append([-edge[(i, j)] for i, j in itertools.combinations(clique, 2)])
    for clique in itertools.combinations(range(1, vertices + 1), blue_clique):
        clauses.append([edge[(i, j)] for i, j in itertools.combinations(clique, 2)])
    return clauses


def _hybrid_schur_vdw_cnf(spec: dict) -> list[list[int]]:
    n = int(spec["n"])
    colors = int(spec["colors"])
    clauses: list[list[int]] = []

    for point in range(1, n + 1):
        clauses.append([_var(point, color, colors) for color in range(colors)])
        for c1 in range(colors):
            for c2 in range(c1 + 1, colors):
                clauses.append([-_var(point, c1, colors), -_var(point, c2, colors)])

    for triple in triples(n).all:
        for color in range(colors):
            clauses.append([-_var(point, color, colors) for point in triple])
    return clauses


GENERATORS = {
    "vdw_progression_cnf": _vdw_progression_cnf,
    "ramsey_edge_coloring_cnf": _ramsey_edge_coloring_cnf,
    "hybrid_schur_vdw_cnf": _hybrid_schur_vdw_cnf,
}


def generate(spec: dict) -> list[list[int]]:
    kind = spec.get("kind")
    if kind not in GENERATORS:
        raise ValueError(f"unknown encoder kind {kind!r}")
    return GENERATORS[kind](spec)


def check_cert_encoder(cert: Path, spec: dict) -> tuple[bool, str]:
    parsed = _parsed_formula(cert)
    generated = generate(spec)
    if parsed == generated:
        return True, f"encoder exact-match ({spec['kind']}: {len(generated)} clauses)"

    first_diff = None
    for idx, (got, want) in enumerate(zip(parsed, generated)):
        if got != want:
            first_diff = f"first diff at clause {idx}: cert={got}, generated={want}"
            break
    if first_diff is None:
        first_diff = f"clause count mismatch: cert={len(parsed)}, generated={len(generated)}"
    return False, f"encoder mismatch ({spec.get('kind')}): {first_diff}"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: encoder_check.py <cert-file> <encoder-kind>", file=sys.stderr)
        print("known encoder kinds: " + ", ".join(sorted(GENERATORS)), file=sys.stderr)
        return 2
    cert = Path(argv[1])
    kind = argv[2]
    presets = {
        "w33": {
            "kind": "vdw_progression_cnf",
            "n": 27,
            "colors": 3,
            "progression_length": 3,
        },
        "r34": {
            "kind": "ramsey_edge_coloring_cnf",
            "vertices": 9,
            "red_clique": 3,
            "blue_clique": 4,
        },
        "hybrid13": {
            "kind": "hybrid_schur_vdw_cnf",
            "n": 13,
            "colors": 3,
        },
    }
    spec = presets.get(kind, {"kind": kind})
    ok, detail = check_cert_encoder(cert, spec)
    print(detail)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
