#!/usr/bin/env python3
"""Group consecutive chi-squared rejections into episodes.

Supports the lockout finding (report section 5): every run rejects about
a thousand consecutive fixes from t~3492 s, and one never recovers. An
episode ends at the next accepted fix; quality-gate rejections do not end it.

    python3 rejection_episodes.py BAG1 BAG2 ... --top 5
"""
import argparse

from fusioncore_ros.msg import GnssStatus
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bags", nargs="+")
p.add_argument("--top", type=int, default=5, help="longest episodes to print per bag")
a = p.parse_args()

for bag in a.bags:
    G = list(read_topic(bag, "/fusion/debug/gnss_status", GnssStatus))
    t0 = G[0][0]
    eps, cur = [], None
    for t, m in G:
        rel = t - t0
        if m.rejection_reason == "CHI2_FAILED":
            if cur is None:
                cur = [rel, rel, 0, 0.0, ""]
            cur[1] = rel
            cur[2] += 1
            cur[3] = max(cur[3], m.position_sigma_x)
        elif m.accepted and cur:
            eps.append(cur)
            cur = None
    if cur:
        cur[4] = "  <- still rejecting at end of run"
        eps.append(cur)
    tot = sum(e[2] for e in eps)
    print(f"=== {bag}: {len(G)} fixes, {tot} rejected ({100 * tot / len(G):.1f}%), "
          f"{len(eps)} episodes")
    for e in sorted(eps, key=lambda e: -e[2])[:a.top]:
        print(f"  t+{e[0]:6.0f} to t+{e[1]:6.0f} s: {e[2]:5d} rejected, "
              f"max sigma {e[3]:6.1f} m{e[4]}")
