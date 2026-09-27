"""Shared helper: iterate over one topic in a ROS 2 MCAP bag."""
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message


def read_topic(bag, topic, msgtype):
    """Yield (header_stamp_seconds, message) for every message on `topic`."""
    r = SequentialReader()
    r.open(StorageOptions(uri=bag, storage_id="mcap"), ConverterOptions("", ""))
    while r.has_next():
        name, data, _ = r.read_next()
        if name == topic:
            m = deserialize_message(data, msgtype)
            yield m.header.stamp.sec + m.header.stamp.nanosec / 1e9, m
