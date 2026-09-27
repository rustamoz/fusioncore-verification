#!/usr/bin/env python3
"""Position and heading difference between two TUM trajectories over time.

Supports the ablation analysis (report section 4). Times are relative
to each trajectory's own first pose.

    python3 compare_arms.py active.tum frozen.tum --times 100 200 300 304 320
"""
import argparse
import math

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("a_tum")
p.add_argument("b_tum")
p.add_argument("--times", type=float, nargs="+",
               default=[100, 120, 150, 180, 210, 240, 270, 290, 300, 303, 305, 310, 320, 340])
a = p.parse_args()


def load(path):
    out = []
    for line in open(path):
        v = line.split()
        if len(v) >= 8:
            qx, qy, qz, qw = map(float, v[4:8])
            yaw = math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
            out.append((float(v[0]), float(v[1]), float(v[2]), yaw))
    return out


def at(tr, rel):
    tgt = tr[0][0] + rel
    return min(tr, key=lambda r: abs(r[0] - tgt))


A, B = load(a.a_tum), load(a.b_tum)
print(f"{'t+s':>6} {'A x,y':>19} {'B x,y':>19} {'dpos':>8} "
      f"{'A yaw':>8} {'B yaw':>8} {'dyaw':>7}")
for rel in a.times:
    ra, rb = at(A, rel), at(B, rel)
    dp = math.hypot(ra[1] - rb[1], ra[2] - rb[2])
    dy = math.degrees(math.atan2(math.sin(ra[3] - rb[3]), math.cos(ra[3] - rb[3])))
    print(f"{rel:6.0f} ({ra[1]:8.1f},{ra[2]:8.1f}) ({rb[1]:8.1f},{rb[2]:8.1f}) "
          f"{dp:8.1f} {math.degrees(ra[3]):8.1f} {math.degrees(rb[3]):8.1f} {dy:7.1f}")
