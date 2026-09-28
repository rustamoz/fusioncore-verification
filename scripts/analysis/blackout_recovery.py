#!/usr/bin/env python3
"""Every GPS fix from the end of a blackout to the first accepted fix,
checked against RTK ground truth.

Supports report section 3: on 2012-08-20 the gate rejects the corrupted
cluster (about 820-840 m from the truth), then 45 good fixes, before one is
accepted. Also reports the offset between the filter's clock and the GPS
log's, and whether the last fix before the blackout was accepted.

    python3 blackout_recovery.py ../0820_debug ../2012-08-20 --after 3500 --before 4100
"""
import argparse
import bisect
import csv
import math
import os

from fusioncore_ros.msg import GnssStatus
from sensor_msgs.msg import NavSatFix
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bag")
p.add_argument("data_dir", help="NCLT sequence folder with gps.csv and gps_rtk.csv")
p.add_argument("--after", type=float, default=0.0, help="look for the gap after this filter time (s)")
p.add_argument("--before", type=float, default=1e9)
p.add_argument("--bad", type=float, default=100.0, help="error vs truth above which a fix counts as corrupted (m)")
a = p.parse_args()

G = list(read_topic(a.bag, "/fusion/debug/gnss_status", GnssStatus))
t0 = G[0][0]
F = {round(t, 3): (m.latitude, m.longitude) for t, m in read_topic(a.bag, "/gnss/fix", NavSatFix)}
R = []
for r in csv.reader(open(os.path.join(a.data_dir, "gps_rtk.csv"))):
    try:
        ut = int(r[0]); md = int(float(r[1])); la = math.degrees(float(r[3])); lo = math.degrees(float(r[4]))
    except (ValueError, IndexError):
        continue
    if md == 3:
        R.append((ut / 1e6, la, lo))
R.sort(); rt = [x[0] for x in R]
g0 = None
for r in csv.reader(open(os.path.join(a.data_dir, "gps.csv"))):
    try:
        ut = int(r[0]); md = int(float(r[1]))
    except (ValueError, IndexError):
        continue
    if md >= 3:
        g0 = ut / 1e6; break


def err(t):
    f = F.get(round(t, 3)); i = bisect.bisect_left(rt, t)
    c = [k for k in (i - 1, i) if 0 <= k < len(R)]
    if not f or not c:
        return None
    k = min(c, key=lambda k: abs(rt[k] - t))
    if abs(rt[k] - t) > 2:
        return None
    return math.hypot((f[0] - R[k][1]) * 110540, (f[1] - R[k][2]) * 111320 * math.cos(math.radians(f[0])))


print(f"filter clock zero is {t0 - g0:+.2f} s after the GPS log's")
k = max((j for j in range(1, len(G)) if a.after < G[j][0] - t0 < a.before),
        key=lambda j: G[j][0] - G[j - 1][0])
print(f"longest gap {G[k][0] - G[k - 1][0]:.2f} s, ends at filter t+{G[k][0] - t0:.2f} (GPS log t+{G[k][0] - g0:.2f})")
lt, lm = G[k - 1]
print(f"last fix before it: filter t+{lt - t0:.2f} {lm.rejection_reason} d2 {lm.mahalanobis_sq:.2f}")
acc = next(j for j in range(k, len(G)) if G[j][1].accepted)
groups = {"corrupted": [], "good": [], "no truth": []}
for t, m in G[k:acc]:
    e = err(t)
    key = "no truth" if e is None else ("corrupted" if e > a.bad else "good")
    groups[key].append((t - t0, e, m.mahalanobis_sq))
print(f"first accepted fix: filter t+{G[acc][0] - t0:.2f}, d2 {G[acc][1].mahalanobis_sq:.2f}, "
      f"error {err(G[acc][0]):.1f} m; {acc - k} rejected before it")
for name, v in groups.items():
    if not v:
        print(f"  {name:9s}: 0"); continue
    ts = [x[0] for x in v]; d2 = [x[2] for x in v]
    line = f"  {name:9s}: {len(v):3d}  filter t+{min(ts):.1f} to {max(ts):.1f} s, d2 {min(d2):.2f}-{max(d2):.2f}"
    es = [x[1] for x in v if x[1] is not None]
    if es:
        line += f", error vs truth {min(es):.0f}-{max(es):.0f} m"
    print(line)
