"""Shared loaders for the CSVs written by extract_figdata.py."""
import csv
import os


def load_status(folder, name):
    rows = []
    for r in csv.DictReader(open(os.path.join(folder, f"{name}_status.csv"))):
        rows.append({"t": float(r["t"]), "reason": r["reason"],
                     "accepted": r["accepted"] == "1", "sigma": float(r["sigma"]),
                     "d2": float(r["d2"]), "err": float(r["err"]) if r["err"] else None})
    return rows


def load_health(folder, name):
    return [(float(r["t"]), float(r["sigma"]), r["coast"] == "1")
            for r in csv.DictReader(open(os.path.join(folder, f"{name}_health.csv")))]


def gaps(status, min_gap=10.0):
    """(start, end) of stretches with no GNSS fix for longer than min_gap seconds."""
    ts = [s["t"] for s in status]
    return [(ts[i - 1], ts[i]) for i in range(1, len(ts)) if ts[i] - ts[i - 1] > min_gap]


def episodes(status):
    """Consecutive chi-squared rejections, closed by the next accepted fix."""
    eps, cur = [], None
    for s in status:
        if s["reason"] == "CHI2_FAILED":
            if cur is None:
                cur = {"start": s["t"], "end": s["t"], "n": 0, "open": False}
            cur["end"] = s["t"]; cur["n"] += 1
        elif s["accepted"] and cur:
            eps.append(cur); cur = None
    if cur:
        cur["open"] = True; eps.append(cur)
    return eps
