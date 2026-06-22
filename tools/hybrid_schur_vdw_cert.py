#!/usr/bin/env python3
"""Build a flat RUP certificate for the hybrid Schur/vdW obstruction."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import rup_check
from hybrid_schur_vdw_check import triples


DEFAULT_LOWER_WITNESS = [0, 1, 0, 2, 1, 2, 2, 0, 2, 0, 1, 1]


@dataclass(frozen=True)
class HybridCnf:
    clauses: list[tuple[int, ...]]
    at_least_indices: dict[int, int]
    forbidden_triples: list[tuple[int, int, int]]


@dataclass(frozen=True)
class ProofStep:
    clause: tuple[int, ...]
    hints: tuple[int, ...]


@dataclass(frozen=True)
class HybridCertificate:
    formula: list[tuple[int, ...]]
    steps: list[ProofStep]
    n: int
    colors: int
    forbidden_triples: list[tuple[int, int, int]]

    @property
    def variable_count(self) -> int:
        return self.n * self.colors

    @property
    def proof_step_count(self) -> int:
        return len(self.steps)

    @property
    def clause_count(self) -> int:
        return len(self.formula)


def hybrid_var(point: int, color: int, colors: int) -> int:
    return (point - 1) * colors + color + 1


def hybrid_cnf(n: int, colors: int) -> HybridCnf:
    """Encode exact coloring plus no monochromatic Schur/AP triples."""

    clauses: list[tuple[int, ...]] = []
    at_least_indices: dict[int, int] = {}

    for point in range(1, n + 1):
        at_least_indices[point] = len(clauses)
        clauses.append(tuple(hybrid_var(point, color, colors) for color in range(colors)))
        for left in range(colors):
            for right in range(left + 1, colors):
                clauses.append(
                    (
                        -hybrid_var(point, left, colors),
                        -hybrid_var(point, right, colors),
                    )
                )

    forbidden_triples = triples(n).all
    for triple in forbidden_triples:
        for color in range(colors):
            clauses.append(tuple(-hybrid_var(point, color, colors) for point in triple))

    return HybridCnf(clauses=clauses, at_least_indices=at_least_indices, forbidden_triples=forbidden_triples)


def _conflict_clause_index(formula: Sequence[Sequence[int]], prefix: Sequence[int]) -> int | None:
    true_lits = set(prefix)
    for index, clause in enumerate(formula):
        if clause and all(lit < 0 and -lit in true_lits for lit in clause):
            return index
    return None


def _render_cert(formula: Sequence[Sequence[int]], steps: Sequence[ProofStep]) -> str:
    ints: list[int] = [len(formula)]
    for clause in formula:
        ints.extend(clause)
        ints.append(0)
    for step in steps:
        ints.extend(step.clause)
        ints.append(0)
        ints.extend(step.hints)
        ints.append(0)
    return " ".join(str(value) for value in ints) + "\n"


def build_certificate(n: int = 13, colors: int = 3) -> HybridCertificate:
    """Create a prefix-blocking RUP proof for the hybrid UNSAT claim.

    Each learned clause blocks one partial coloring prefix. Leaf prefixes are
    blocked directly by an already-falsified forbidden triple. Internal prefixes
    are blocked by all child blockers plus the exact-one color clause for the
    next point.
    """

    cnf = hybrid_cnf(n=n, colors=colors)
    formula = list(cnf.clauses)
    steps: list[ProofStep] = []

    def append_step(clause: tuple[int, ...], hints: Iterable[int]) -> int:
        db_index = len(formula) + len(steps)
        steps.append(ProofStep(clause=clause, hints=tuple(hints)))
        return db_index

    def prove_prefix(prefix: tuple[int, ...], next_point: int) -> int:
        conflict_index = _conflict_clause_index(formula, prefix)
        blocker = tuple(-lit for lit in prefix)
        if conflict_index is not None:
            return append_step(blocker, (conflict_index + 1,))

        if next_point > n:
            raise RuntimeError(f"found an unblocked coloring prefix: {prefix!r}")

        child_indices: list[int] = []
        for color in range(colors):
            lit = hybrid_var(next_point, color, colors)
            child_indices.append(prove_prefix(prefix + (lit,), next_point + 1))

        hints = [index + 1 for index in child_indices]
        hints.append(cnf.at_least_indices[next_point] + 1)
        return append_step(blocker, hints)

    root_index = prove_prefix((), 1)
    if root_index != len(formula) + len(steps) - 1:
        raise AssertionError("root proof step was not appended last")
    if steps[-1].clause != ():
        raise AssertionError("certificate does not end in the empty clause")

    parsed_formula, parsed_steps = rup_check.parse_cert(_render_cert(formula, steps))
    ok, reason = rup_check.check_proof(parsed_formula, parsed_steps)
    if not ok:
        raise RuntimeError(f"generated certificate failed rup_check: {reason}")

    return HybridCertificate(
        formula=formula,
        steps=steps,
        n=n,
        colors=colors,
        forbidden_triples=cnf.forbidden_triples,
    )


def write_certificate(cert: HybridCertificate, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_cert(cert.formula, cert.steps), encoding="utf-8")


def summary(cert: HybridCertificate) -> dict[str, object]:
    return {
        "claim": f"no {cert.colors}-coloring of [1..{cert.n}] avoids both Schur triples and 3-term APs",
        "n": cert.n,
        "colors": cert.colors,
        "variables": cert.variable_count,
        "original_clauses": cert.clause_count,
        "proof_steps": cert.proof_step_count,
        "forbidden_triples": len(cert.forbidden_triples),
        "checker": "rup-python",
        "verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=13)
    parser.add_argument("--colors", type=int, default=3)
    parser.add_argument("--write-cert", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cert = build_certificate(n=args.n, colors=args.colors)
    if args.write_cert is not None:
        write_certificate(cert, args.write_cert)

    data = summary(cert)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(f"{data['claim']}: VERIFIED")
        print(
            f"variables={data['variables']} original_clauses={data['original_clauses']} "
            f"proof_steps={data['proof_steps']} forbidden_triples={data['forbidden_triples']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
