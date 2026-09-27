#!/usr/bin/env python3
"""Error of each GNSS fix against RTK ground truth, split by gate decision.

Supports the lockout finding (report section 5): rejected fixes are as
close to ground truth as accepted ones, so the gate was rejecting good GPS.
Each fix is matched to the nearest mode-3 RTK fix within --max-dt seconds.

    python3 fix_vs_truth.py BAG DATA/2012-01-08/gps_rtk.csv --window 3490 3716
"""
import argparse
import bisect
import csv
import math

from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import NavSatFix
from fusioncore_ros.msg import GnssStatus

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bag")
p.add_argument("rtk_csv")
p.add_argument("--window", type=float, nargs=2, metavar=("START", "END"),
               help="also report rejected fixes in this window (s from first status)")
p.add_argument("--max-dt", type=float, default=1.0, help="max time gap to an RTK fix (s)")
a = p.parse_args()

rtk = []
for row in csv.reader(open(a.rtk_csv)):
    try:
        ut = int(row[0])
        mode = int(float(row[1]))
        lat = math.degrees(float(row[3]))
        lon = math.degrees(float(row[4]))
    except (ValueError, IndexError):
        continue
    if mode == 3:
        rtk.append((ut / 1e6, lat, lon))
rtk.sort()
rt = [x[0] for x in rtk]

fix, stat = {}, []
r = SequentialReader()
r.open(StorageOptions(uri=a.bag, storage_id="mcap"), ConverterOptions("", ""))
while r.has_next():
    topic, data, _ = r.read_next()
    if topic == "/gnss/fix":
        m = deserialize_message(data, NavSatFix)
        s = m.header.stamp.sec + m.header.stamp.nanosec / 1e9
        fix[round(s, 3)] = (m.latitude, m.longitude)
    elif topic == "/fusion/debug/gnss_status":
        m = deserialize_message(data, GnssStatus)
        stat.append((m.header.stamp.sec + m.header.stamp.nanosec / 1e9, m.rejection_reason))
t0 = stat[0][0]


def err(s):
    f = fix.get(round(s, 3))
    if f is None:
        return None
    i = bisect.bisect_left(rt, s)
    cands = [k for k in (i - 1, i) if 0 <= k < len(rt)]
    if not cands:
        return None
    j = min(cands, key=lambda k: abs(rt[k] - s))
    if abs(rt[j] - s) > a.max_dt:
        return None
    dy = (f[0] - rtk[j][1]) * 110540
    dx = (f[1] - rtk[j][2]) * 111320 * math.cos(math.radians(rtk[j][1]))
    return math.hypot(dx, dy)


def summary(label, vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        print(f"  {label:34s} no RTK truth available ({len(vals)} fixes)")
        return
    print(f"  {label:34s} {len(v):5d}/{len(vals):5d} matched  "
          f"median {v[len(v) // 2]:6.1f} m  90th {v[int(.9 * len(v))]:6.1f} m")


print(f"=== {a.bag}  (fix error against RTK truth)")
summary("accepted fixes", [err(s) for s, rr in stat if rr == "ACCEPTED"])
summary("rejected fixes, whole run", [err(s) for s, rr in stat if rr == "CHI2_FAILED"])
if a.window:
    lo, hi = a.window
    summary(f"rejected fixes, t+{lo:.0f} to {hi:.0f} s",
            [err(s) for s, rr in stat if rr == "CHI2_FAILED" and lo <= s - t0 <= hi])
