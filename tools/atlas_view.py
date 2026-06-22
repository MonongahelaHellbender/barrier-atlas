#!/usr/bin/env python3
"""atlas_view.py -- render the Barrier Atlas as a visual negative-space map.

A single self-contained HTML page (inline CSS, no dependencies, phone-friendly):
the certified map of *what cannot be*, laid out as a trust gradient -- strongest
rungs (R0) bright at the top, weakest (R5) dim at the bottom -- with every barrier
LIVE re-checked and colour-coded by its real status.

Usage:
  python3 tools/atlas_view.py [out.html]        # live re-check (default)
  python3 tools/atlas_view.py --declared out.html   # fast: declared rung/status only
Also exposes render_html() for embedding (e.g. a Foundation dashboard route).
"""
import glob
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ATLAS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ATLAS_ROOT / "tools"))

RUNGS = ["R0", "R1", "R2", "R3", "R4", "R5"]
RUNG_LABEL = {
    "R0": "kernel-checked", "R1": "compiler-assisted", "R2": "verified-checker program",
    "R3": "independent recomputation", "R4": "empirical (named human gate)", "R5": "argued / conjectural",
}
STATUS_COLOR = {
    "CERTIFIED": "#3ddc84", "DEFERRED": "#f4c14b",
    "REFUSED": "#ff5c5c", "UNVERIFIABLE-HERE": "#8a93a6",
}


def _barriers():
    out = []
    for p in sorted(glob.glob(str(ATLAS_ROOT / "barriers" / "*.barrier.json"))):
        if Path(p).name.startswith("_test_"):
            continue
        out.append(json.loads(Path(p).read_text()))
    return out


def _statuses(barriers, live):
    if not live:
        return {b["id"]: (b.get("status", "live").upper(), "declared (no live re-check)") for b in barriers}
    import barrier_check
    res = {}
    for b in barriers:
        try:
            st, detail = barrier_check.run(b)
        except Exception as e:  # noqa: BLE001
            st, detail = "UNVERIFIABLE-HERE", f"checker error: {e}"
        res[b["id"]] = (st, detail)
    return res


def _card(b, status, detail):
    color = STATUS_COLOR.get(status, "#8a93a6")
    claim = html.escape(b["claim"]["statement"])
    signed = ""
    hr = b.get("checker", {}).get("human_review", {})
    if hr.get("verdict") == "adequate" and hr.get("by"):
        signed = f'<span class="sig">signed · {html.escape(hr["by"])}</span>'
    tb = "".join(f"<li>{html.escape(t)}</li>" for t in b.get("rung", {}).get("trusted_base", []))
    return f"""
    <details class="card" style="--c:{color}">
      <summary>
        <span class="dot"></span>
        <span class="cid">{html.escape(b['id'])}</span>
        <span class="badge" style="background:{color}">{html.escape(status)}</span>
        <span class="kind">{html.escape(b.get('checker', {}).get('kind', '?'))}</span>{signed}
      </summary>
      <p class="claim">{claim}</p>
      <p class="detail">{html.escape(detail)}</p>
      <div class="tb"><span>trusted base</span><ul>{tb}</ul></div>
    </details>"""


def render_html(live=True):
    barriers = _barriers()
    st = _statuses(barriers, live)
    counts = {}
    for s, _ in st.values():
        counts[s] = counts.get(s, 0) + 1
    by_rung = {r: [] for r in RUNGS}
    for b in barriers:
        by_rung.setdefault(b["rung"]["level"], []).append(b)
    bands = ""
    for i, r in enumerate(RUNGS):
        items = by_rung.get(r, [])
        if not items:
            continue
        bright = 1.0 - i * 0.11  # trust gradient: stronger rung -> brighter band
        cards = "".join(_card(b, *st[b["id"]]) for b in items)
        bands += f"""
      <section class="band" style="opacity:{bright:.2f}">
        <div class="rung"><span class="rl">{r}</span><span class="rd">{RUNG_LABEL.get(r,'')}</span>
          <span class="rn">{len(items)}</span></div>
        <div class="cards">{cards}</div>
      </section>"""
    summary = "  ".join(
        f'<span style="color:{STATUS_COLOR.get(s,"#ccc")}">&#9679; {n} {s.lower()}</span>'
        for s, n in sorted(counts.items()))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode = "live re-check" if live else "declared"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Barrier Atlas — the negative space</title>
<style>
  :root{{color-scheme:dark}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:#0b0e14;color:#e6e9ef;
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}}
  header{{padding:22px 18px 10px;text-align:center;border-bottom:1px solid #1c2130}}
  h1{{margin:0;font-size:20px;letter-spacing:.5px}}
  .sub{{color:#8a93a6;font-size:13px;margin-top:4px}}
  .summary{{margin:10px 0 2px;font-size:13.5px}}
  main{{max-width:880px;margin:0 auto;padding:8px 12px 60px}}
  .band{{margin:14px 0;padding:10px;border:1px solid #1c2130;border-radius:12px;
    background:linear-gradient(180deg,#11151f,#0d111a)}}
  .rung{{display:flex;align-items:center;gap:10px;margin:2px 4px 10px}}
  .rl{{font-weight:700;font-size:15px;background:#1c2130;padding:2px 9px;border-radius:7px}}
  .rd{{color:#9aa3b2;font-size:13px;flex:1}}
  .rn{{color:#6b7280;font-size:12px}}
  .cards{{display:flex;flex-direction:column;gap:8px}}
  .card{{border:1px solid #222838;border-left:3px solid var(--c);border-radius:9px;
    background:#0f1320;padding:0}}
  summary{{list-style:none;cursor:pointer;padding:10px 12px;display:flex;
    align-items:center;gap:8px;flex-wrap:wrap}}
  summary::-webkit-details-marker{{display:none}}
  .dot{{width:9px;height:9px;border-radius:50%;background:var(--c);flex:none}}
  .cid{{font-weight:600;font-family:ui-monospace,Menlo,monospace;font-size:13px}}
  .badge{{font-size:11px;font-weight:700;color:#0b0e14;padding:1px 7px;border-radius:20px}}
  .kind{{color:#8a93a6;font-size:12px;font-family:ui-monospace,Menlo,monospace}}
  .sig{{color:#3ddc84;font-size:11px;border:1px solid #245c3e;padding:1px 7px;border-radius:20px}}
  .claim{{margin:0 12px 6px;color:#c9cfdb;font-size:13.5px}}
  .detail{{margin:0 12px 8px;color:#7f8aa0;font-size:12px;font-family:ui-monospace,Menlo,monospace}}
  .tb{{margin:0 12px 12px}}
  .tb>span{{color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:.5px}}
  .tb ul{{margin:4px 0 0;padding-left:18px;color:#9aa3b2;font-size:12.5px}}
  footer{{text-align:center;color:#5b6473;font-size:12px;padding:18px}}
</style></head><body>
<header>
  <h1>Barrier Atlas — the negative space</h1>
  <div class="sub">a certified map of what <em>cannot</em> be · strongest rungs on top</div>
  <div class="summary">{summary}</div>
</header>
<main>{bands}</main>
<footer>{len(barriers)} barriers · {mode} · {now} · re-checkable: <code>python3 tools/barrier_check.py</code></footer>
</body></html>"""


def main(argv):
    live = "--declared" not in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    out = Path(args[0]) if args else ATLAS_ROOT / "atlas.html"
    out.write_text(render_html(live=live), encoding="utf-8")
    print(f"wrote {out}  ({'live' if live else 'declared'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
