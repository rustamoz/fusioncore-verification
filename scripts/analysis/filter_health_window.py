#!/usr/bin/env python3
"""Encoder innovation, heading sigma and position sigma through a window.

Supports the ablation analysis (report section 4): the filter's own
health metrics do not distinguish the two arms during the blackout.

    python3 filter_health_window.py BAG_A BAG_B --start 90 --end 340
"""
import argparse

from fusioncore_ros.msg import FilterHealth
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bags", nargs="+")
p.add_argument("--start", type=float, default=90.0)
p.add_argument("--end", type=float, default=340.0)
p.add_argument("--step", type=int, default=10, help="print every Nth second")
a = p.parse_args()

for bag in a.bags:
    rows = list(read_topic(bag, "/fusion/debug/filter_health", FilterHealth))
    t0 = rows[0][0]
    print(f"\n=== {bag} ===")
    print(f"{'t+s':>7} {'enc_innov':>10} {'hdg_sig':>9} {'pos_sig':>9} coast")
    for t, m in rows:
        rel = t - t0
        if a.start <= rel <= a.end and int(rel) % a.step == 0:
            print(f"{rel:7.0f} {m.encoder_innovation_norm:10.4f} "
                  f"{m.heading_sigma_deg:9.2f} {m.position_sigma_x:9.2f} "
                  f"{m.gnss_in_coast}")
