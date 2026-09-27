#!/usr/bin/env python3
"""Count GNSS fixes by rejection reason from /fusion/debug/gnss_status.

Supports claim one (report section 3): on 2012-08-20 the chi-squared
gate rejected 2,862 fixes and the pre-gate had nothing left to catch.

    python3 rejection_reasons.py path/to/bag
"""
import argparse
from collections import Counter

from fusioncore_ros.msg import GnssStatus
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bag")
a = p.parse_args()

c = Counter(m.rejection_reason for _, m in
            read_topic(a.bag, "/fusion/debug/gnss_status", GnssStatus))
print(f"--- {a.bag} ---")
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print(f"  {k or '(empty)'} : {v}")
