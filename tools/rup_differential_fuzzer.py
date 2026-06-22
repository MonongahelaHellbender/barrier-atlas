#!/usr/bin/env python3
"""Deterministic differential fuzzer for the R3 independent RUP checker.

It generates small flat LRAT/RUP certificates, checks them with the independent
Python checker, and (when available) with the Lean-proved `lratcheck` binary.
This hardens the R3 claim: Python and lratcheck should agree on generated valid
certificates and on deterministic invalid mutations.

The fuzzer is intentionally small and reproducible. It is a regression guard, not
a SAT-solver benchmark.
"""
from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import rup_check  # noqa: E402


def _find_lratcheck() -> Path | None:
    env = os.environ.get("LRATCHECK_BIN")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            ROOT.parent / "dist" / "lean-verification-journey" / ".lake" / "build" / "bin" / "lratcheck",
            ROOT.parent / "lean-verification-journey" / ".lake" / "build" / "bin" / "lratcheck",
        ]
    )
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _flat_clause(clause: Iterable[int]) -> str:
    return " ".join(str(x) for x in clause) + " 0"


def render_cert(formula: list[list[int]], steps: list[tuple[list[int], list[int]]]) -> str:
    groups = [str(len(formula))]
    groups.extend(_flat_clause(clause) for clause in formula)
    for clause, hints in steps:
        groups.append(_flat_clause(clause))
        groups.append(_flat_clause(hints))
    return " ".join(groups) + "\n"


def generated_valid_case(rng: random.Random, idx: int) -> str:
    """Generate a small contradictory unit formula plus an empty-clause proof."""
    var_count = rng.randint(1, 6)
    pivot = rng.randint(1, var_count)
    sign = rng.choice([-1, 1])
    first = sign * pivot
    second = -first

    formula: list[list[int]] = []
    # Add harmless unit noise before/after the contradictory pair. Noise may be
    # duplicated; the proof hints name only the contradiction pair.
    for _ in range(rng.randint(0, 4)):
        v = rng.randint(1, var_count)
        formula.append([rng.choice([-1, 1]) * v])
    first_idx = len(formula) + 1
    formula.append([first])
    second_idx = len(formula) + 1
    formula.append([second])
    for _ in range(rng.randint(0, 4)):
        v = rng.randint(1, var_count)
        formula.append([rng.choice([-1, 1]) * v])

    if rng.choice([False, True]):
        hints = [first_idx, second_idx]
    else:
        hints = [second_idx, first_idx]
    return render_cert(formula, [([], hints)])


def mutate_valid_cert(text: str, rng: random.Random) -> str:
    formula, steps = rup_check.parse_cert(text)
    int_formula = [[-v if neg else v for v, neg in clause] for clause in formula]
    int_steps = [([(-v if neg else v) for v, neg in clause], [h + 1 for h in hints]) for clause, hints in steps]
    mode = rng.choice(["drop_hint", "bad_hint", "drop_step", "nonempty_no_empty"])
    if mode == "drop_hint" and int_steps and int_steps[0][1]:
        int_steps[0] = (int_steps[0][0], int_steps[0][1][:-1])
    elif mode == "bad_hint" and int_steps:
        int_steps[0] = (int_steps[0][0], [len(int_formula) + 1000])
    elif mode == "drop_step":
        int_steps = []
    else:
        int_steps = [([len(int_formula) + 999], int_steps[0][1] if int_steps else [])]
    return render_cert(int_formula, int_steps)


def _python_accepts(text: str) -> bool:
    formula, steps = rup_check.parse_cert(text)
    return bool(rup_check.check_proof(formula, steps)[0])


def _lratcheck_accepts(binary: Path, text: str) -> bool:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fh:
        fh.write(text)
        tmp = Path(fh.name)
    try:
        proc = subprocess.run([str(binary), str(tmp)], capture_output=True, text=True, timeout=30)
        return proc.returncode == 0 and "VERIFIED" in (proc.stdout + proc.stderr)
    finally:
        tmp.unlink(missing_ok=True)


def run(seed: int, cases: int, require_lratcheck: bool = False) -> dict[str, int | bool | str]:
    rng = random.Random(seed)
    lrat = _find_lratcheck()
    if require_lratcheck and lrat is None:
        raise RuntimeError("lratcheck not found; set LRATCHECK_BIN or build lean-verification-journey")

    valid_checked = 0
    invalid_checked = 0
    differential_checked = 0
    for idx in range(cases):
        valid = generated_valid_case(rng, idx)
        py_valid = _python_accepts(valid)
        if not py_valid:
            raise AssertionError(f"generated valid case {idx} refused by Python checker: {valid}")
        valid_checked += 1
        if lrat is not None:
            lr_valid = _lratcheck_accepts(lrat, valid)
            differential_checked += 1
            if py_valid != lr_valid:
                raise AssertionError(f"valid case {idx} disagreed: python={py_valid}, lratcheck={lr_valid}: {valid}")

        invalid = mutate_valid_cert(valid, rng)
        py_invalid = _python_accepts(invalid)
        if py_invalid:
            raise AssertionError(f"mutated invalid case {idx} accepted by Python checker: {invalid}")
        invalid_checked += 1
        if lrat is not None:
            lr_invalid = _lratcheck_accepts(lrat, invalid)
            differential_checked += 1
            if py_invalid != lr_invalid:
                raise AssertionError(f"invalid case {idx} disagreed: python={py_invalid}, lratcheck={lr_invalid}: {invalid}")

    return {
        "seed": seed,
        "cases": cases,
        "valid_checked": valid_checked,
        "invalid_checked": invalid_checked,
        "differential_checked": differential_checked,
        "lratcheck_available": lrat is not None,
        "lratcheck_path": str(lrat) if lrat is not None else "",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260622)
    parser.add_argument("--cases", type=int, default=64)
    parser.add_argument("--require-lratcheck", action="store_true")
    args = parser.parse_args(argv)

    result = run(args.seed, args.cases, args.require_lratcheck)
    print(
        "PASS  RUP differential fuzzer: "
        f"{result['valid_checked']} valid + {result['invalid_checked']} invalid; "
        f"differential comparisons={result['differential_checked']}; "
        f"lratcheck_available={result['lratcheck_available']}"
    )
    if result["lratcheck_available"]:
        print(f"      lratcheck={result['lratcheck_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
