"""Load and align the animation export: filter estimate, GPS fixes, RTK truth."""
import bisect, csv, math, os

A, E2 = 6378137.0, 6.69437999014e-3   # WGS84

def enu_factors(lat0):
    s = math.sin(math.radians(lat0))
    N = A / math.sqrt(1 - E2 * s * s)
    M = A * (1 - E2) / (1 - E2 * s * s) ** 1.5
    return N * math.cos(math.radians(lat0)), M          # metres per radian of lon, lat

def load_run(folder, name):
    meta = next(csv.DictReader(open(os.path.join(folder, f"{name}_meta.csv"))))
    t0, lat0, lon0 = float(meta["t0"]), float(meta["lat0"]), float(meta["lon0"])
    kx, ky = enu_factors(lat0)
    def enu(lat, lon):
        return math.radians(lon - lon0) * kx, math.radians(lat - lat0) * ky
    odom = [(float(r["t"]), float(r["x"]), float(r["y"]), float(r["yaw"]))
            for r in csv.DictReader(open(os.path.join(folder, f"{name}_odom.csv")))]
    fixes = []
    for r in csv.DictReader(open(os.path.join(folder, f"{name}_fix.csv"))):
        if not r["lat"]:
            continue
        x, y = enu(float(r["lat"]), float(r["lon"]))
        fixes.append({"t": float(r["t"]), "x": x, "y": y, "reason": r["reason"],
                      "accepted": r["accepted"] == "1", "sigma": float(r["sigma"]), "d2": float(r["d2"])})
    rtk = []
    for r in csv.DictReader(open(os.path.join(folder, "rtk.csv"))):
        x, y = enu(float(r["lat"]), float(r["lon"]))
        rtk.append((float(r["t_abs"]) - t0, x, y))
    return {"t0": t0, "odom": odom, "fixes": fixes, "rtk": clean_rtk(rtk)}

def clean_rtk(rtk, vmax=30.0):
    """Drop RTK outliers implying > vmax m/s, as nclt_rtk_to_tum.py does."""
    out = [rtk[0]]
    for t, x, y in rtk[1:]:
        pt, px, py = out[-1]
        dt = t - pt
        if dt > 0 and math.hypot(x - px, y - py) / dt > vmax:
            continue
        out.append((t, x, y))
    return out

def interp(series, t):
    """Linear interpolation of (t, x, y, ...) at time t; None outside range."""
    ts = [s[0] for s in series] if not hasattr(series, "_ts") else series._ts
    i = bisect.bisect_left(ts, t)
    if i == 0 or i >= len(series):
        return None
    (t1, x1, y1, *_), (t2, x2, y2, *_) = series[i - 1], series[i]
    w = (t - t1) / (t2 - t1) if t2 > t1 else 0.0
    return x1 + w * (x2 - x1), y1 + w * (y2 - y1)
