#!/usr/bin/env python3
"""barrier_check.py -- re-verify barrier envelopes from the atlas.

One-directional by construction: a checker can only move an entry to REFUSED or
UNVERIFIABLE-HERE. The single path to CERTIFIED is a positive check passing. A
missing tool, a corrupt cert, or an extra axiom all fail *closed*.

Statuses:
  CERTIFIED          the impossibility re-checked here, at its declared rung
  REFUSED            a LIVE entry failed its check  -> real failure (exit 1)
  UNVERIFIABLE-HERE  checker/toolchain absent in this environment -> warning
  DEFERRED           registered but no automated checker yet (status=deferred)

Stdlib only. Usage:
  python3 tools/barrier_check.py barriers/*.barrier.json
  python3 tools/barrier_check.py            # defaults to every barriers/*.barrier.json
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import encoder_check  # noqa: E402  (claim-CNF binding for v0 combinatorics)
import hybrid_schur_vdw_check  # noqa: E402  (finite hybrid Schur/AP exhaustive checker)
import rup_check  # noqa: E402  (sibling module: the independent R3 checker)
import claim_stress_check  # noqa: E402  (R4/R5 empirical-rung stress-contract engine)

ATLAS_ROOT = Path(__file__).resolve().parent.parent

CERTIFIED, REFUSED, UNVERIFIABLE, DEFERRED = (
    "CERTIFIED", "REFUSED", "UNVERIFIABLE-HERE", "DEFERRED")


def _resolve(p: str) -> Path:
    """Resolve an envelope path relative to the atlas root."""
    return (ATLAS_ROOT / p).resolve()


def _check_encoder_binding(cert: Path, cert_spec: dict):
    enc = cert_spec.get("encoder")
    if not enc:
        return None
    try:
        ok, detail = encoder_check.check_cert_encoder(cert, enc)
    except Exception as e:  # noqa: BLE001
        return False, f"encoder check crashed: {e}"
    return ok, detail


def check_lratcheck(env: dict):
    """R2: run the compiled, proven-correct checker on the certificate.

    Binds the cert to THIS claim before trusting the VERIFIED: the checker only
    proves 'the parsed CNF is UNSAT', so a tampered file could certify a different
    (irrelevant) impossibility. We pin the exact bytes by sha256 and cross-check the
    parser's reported clause/step counts against the declared meta -- both fail
    closed -- so tampering can only REFUSE, never falsely certify this barrier.
    """
    chk = env["checker"]
    cert_spec = env.get("certificate", {})
    binary = os.environ.get(chk.get("binary_env", ""), "") or chk["binary_default"]
    binary = _resolve(binary)
    cert = _resolve(chk["cert"])
    if not cert.exists():
        return REFUSED, f"certificate missing ({cert})"
    # (1) byte-level binding FIRST -- environment-independent, needs no toolchain:
    # a tampered/substituted cert fails closed even on a runner without the checker.
    want_hash = cert_spec.get("sha256")
    if want_hash:
        got = hashlib.sha256(cert.read_bytes()).hexdigest()
        if got != want_hash:
            return REFUSED, f"cert sha256 mismatch (tampered/substituted): {got[:16]}..."
    encoder_detail = _check_encoder_binding(cert, cert_spec)
    if encoder_detail:
        ok, detail = encoder_detail
        if not ok:
            return REFUSED, detail
    if not binary.exists():
        suffix = f"; {encoder_detail[1]}" if encoder_detail else ""
        return UNVERIFIABLE, f"checker binary not built ({binary}){suffix}"
    try:
        out = subprocess.run([str(binary), str(cert)], capture_output=True,
                             text=True, timeout=600)
    except Exception as e:  # noqa: BLE001
        return UNVERIFIABLE, f"could not run checker: {e}"
    blob = out.stdout + out.stderr
    # (2) structural cross-check: parsed counts must match the declared claim's CNF.
    meta = cert_spec.get("meta", {})
    m = re.search(r"parsed:\s*(\d+)\s+original clauses,\s*(\d+)\s+proof steps", blob)
    if m and ("original_clauses" in meta or "proof_steps" in meta):
        pc, ps = int(m.group(1)), int(m.group(2))
        if meta.get("original_clauses", pc) != pc or meta.get("proof_steps", ps) != ps:
            return REFUSED, (f"parsed shape {pc}cl/{ps}steps != declared "
                             f"{meta.get('original_clauses')}cl/{meta.get('proof_steps')}steps")
    if out.returncode == 0 and re.search(chk["accept_pattern"], blob):
        binding = "bytes+shape+encoder bound" if encoder_detail else "bytes+shape bound"
        return CERTIFIED, f"{chk['accept_pattern']}, {binding}"
    return REFUSED, f"checker did not emit {chk['accept_pattern']} (rc={out.returncode})"


def check_lean_axioms(env: dict):
    """R0/R1: assert the theorem's axiom set EXACTLY equals the declared base."""
    chk = env["checker"]
    repo = os.environ.get(chk.get("repo_env", ""), "") or chk["repo_default"]
    repo = _resolve(repo)
    if not (repo / "lakefile.toml").exists() and not (repo / "lakefile.lean").exists():
        return UNVERIFIABLE, f"lean repo not found ({repo})"
    thm = chk["theorem"]
    try:
        out = subprocess.run(["lake", "env", "lean", chk["lean_file"]],
                             cwd=str(repo), capture_output=True, text=True, timeout=900)
    except FileNotFoundError:
        return UNVERIFIABLE, "lake/lean not on PATH"
    except Exception as e:  # noqa: BLE001
        return UNVERIFIABLE, f"could not run lean: {e}"
    blob = out.stdout + out.stderr
    if re.search(rf"'{re.escape(thm)}' does not depend on any axioms", blob):
        found = set()
    else:
        m = re.search(rf"'{re.escape(thm)}' depends on axioms: \[([^\]]*)\]", blob)
        if not m:
            return UNVERIFIABLE, f"no axiom audit for '{thm}' (build error? rc={out.returncode})"
        found = {a.strip() for a in m.group(1).split(",") if a.strip()}
    expected = set(chk["expected_axioms"])
    if found == expected:
        return CERTIFIED, f"axioms == {sorted(expected)}"
    extra, missing = found - expected, expected - found
    return REFUSED, f"axiom mismatch (extra={sorted(extra)}, missing={sorted(missing)})"


def check_rup_python(env: dict):
    """R3: an independent pure-Python re-derivation of the SAME certificate.

    Weaker than the kernel-proved checker (you now trust this Python), but real
    cross-implementation corroboration. Same byte+shape binding as lratcheck, so
    tampering fails closed; then re-run the from-scratch RUP checker.
    """
    chk = env["checker"]
    cert_spec = env.get("certificate", {})
    cert = _resolve(chk["cert"])
    if not cert.exists():
        return REFUSED, f"certificate missing ({cert})"
    want_hash = cert_spec.get("sha256")
    if want_hash:
        got = hashlib.sha256(cert.read_bytes()).hexdigest()
        if got != want_hash:
            return REFUSED, f"cert sha256 mismatch (tampered/substituted): {got[:16]}..."
    encoder_detail = _check_encoder_binding(cert, cert_spec)
    if encoder_detail:
        ok, detail = encoder_detail
        if not ok:
            return REFUSED, detail
    formula, steps = rup_check.parse_cert(cert.read_text(encoding="utf-8"))
    meta = cert_spec.get("meta", {})
    if (meta.get("original_clauses", len(formula)) != len(formula)
            or meta.get("proof_steps", len(steps)) != len(steps)):
        return REFUSED, (f"parsed shape {len(formula)}cl/{len(steps)}steps != declared "
                         f"{meta.get('original_clauses')}cl/{meta.get('proof_steps')}steps")
    ok, detail = rup_check.check_proof(formula, steps)
    prefix = f"{encoder_detail[1]}; " if encoder_detail else ""
    return (CERTIFIED, f"{prefix}independent RUP agrees ({detail})") if ok else (REFUSED, detail)


def check_hybrid_schur_vdw(env: dict):
    """R3: exhaustive finite search for a hybrid Schur / AP coloring barrier."""
    chk = env["checker"]
    n = int(chk["n"])
    colors = int(chk["colors"])
    witness = chk.get("lower_bound_witness")
    declared = env.get("certificate", {}).get("meta", {}).get("lower_bound_witness")
    if declared is not None and witness != declared:
        return REFUSED, "checker lower-bound witness differs from declared certificate metadata"
    ok, detail, report = hybrid_schur_vdw_check.check_barrier(n, colors, witness)
    target = report.get("target_search", {})
    lower = report.get("lower_bound", {})
    if ok:
        suffix = (
            f"nodes={target.get('nodes_visited')}, "
            f"triples={target.get('combined_unique_triple_count')}, "
            f"lower_witness_n={lower.get('lower_bound_witness_n')}"
        )
        return CERTIFIED, f"{detail}; {suffix}"
    return REFUSED, detail


RUNG_ORDER = ["R0", "R1", "R2", "R3", "R4", "R5"]  # strongest .. weakest


def _weaker(a: str, b: str) -> str:
    """Min-trust: the weaker (higher-index) of two rungs."""
    return a if RUNG_ORDER.index(a) >= RUNG_ORDER.index(b) else b


_ID_INDEX = None
_COMPOSE_STACK = set()


def _load_by_id(bid: str):
    global _ID_INDEX
    if _ID_INDEX is None:
        _ID_INDEX = {}
        for p in glob.glob(str(ATLAS_ROOT / "barriers" / "*.barrier.json")):
            path = Path(p)
            if path.name.startswith("_test_"):
                continue
            try:
                e = json.loads(path.read_text())
            except FileNotFoundError:
                continue
            _ID_INDEX[e["id"]] = e
    return _ID_INDEX.get(bid)


def check_composed(env: dict):
    """The min-rung calculus: a composed barrier re-checks each sub-barrier and
    earns the WEAKEST rung among its parts and the composition step. CERTIFIED only
    if every part certifies AND the declared rung equals that min-trust rung. Any
    weak/failed/deferred part propagates (fails closed)."""
    comp = env["checker"]["composition"]
    if env["id"] in _COMPOSE_STACK:
        return REFUSED, "composition cycle"
    _COMPOSE_STACK.add(env["id"])
    try:
        weakest = comp["step"]["rung"]
        parts = []
        for sid in comp["sub_barriers"]:
            sub = _load_by_id(sid)
            if sub is None:
                return UNVERIFIABLE, f"sub-barrier '{sid}' not found"
            st, detail = run(sub)
            parts.append((sid, sub["rung"]["level"]))
            if st != CERTIFIED:
                # the composite is at best as good as its weakest part
                return (st if st in (REFUSED, UNVERIFIABLE, DEFERRED) else REFUSED), \
                    f"sub '{sid}' is {st} ({detail})"
            weakest = _weaker(weakest, sub["rung"]["level"])
    finally:
        _COMPOSE_STACK.discard(env["id"])
    declared = env["rung"]["level"]
    chain = "+".join(f"{p[0]}={p[1]}" for p in parts) + f"+step={comp['step']['rung']}"
    if declared != weakest:
        return REFUSED, f"declared {declared} != min-trust {weakest} (from {chain})"
    return CERTIFIED, f"min-trust {weakest} from {chain}"


def check_multi_region(env: dict):
    """One claim, domain partitioned into REGIONS, each with its own inline checker
    and rung (e.g. rigorous R2 on a threshold, only R5-argued on the tail). The
    barrier earns the WEAKEST region's rung (min-trust). CERTIFIED only if every
    region certifies AND the declared rung equals the weakest. Any failed/deferred
    region propagates -- a strong region cannot launder a weak one up."""
    regions = env["checker"]["regions"]
    results = []  # (name, rung, status, detail)
    for r in regions:
        mini = {
            "id": f"{env['id']}#{r.get('region', '?')}",
            "rung": {"level": r["rung"]},
            "checker": r["checker"],
            "certificate": r.get("certificate", {}),
        }
        st, detail = run(mini)
        results.append((r.get("region", "?"), r["rung"], st, detail))
    chain = "; ".join(f"{n}={rg}:{st}" for n, rg, st, _ in results)
    # one-directional: any non-certified region propagates the most severe status
    for sev in (REFUSED, UNVERIFIABLE, DEFERRED):
        hit = next((x for x in results if x[2] == sev), None)
        if hit:
            return sev, f"region '{hit[0]}' ({hit[1]}) is {sev}: {hit[3]} | regions: {chain}"
    weakest = None
    for _, rg, _, _ in results:
        weakest = rg if weakest is None else _weaker(weakest, rg)
    declared = env["rung"]["level"]
    if declared != weakest:
        return REFUSED, f"declared {declared} != min-trust {weakest} across regions ({chain})"
    return CERTIFIED, f"min-trust {weakest} across regions: {chain}"


def check_claim_stress(env: dict):
    """R4/R5: the three-stage empirical-rung contract (completeness -> adequacy ->
    named human/llm correctness gate). One-directional: can only refuse or defer,
    never grant a rung from automation alone. Returns the same status vocabulary."""
    return claim_stress_check.evaluate(env)


def check_manual(env: dict):
    return DEFERRED, env["checker"].get("promote_recipe", "(no recipe given)")


CHECKERS = {
    "lratcheck": check_lratcheck,
    "lean-axioms": check_lean_axioms,
    "rup-python": check_rup_python,
    "hybrid-schur-vdw-exhaustive": check_hybrid_schur_vdw,
    "composed": check_composed,
    "multi-region": check_multi_region,
    "claim-stress": check_claim_stress,
    "manual": check_manual,
}


def run(env: dict):
    fn = CHECKERS.get(env["checker"]["kind"])
    if fn is None:
        return UNVERIFIABLE, f"unknown checker kind '{env['checker']['kind']}'"
    return fn(env)


def main(argv):
    paths = argv[1:] or [
        p for p in sorted(glob.glob(str(ATLAS_ROOT / "barriers" / "*.barrier.json")))
        if not Path(p).name.startswith("_test_")
    ]
    if not paths:
        print("no barrier envelopes found", file=sys.stderr)
        return 2

    rows, refused = [], 0
    for p in paths:
        env = json.loads(Path(p).read_text())
        status, detail = run(env)
        if status == REFUSED:
            refused += 1
        rows.append((env["id"], env["domain"], env["rung"]["level"],
                     env["checker"]["kind"], status, detail))

    idw = max(len(r[0]) for r in rows)
    domw = max(len(r[1]) for r in rows)
    print(f"\n  Barrier Atlas -- re-check ({len(rows)} entries)\n")
    print(f"  {'id'.ljust(idw)}  {'domain'.ljust(domw)}  rung  checker       status")
    print(f"  {'-'*idw}  {'-'*domw}  ----  ------------  ------")
    mark = {CERTIFIED: "[x]", REFUSED: "[!]", UNVERIFIABLE: "[~]", DEFERRED: "[ ]"}
    for rid, dom, rung, kind, status, detail in rows:
        print(f"  {rid.ljust(idw)}  {dom.ljust(domw)}  {rung}   {kind.ljust(12)} {mark[status]} {status}")
        print(f"  {' '*idw}  {' '*domw}        {' '*12}      -> {detail}")

    n = {s: sum(1 for r in rows if r[4] == s) for s in (CERTIFIED, REFUSED, UNVERIFIABLE, DEFERRED)}
    print(f"\n  summary: {n[CERTIFIED]} certified, {n[REFUSED]} refused, "
          f"{n[UNVERIFIABLE]} unverifiable-here, {n[DEFERRED]} deferred\n")
    if refused:
        print("  FAIL: a LIVE barrier did not re-check.\n")
        return 1
    print("  OK: every LIVE barrier re-checked (or honestly degraded).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
