#!/usr/bin/env python3
"""Per-fix gate decision, Mahalanobis distance and position sigma in a window.

Supports claim one (report section 3): during coast the position sigma
reaches 77.5 m, yet the specific fix the paper names is rejected at
d2 = 83.3 against a threshold of 16.27.

    python3 gnss_status_window.py path/to/bag --start 3950 --end 3995
"""
import argparse

from fusioncore_ros.msg import GnssStatus
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bag")
p.add_argument("--start", type=float, required=True, help="seconds from first status")
p.add_argument("--end", type=float, required=True)
a = p.parse_args()

rows = list(read_topic(a.bag, "/fusion/debug/gnss_status", GnssStatus))
t0 = rows[0][0]
print(f"{'t+s':>8} {'reason':>18} {'d2':>10} {'thresh':>7} {'sigma_x':>8} coast")
for t, m in rows:
    rel = t - t0
    if a.start <= rel <= a.end:
        print(f"{rel:8.1f} {m.rejection_reason:>18} {m.mahalanobis_sq:10.1f} "
              f"{m.chi2_threshold:7.2f} {m.position_sigma_x:8.2f} {m.in_coast_mode}")
