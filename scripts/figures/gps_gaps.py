#!/usr/bin/env python3
"""What happens when GPS returns after each gap in the fix stream.

Supports report section 5: lockouts follow natural GPS gaps, but start
after the first returning fix is accepted, not at the gap itself. Reads
CSVs from extract_figdata.py.

    python3 gps_gaps.py noout_ON noout_OFF out3_ON out3_OFF --data figdata
"""
import argparse

from _figdata import load_status, gaps

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("runs", nargs="+")
ap.add_argument("--data", default="figdata")
ap.add_argument("--min-gap", type=float, default=10.0, help="seconds")
a = ap.parse_args()

for n in a.runs:
    st = load_status(a.data, n)
    print(f"=== {n}")
    for g0, g1 in gaps(st, a.min_gap):
        after = [s for s in st if s["t"] >= g1]
        nrej, acc = 0, None
        for s in after:
            if s["accepted"]:
                acc = s
                break
            if s["reason"] == "CHI2_FAILED":
                nrej += 1
        wait = f"{acc['t'] - g1:7.1f} s" if acc else "  never"
        print(f"  gap t+{g0:6.0f} to {g1:6.0f} s ({g1 - g0:4.0f} s)   "
              f"sigma on return {after[0]['sigma']:6.1f} m   first fix {after[0]['reason']:12s}  "
              f"rejected before first accept {nrej:5d}   wait {wait}")
