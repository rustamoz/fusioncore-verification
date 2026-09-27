#!/usr/bin/env python3
"""Position sigma before and during coast, and the gate's decisions after.

Supports report section 3: after a 200 s injected blackout, sigma grows
from 1.4 m to 78.4 m and the first 46 returning fixes are rejected.
Uses the 1 Hz health topic for sigma, since per-fix status only sees
sigma when a fix arrives.

    python3 coast_sigma.py BAG --before 100
"""
import argparse

from fusioncore_ros.msg import GnssStatus, FilterHealth
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bag")
p.add_argument("--before", type=float, default=100.0,
               help="seconds from start treated as 'before the outage'")
a = p.parse_args()

H = list(read_topic(a.bag, "/fusion/debug/filter_health", FilterHealth))
G = list(read_topic(a.bag, "/fusion/debug/gnss_status", GnssStatus))
t0 = min(H[0][0], G[0][0])
print(f"=== {a.bag} ===")
pre = sorted(m.position_sigma_x for t, m in H if not m.gnss_in_coast and t - t0 < a.before)
if pre:
    print(f"health: sigma before outage  median {pre[len(pre) // 2]:.2f} m, max {pre[-1]:.2f} m")
coast = [(t - t0, m.position_sigma_x) for t, m in H if m.gnss_in_coast]
if coast:
    pk = max(coast, key=lambda c: c[1])
    print(f"health: peak sigma in coast  {pk[1]:.2f} m at t+{pk[0]:.1f}s "
          f"(coast t+{coast[0][0]:.0f} to t+{coast[-1][0]:.0f}s)")
rej = [(t - t0, m) for t, m in G if m.rejection_reason == "CHI2_FAILED"]
print(f"status: {len(G)} fixes, {len(rej)} CHI2_FAILED")
if rej:
    d = [m.mahalanobis_sq for _, m in rej]
    print(f"status: d2 of rejections {min(d):.2f} to {max(d):.2f}")
    print(f"status: max sigma at a rejected fix {max(m.position_sigma_x for _, m in rej):.2f} m")
    acc = [(t - t0, m) for t, m in G if t - t0 > rej[-1][0] and m.accepted]
    if acc:
        t_a, m_a = acc[0]
        print(f"status: first accept t+{t_a:.1f}s  d2 {m_a.mahalanobis_sq:.2f}  "
              f"sigma {m_a.position_sigma_x:.2f} m")
