#!/usr/bin/env python3
"""Extract per-fix gate decisions and 1 Hz filter health from bags to CSV.

Feeds fig_lockout.py, fig_fix_accuracy.py and fig_blackout.py. Needs a
sourced ROS 2 environment with the FusionCore messages built. Output CSVs
are derived from NCLT and are gitignored; do not commit them.

Times are seconds from each bag's first GNSS status message, matching the
episode times in the report.

    python3 extract_figdata.py noout_ON noout_OFF out3_ON out3_OFF \
        blackout_spike_ON --rtk 2012-01-08/gps_rtk.csv --out figdata
"""
import argparse
import bisect
import csv
import math
import os

from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import NavSatFix
from fusioncore_ros.msg import GnssStatus, FilterHealth

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bags", nargs="+")
p.add_argument("--rtk", help="gps_rtk.csv for the same sequence (enables the err column)")
p.add_argument("--out", default="figdata")
p.add_argument("--max-dt", type=float, default=1.0, help="max gap to an RTK fix (s)")
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)

rtk, rt = [], []
if a.rtk:
    for row in csv.reader(open(a.rtk)):
        try:
            ut = int(row[0]); mode = int(float(row[1]))
            lat = math.degrees(float(row[3])); lon = math.degrees(float(row[4]))
        except (ValueError, IndexError):
            continue
        if mode == 3:
            rtk.append((ut / 1e6, lat, lon))
    rtk.sort()
    rt = [x[0] for x in rtk]


def err(stamp, fix):
    f = fix.get(round(stamp, 3))
    if f is None or not rt:
        return None
    i = bisect.bisect_left(rt, stamp)
    cands = [k for k in (i - 1, i) if 0 <= k < len(rt)]
    if not cands:
        return None
    j = min(cands, key=lambda k: abs(rt[k] - stamp))
    if abs(rt[j] - stamp) > a.max_dt:
        return None
    dy = (f[0] - rtk[j][1]) * 110540
    dx = (f[1] - rtk[j][2]) * 111320 * math.cos(math.radians(rtk[j][1]))
    return math.hypot(dx, dy)


for bag in a.bags:
    status, health, fix = [], [], {}
    r = SequentialReader()
    r.open(StorageOptions(uri=bag, storage_id="mcap"), ConverterOptions("", ""))
    while r.has_next():
        topic, data, _ = r.read_next()
        if topic == "/fusion/debug/gnss_status":
            m = deserialize_message(data, GnssStatus)
            status.append((m.header.stamp.sec + m.header.stamp.nanosec / 1e9, m))
        elif topic == "/fusion/debug/filter_health":
            m = deserialize_message(data, FilterHealth)
            health.append((m.header.stamp.sec + m.header.stamp.nanosec / 1e9, m))
        elif topic == "/gnss/fix" and rt:
            m = deserialize_message(data, NavSatFix)
            s = m.header.stamp.sec + m.header.stamp.nanosec / 1e9
            fix[round(s, 3)] = (m.latitude, m.longitude)
    t0 = status[0][0]
    name = os.path.basename(os.path.normpath(bag))

    n_rej = n_err = 0
    with open(os.path.join(a.out, f"{name}_status.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "reason", "accepted", "sigma", "d2", "err"])
        for s, m in status:
            e = err(s, fix)
            n_rej += m.rejection_reason == "CHI2_FAILED"
            n_err += e is not None
            w.writerow([f"{s - t0:.3f}", m.rejection_reason, int(m.accepted),
                        f"{m.position_sigma_x:.4f}", f"{m.mahalanobis_sq:.4f}",
                        "" if e is None else f"{e:.3f}"])
    with open(os.path.join(a.out, f"{name}_health.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "sigma", "coast"])
        for s, m in health:
            w.writerow([f"{s - t0:.3f}", f"{m.position_sigma_x:.4f}", int(m.gnss_in_coast)])
    print(f"{name:20s} fixes {len(status):6d}  chi2-rejected {n_rej:5d}  "
          f"health {len(health):5d}  matched-to-RTK {n_err:6d}")
