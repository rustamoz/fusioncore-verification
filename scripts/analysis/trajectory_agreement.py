#!/usr/bin/env python3
"""Pose-by-pose distance between two TUM trajectories at matched timestamps.

Build validation (report section 2): my spike-test output agreed with
the author's shipped fusioncore_spike.tum to within 2.60 m (mean 1.09 m)
across 2,792 matched timestamps.

    python3 trajectory_agreement.py theirs.tum mine.tum
"""
import argparse
import math

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("reference_tum")
p.add_argument("test_tum")
p.add_argument("--rows", type=int, default=25, help="how many samples to print")
a = p.parse_args()


def load(path):
    d = {}
    for line in open(path):
        v = line.split()
        if len(v) >= 4:
            d[round(float(v[0]), 2)] = (float(v[1]), float(v[2]))
    return d


ref, test = load(a.reference_tum), load(a.test_tum)
common = sorted(set(ref) & set(test))
print(f"reference: {len(ref)}  test: {len(test)}  common timestamps: {len(common)}")
if not common:
    raise SystemExit("no overlapping timestamps")
t0 = common[0]
diffs = [math.hypot(test[t][0] - ref[t][0], test[t][1] - ref[t][1]) for t in common]
for t in common[::max(1, len(common) // a.rows)]:
    r, m = ref[t], test[t]
    print(f"  t+{t - t0:6.1f}s  ref=({r[0]:7.1f},{r[1]:7.1f})  "
          f"test=({m[0]:7.1f},{m[1]:7.1f})  diff={math.hypot(m[0]-r[0], m[1]-r[1]):6.1f}m")
print(f"\nmin {min(diffs):.2f} m   max {max(diffs):.2f} m   "
      f"mean {sum(diffs) / len(diffs):.2f} m")
