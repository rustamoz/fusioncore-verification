#!/usr/bin/env python3
"""Show every mode-3 fix in a time window with its step and implied speed.

Supports claim one (report section 3): the adversarial cluster on
2012-08-20 is internally smooth, so a fix-to-fix speed check cannot
distinguish it from normal driving.

    python3 gps_cluster_window.py 2012-08-20/gps.csv --start 3940 --end 4010
"""
import argparse
import csv
import math

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("gps_csv")
p.add_argument("--start", type=float, required=True, help="seconds from first fix")
p.add_argument("--end", type=float, required=True)
a = p.parse_args()

rows = []
for row in csv.reader(open(a.gps_csv)):
    try:
        ut = int(row[0])
        mode = int(float(row[1]))
        lat = math.degrees(float(row[3]))
        lon = math.degrees(float(row[4]))
    except (ValueError, IndexError):
        continue
    if mode >= 3:
        rows.append((ut, lat, lon))

t0 = rows[0][0]
win = [r for r in rows if a.start <= (r[0] - t0) / 1e6 <= a.end]
print(f"{len(win)} mode-3 fixes in t+{a.start:.0f}..{a.end:.0f}s\n")
prev = None
for ut, lat, lon in win:
    if prev:
        dx = (lon - prev[2]) * 111320 * math.cos(math.radians(lat))
        dy = (lat - prev[1]) * 110540
        d = math.hypot(dx, dy)
        dt = (ut - prev[0]) / 1e6
        sp = d / dt if dt > 0 else 0.0
        print(f"t+{(ut - t0) / 1e6:7.1f}s  gap={dt:6.2f}s  "
              f"step={d:8.1f}m  implied={sp:9.1f} m/s")
    prev = (ut, lat, lon)
