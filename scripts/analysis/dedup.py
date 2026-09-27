#!/usr/bin/env python3
"""Remove poses that repeat an earlier timestamp from a TUM trajectory.

Supports the harness finding (report section 5): recorded FusionCore
odometry carried between 38% and 95% duplicate timestamps before the fix.

    python3 dedup.py fc.tum fc_clean.tum
"""
import argparse

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("input")
p.add_argument("output")
a = p.parse_args()

seen, total, kept = set(), 0, 0
with open(a.input) as f, open(a.output, "w") as out:
    for line in f:
        total += 1
        t = line.split()[0]
        if t in seen:
            continue
        seen.add(t)
        out.write(line)
        kept += 1
dup = total - kept
pct = 100 * dup / total if total else 0.0
print(f"{a.input}: {total} -> {kept} ({dup} duplicates removed, {pct:.1f}%)")
