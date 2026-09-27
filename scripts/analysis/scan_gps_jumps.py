#!/usr/bin/env python3
"""List consecutive mode-3 GPS fixes further apart than a threshold.

Supports claim one (report section 3): the fix arriving after the
211 s blackout on 2012-08-20 implies 3.4 m/s, not the 3400 m/s the
paper states.

NCLT gps.csv columns: utime, mode, ?, lat_rad, lon_rad, alt_m, ?, ?

    python3 scan_gps_jumps.py 2012-08-20/gps.csv --min-jump 300
"""
import argparse
import csv
import math

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("gps_csv")
p.add_argument("--min-jump", type=float, default=300.0, help="metres")
a = p.parse_args()

prev = None
t0 = None
for row in csv.reader(open(a.gps_csv)):
    try:
        ut = int(row[0])
        mode = int(float(row[1]))
        lat = math.degrees(float(row[3]))
        lon = math.degrees(float(row[4]))
    except (ValueError, IndexError):
        continue
    if mode < 3:
        continue
    if t0 is None:
        t0 = ut
    if prev:
        dx = (lon - prev[1]) * 111320 * math.cos(math.radians(lat))
        dy = (lat - prev[0]) * 110540
        d = math.hypot(dx, dy)
        dt = (ut - prev[2]) / 1e6
        if d > a.min_jump and dt > 0:
            print(f"t+{(ut - t0) / 1e6:7.1f}s  jump={d:7.1f}m  "
                  f"dt={dt:.2f}s  implied={d / dt:8.1f} m/s")
    prev = (lat, lon, ut)
