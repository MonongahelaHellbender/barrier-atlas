#!/usr/bin/env python3
"""Finite decision-core model for Barrier Atlas Phase F.

This module is a spec/test artifact, not runner runtime. It mirrors the runner's
CERTIFIED gate over extracted Boolean facts so the Lean proof and Python bridge
can compare an exhaustive finite table without importing the production runners.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterator


class Kind(str, Enum):
    ATOMIC = "atomic"
    EXTERNAL = "external"
    COMPOSED = "composed"
    MULTI_REGION = "multi-region"
    QUORUM = "quorum"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class Verdict(str, Enum):
    CERTIFIED = "CERTIFIED"
    REFUSED = "REFUSED"
    DEFERRED = "DEFERRED"
    UNVERIFIABLE = "UNVERIFIABLE-HERE"


FIELD_NAMES = [
    "path_ok",
    "artifact_present",
    "artifact_hash_ok",
    "manifest_ok",
    "manifest_hash_ok",
    "timeout_ok",
    "sandbox_ok",
    "rung_within_ceiling",
    "plugin_output_legal",
    "plugin_rung_le_ceiling",
    "plugin_rung_le_declared",
    "checker_positive",
    "all_parts_certified",
    "declared_eq_weakest",
    "quorum_count_ge_required",
    "quorum_distinct_count_ge_required",
]

KINDS = [kind.value for kind in Kind]
FACT_SPACE_SIZE = 1 << len(FIELD_NAMES)


@dataclass(frozen=True)
class Facts:
    kind: Kind
    path_ok: bool
    artifact_present: bool
    artifact_hash_ok: bool
    manifest_ok: bool
    manifest_hash_ok: bool
    timeout_ok: bool
    sandbox_ok: bool
    rung_within_ceiling: bool
    plugin_output_legal: bool
    plugin_rung_le_ceiling: bool
    plugin_rung_le_declared: bool
    checker_positive: bool
    all_parts_certified: bool
    declared_eq_weakest: bool
    quorum_count_ge_required: bool
    quorum_distinct_count_ge_required: bool


def facts_from_code(kind: str | Kind, code: int) -> Facts:
    values = {name: bool((code >> i) & 1) for i, name in enumerate(FIELD_NAMES)}
    return Facts(kind=Kind(kind), **values)


def code_from_facts(**overrides: bool | str | Kind) -> tuple[Kind, int]:
    kind = Kind(overrides.pop("kind", Kind.ATOMIC))
    code = 0
    for i, name in enumerate(FIELD_NAMES):
        if bool(overrides.get(name, False)):
            code |= 1 << i
    return kind, code


def common_ok(f: Facts) -> bool:
    return f.path_ok and f.artifact_present and f.artifact_hash_ok


def certified_preconditions(f: Facts) -> bool:
    if f.kind == Kind.ATOMIC:
        return common_ok(f) and f.rung_within_ceiling and f.checker_positive
    if f.kind == Kind.EXTERNAL:
        return (
            common_ok(f)
            and f.manifest_ok
            and f.manifest_hash_ok
            and f.rung_within_ceiling
            and f.timeout_ok
            and f.sandbox_ok
            and f.plugin_output_legal
            and f.plugin_rung_le_ceiling
            and f.plugin_rung_le_declared
            and f.checker_positive
        )
    if f.kind in (Kind.COMPOSED, Kind.MULTI_REGION):
        return common_ok(f) and f.checker_positive and f.all_parts_certified and f.declared_eq_weakest
    if f.kind == Kind.QUORUM:
        return (
            common_ok(f)
            and f.checker_positive
            and f.quorum_count_ge_required
            and f.quorum_distinct_count_ge_required
        )
    return False


def _common_refusal(f: Facts) -> tuple[Verdict, str] | None:
    if not f.path_ok:
        return Verdict.REFUSED, "PATH_REJECTED"
    if not f.artifact_present:
        return Verdict.REFUSED, "ARTIFACT_MISSING"
    if not f.artifact_hash_ok:
        return Verdict.REFUSED, "ARTIFACT_HASH_MISMATCH"
    return None


def decide(f: Facts) -> tuple[Verdict, str]:
    common = _common_refusal(f)
    if common is not None:
        return common

    if f.kind == Kind.MANUAL:
        return Verdict.DEFERRED, "DEFERRED_PENDING_HUMAN"
    if f.kind == Kind.UNKNOWN:
        return Verdict.UNVERIFIABLE, "UNKNOWN_CHECKER"

    if f.kind == Kind.ATOMIC:
        if not f.rung_within_ceiling:
            return Verdict.REFUSED, "RUNG_CEILING_EXCEEDED"
        if f.checker_positive:
            return Verdict.CERTIFIED, "OK"
        return Verdict.REFUSED, "CHECKER_ERROR"

    if f.kind == Kind.EXTERNAL:
        if not f.manifest_ok:
            return Verdict.REFUSED, "MANIFEST_INVALID"
        if not f.manifest_hash_ok:
            return Verdict.REFUSED, "CHECKER_HASH_MISMATCH"
        if not f.rung_within_ceiling:
            return Verdict.REFUSED, "RUNG_CEILING_EXCEEDED"
        if not f.timeout_ok:
            return Verdict.UNVERIFIABLE, "CHECKER_TIMEOUT"
        if not f.sandbox_ok:
            return Verdict.UNVERIFIABLE, "SANDBOX_UNAVAILABLE"
        if not f.plugin_output_legal:
            return Verdict.UNVERIFIABLE, "CHECKER_ERROR"
        if not f.plugin_rung_le_ceiling:
            return Verdict.REFUSED, "RUNG_CEILING_EXCEEDED"
        if not f.plugin_rung_le_declared:
            return Verdict.REFUSED, "RUNG_LAUNDERING"
        if f.checker_positive:
            return Verdict.CERTIFIED, "OK"
        return Verdict.REFUSED, "CHECKER_ERROR"

    if f.kind in (Kind.COMPOSED, Kind.MULTI_REGION):
        if not f.all_parts_certified:
            return Verdict.DEFERRED, "WEAK_SUBBARRIER"
        if not f.declared_eq_weakest:
            return Verdict.REFUSED, "RUNG_LAUNDERING"
        if f.checker_positive:
            return Verdict.CERTIFIED, "OK"
        return Verdict.REFUSED, "CHECKER_ERROR"

    if f.kind == Kind.QUORUM:
        if not f.quorum_count_ge_required:
            return Verdict.REFUSED, "QUORUM_NOT_MET"
        if not f.quorum_distinct_count_ge_required:
            return Verdict.REFUSED, "QUORUM_NOT_INDEPENDENT"
        if f.checker_positive:
            return Verdict.CERTIFIED, "OK"
        return Verdict.REFUSED, "QUORUM_NOT_MET"

    raise AssertionError(f.kind)


def iter_rows() -> Iterator[list[str | int]]:
    for kind in KINDS:
        for code in range(FACT_SPACE_SIZE):
            verdict, reason = decide(facts_from_code(kind, code))
            yield [kind, code, verdict.value, reason]

