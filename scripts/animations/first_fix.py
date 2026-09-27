#!/usr/bin/env python3
"""Reproduce the corrupted-first-fix analysis (report section 5).

Reads the CSVs written by export_anim.py and prints:
  1. frame check: accepted GPS fixes and RTK truth against the estimate,
     with no alignment applied;
  2. for every gap in the GPS stream, the receiver's first fixes after it
     against RTK truth, and what the filter did;
  3. the proposed 20 m/s pre-gate applied to the fixes that triggered lockouts;
  4. dead-reckoning drift over the blind stretch before the last gap ends.

    python3 first_fix.py --data anim_export
"""
import argparse
import math
import statistics as st

from animdata import load_run, interp

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--data", default="anim_export")
ap.add_argument("--runs", nargs="+", default=["out3_OFF", "out3_ON"])
ap.add_argument("--limit", type=float, default=20.0, help="pre-gate threshold, m/s")
a = ap.parse_args()


def truth(rtk, t, tol=2.0):
    r = min(rtk, key=lambda q: abs(q[0] - t))
    return (r[1], r[2]) if abs(r[0] - t) <= tol else None


for n in a.runs:
    d = load_run(a.data, n)
    od, fx, rtk = d["odom"], d["fixes"], d["rtk"]
    print(f"\n===== {n}  (t0 {d['t0']:.3f})")

    # 1. frame check over normal operation
    for label, pts in (("accepted GPS - estimate", [(f["t"], f["x"], f["y"]) for f in fx if f["accepted"]]),
                       ("RTK truth - estimate", rtk)):
        r = [(x - e[0], y - e[1]) for t, x, y in pts if 400 <= t <= 2900 and (e := interp(od, t))]
        mags = sorted(math.hypot(u, v) for u, v in r)
        print(f"  {label:24s} median offset ({st.median(u for u, _ in r):+.2f}, {st.median(v for _, v in r):+.2f}) m, "
              f"|offset| median {mags[len(mags) // 2]:.2f} m, 90th {mags[int(.9 * len(mags))]:.2f} m")

    # 2. first fixes after each gap
    ts = [f["t"] for f in fx]
    for g0, g1 in [(ts[i - 1], ts[i]) for i in range(1, len(ts)) if ts[i] - ts[i - 1] > 10]:
        i = ts.index(g1); f = fx[i]
        eb, ea = interp(od, f["t"] - 0.05), interp(od, f["t"] + 0.15)
        g = truth(rtk, f["t"])
        line = (f"  gap t+{g0:6.0f}-{g1:6.0f} ({g1 - g0:3.0f} s): first fix {f['reason']:11s} "
                f"d2 {f['d2']:7.2f} sigma {f['sigma']:6.1f}")
        if g:
            line += (f" | fix error {math.hypot(f['x'] - g[0], f['y'] - g[1]):6.1f} m | estimate error "
                     f"{math.hypot(eb[0] - g[0], eb[1] - g[1]):6.1f} -> {math.hypot(ea[0] - g[0], ea[1] - g[1]):6.1f} m")
        print(line)
        errs = [round(math.hypot(q["x"] - gg[0], q["y"] - gg[1])) for q in fx[i:i + 25] if (gg := truth(rtk, q["t"]))]
        print(f"      next fixes, error vs truth (m): {errs}")

    # 3. the pre-gate against the fixes that were accepted after a gap
    for g0, g1 in [(ts[i - 1], ts[i]) for i in range(1, len(ts)) if ts[i] - ts[i - 1] > 60]:
        f = fx[ts.index(g1)]
        prev = max((q for q in fx if q["accepted"] and q["t"] < g0 + 0.01), key=lambda q: q["t"], default=None)
        if prev:
            dist, dt = math.hypot(f["x"] - prev["x"], f["y"] - prev["y"]), f["t"] - prev["t"]
            print(f"  pre-gate: fix t+{f['t']:.2f} vs last accepted t+{prev['t']:.2f}: {dist:.0f} m in {dt:.1f} s "
                  f"= {dist / dt:.2f} m/s -> {'REJECTED' if dist / dt > a.limit else 'passes'} a {a.limit:.0f} m/s gate")

    # 4. dead-reckoning drift across the blind stretch before the long gap at ~t+3900
    ta = max((r for r in rtk if r[0] < 3713), key=lambda r: r[0])
    tb = min((r for r in rtk if r[0] > 3900), key=lambda r: r[0])
    ea_, eb_ = interp(od, ta[0]), interp(od, tb[0])
    dxt, dyt = tb[1] - ta[1], tb[2] - ta[2]; dxe, dye = eb_[0] - ea_[0], eb_[1] - ea_[1]
    ang = (math.degrees(math.atan2(dye, dxe) - math.atan2(dyt, dxt)) + 180) % 360 - 180
    print(f"  drift t+{ta[0]:.0f}..{tb[0]:.0f}: {math.hypot(dxe - dxt, dye - dyt):.1f} m, heading of net motion off "
          f"{ang:+.1f} deg | error vs truth {math.hypot(ea_[0] - ta[1], ea_[1] - ta[2]):.0f} -> "
          f"{math.hypot(eb_[0] - tb[1], eb_[1] - tb[2]):.0f} m")
