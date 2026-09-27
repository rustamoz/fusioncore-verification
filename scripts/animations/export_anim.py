#!/usr/bin/env python3
"""Export compact position data for the lockout animation.

Writes, for each bag:
  <name>_odom.csv   t, x, y, yaw          filter estimate, subsampled
  <name>_fix.csv    t, lat, lon, reason, accepted, sigma, d2
  <name>_meta.csv   t0 (absolute sim seconds of the first GNSS status),
                    lat0, lon0 (first GNSS fix in the bag)
and once:
  rtk.csv           t_abs, lat, lon       RTK ground truth, mode 3 only

Times in odom and fix files are seconds from the first GNSS status, the
same zero used everywhere in the report. Output is derived from NCLT
(Open Database License); do not commit it.

    python3 export_anim.py out3_ON out3_OFF --rtk 2012-01-08/gps_rtk.csv
"""
import argparse
import csv
import math
import os

from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry
from sensor_msgs.msg import NavSatFix
from fusioncore_ros.msg import GnssStatus

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bags", nargs="+")
p.add_argument("--rtk", required=True)
p.add_argument("--out", default="anim_export")
p.add_argument("--odom-hz", type=float, default=10.0)
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)


def stamp(m):
    return m.header.stamp.sec + m.header.stamp.nanosec / 1e9


n_rtk = 0
with open(os.path.join(a.out, "rtk.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t_abs", "lat", "lon"])
    for row in csv.reader(open(a.rtk)):
        try:
            ut = int(row[0]); mode = int(float(row[1]))
            lat = math.degrees(float(row[3])); lon = math.degrees(float(row[4]))
        except (ValueError, IndexError):
            continue
        if mode == 3:
            w.writerow([f"{ut / 1e6:.3f}", f"{lat:.8f}", f"{lon:.8f}"])
            n_rtk += 1
print(f"rtk: {n_rtk} mode-3 fixes")

for bag in a.bags:
    name = os.path.basename(os.path.normpath(bag))
    odom, fixes, status = [], {}, []
    r = SequentialReader()
    r.open(StorageOptions(uri=bag, storage_id="mcap"), ConverterOptions("", ""))
    while r.has_next():
        topic, data, _ = r.read_next()
        if topic == "/fusion/odom":
            m = deserialize_message(data, Odometry)
            q = m.pose.pose.orientation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            odom.append((stamp(m), m.pose.pose.position.x, m.pose.pose.position.y, yaw))
        elif topic == "/gnss/fix":
            m = deserialize_message(data, NavSatFix)
            fixes[round(stamp(m), 3)] = (m.latitude, m.longitude)
        elif topic == "/fusion/debug/gnss_status":
            m = deserialize_message(data, GnssStatus)
            status.append((stamp(m), m))

    t0 = status[0][0]
    first_fix = min(fixes.items())[1] if fixes else (float("nan"), float("nan"))
    with open(os.path.join(a.out, f"{name}_meta.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t0", "lat0", "lon0"])
        w.writerow([f"{t0:.3f}", f"{first_fix[0]:.8f}", f"{first_fix[1]:.8f}"])

    step = 1.0 / a.odom_hz
    kept, last = 0, None
    odom.sort()
    with open(os.path.join(a.out, f"{name}_odom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "x", "y", "yaw"])
        for s, x, y, yaw in odom:
            if last is not None and s - last < step:
                continue
            w.writerow([f"{s - t0:.3f}", f"{x:.3f}", f"{y:.3f}", f"{yaw:.4f}"])
            last = s; kept += 1

    n_pos = 0
    with open(os.path.join(a.out, f"{name}_fix.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "lat", "lon", "reason", "accepted", "sigma", "d2"])
        for s, m in status:
            ll = fixes.get(round(s, 3))
            n_pos += ll is not None
            w.writerow([f"{s - t0:.3f}",
                        "" if ll is None else f"{ll[0]:.8f}",
                        "" if ll is None else f"{ll[1]:.8f}",
                        m.rejection_reason, int(m.accepted),
                        f"{m.position_sigma_x:.4f}", f"{m.mahalanobis_sq:.4f}"])
    print(f"{name:12s} odom {len(odom):7d} -> {kept:6d} kept   status {len(status):6d}   "
          f"with position {n_pos:6d}   t0 {t0:.3f}   first fix {first_fix[0]:.6f}, {first_fix[1]:.6f}")
