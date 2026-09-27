#!/usr/bin/env python3
"""Find gaps in the GNSS stream longer than a threshold.

Confirms an injected outage actually landed where intended
(report section 4: a 200.2 s gap starting at t+104.3 s).

    python3 outage_gaps.py path/to/bag --min-gap 10
"""
import argparse

from fusioncore_ros.msg import GnssStatus
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bag")
p.add_argument("--min-gap", type=float, default=10.0, help="seconds")
a = p.parse_args()

ts = [t for t, _ in read_topic(a.bag, "/fusion/debug/gnss_status", GnssStatus)]
t0 = ts[0]
print(f"{len(ts)} fixes; gaps > {a.min_gap:.0f} s:")
for i in range(1, len(ts)):
    g = ts[i] - ts[i - 1]
    if g > a.min_gap:
        print(f"  gap of {g:6.1f}s starting at t+{ts[i - 1] - t0:.1f}s")
