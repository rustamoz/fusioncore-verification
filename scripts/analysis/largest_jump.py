#!/usr/bin/env python3
"""Largest single-step position jump in each TUM trajectory.

Locates the long-run excursion (report sections 2 and 7) and
distinguishes it from GPS re-anchoring after an injected outage.

    python3 largest_jump.py run1.tum run2.tum ...
"""
import argparse
import math

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("tums", nargs="+")
a = p.parse_args()

for path in a.tums:
    tr = []
    for line in open(path):
        v = line.split()
        if len(v) >= 4:
            tr.append((float(v[0]), float(v[1]), float(v[2])))
    t0, mx, mt = tr[0][0], 0.0, 0.0
    for i in range(1, len(tr)):
        d = math.hypot(tr[i][1] - tr[i - 1][1], tr[i][2] - tr[i - 1][2])
        if d > mx:
            mx, mt = d, tr[i][0] - t0
    print(f"{path}: biggest single-step jump {mx:8.1f} m at t+{mt:.0f}s")
