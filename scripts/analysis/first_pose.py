#!/usr/bin/env python3
"""First /fusion/odom pose in each bag.

Checks every run initialised at the origin, ruling out a bad start
as the cause of a large ATE (report section 4).

    python3 first_pose.py BAG1 BAG2 ...
"""
import argparse

from nav_msgs.msg import Odometry
from _bag import read_topic

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("bags", nargs="+")
a = p.parse_args()

for bag in a.bags:
    for _, m in read_topic(bag, "/fusion/odom", Odometry):
        q = m.pose.pose.position
        print(f"{bag}: first pose ({q.x:.4f}, {q.y:.4f}, {q.z:.4f})")
        break
