#!/usr/bin/env python3
"""Figure: why a displacement/elapsed-time speed check cannot catch the cluster.
Reads NCLT gps.csv directly so the figure is reproducible from raw data."""
import argparse, csv, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser(description="Speed-gate threshold figure")
ap.add_argument("gps_csv", help="path to NCLT 2012-08-20/gps.csv")
ap.add_argument("--threshold", type=float, default=20.0, help="m/s")
ap.add_argument("--out", default="fig_speedgate.png")
args = ap.parse_args()
GPS, THRESH, OUT = args.gps_csv, args.threshold, args.out

def load(path):
    rows = []
    for r in csv.reader(open(path)):
        try:
            ut = int(r[0]); mode = int(float(r[1]))
            lat = math.degrees(float(r[3])); lon = math.degrees(float(r[4]))
        except (ValueError, IndexError):
            continue
        if mode >= 3:
            rows.append((ut, lat, lon))
    return rows

rows = load(GPS)
t0 = rows[0][0]
steps = []
prev = None
for ut, lat, lon in rows:
    if prev:
        dx = (lon - prev[2]) * 111320 * math.cos(math.radians(lat))
        dy = (lat - prev[1]) * 110540
        d  = math.hypot(dx, dy)
        dt = (ut - prev[0]) / 1e6
        if dt > 0 and d > 0:
            steps.append(((ut - t0) / 1e6, dt, d))
    prev = (ut, lat, lon)

normal = [(dt, d) for _, dt, d in steps if d <= 300]
big    = [(rel, dt, d) for rel, dt, d in steps if d > 300]

fig, ax = plt.subplots(figsize=(8.4, 5.6))
n_over = sum(1 for dt, d in normal if d / dt > THRESH)
ax.scatter([s[0] for s in normal], [s[1] for s in normal],
           s=6, c="#9fb3c8", alpha=0.35, edgecolors="none",
           label=f"ordinary fix-to-fix steps (n={len(normal):,}; "
                 f"{n_over:,} exceed the threshold)", zorder=2)

lo, hi = 0.05, 1500
ax.plot([lo, hi], [THRESH*lo, THRESH*hi], color="#1d9e75", lw=2,
        label=f"pre-gate threshold ({THRESH:.0f} m/s)", zorder=4)
ax.fill_between([lo, hi], [THRESH*lo, THRESH*hi], 1e5,
                color="#1d9e75", alpha=0.07, zorder=1)
ax.text(0.075, 60, "above the line: REJECTED", color="#137a58", fontsize=9.5,
        fontweight="bold", zorder=5)
ax.text(0.075, 0.045, "below the line: ACCEPTED", color="#5f5e5a", fontsize=9.5,
        fontweight="bold", zorder=5)

mk = dict(s=95, zorder=6, edgecolors="white", linewidths=1.4)
big.sort(key=lambda b: b[1])                    # left to right by gap
# label positions in data coordinates, chosen to sit in empty space
# (red: above the line, right of the point; orange: below the line)
placements = [((0.9, 1300), "left"), ((55, 55), "left"), ((115, 230), "left")]
for i, (rel, dt, d) in enumerate(big):
    sp = d / dt
    caught = sp > THRESH
    col = "#a32d2d" if caught else "#c26a00"
    ax.scatter([dt], [d], c=col, **mk)
    verdict = "rejected" if caught else "ACCEPTED"
    xy_text, ha = placements[i] if i < len(placements) else ((dt * 2, d / 3), "left")
    ax.annotate(f"t+{rel:.0f} s   {verdict}\n{d:.0f} m / {dt:.2f} s = {sp:,.1f} m/s",
                xy=(dt, d), xytext=xy_text, textcoords="data", ha=ha,
                fontsize=8.5, color=col,
                arrowprops=dict(arrowstyle="-", lw=0.8, color=col,
                                shrinkA=2, shrinkB=5))

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(lo, hi); ax.set_ylim(0.03, 6000)
ax.set_xlabel("time since previous fix in the raw GPS log (s)")
ax.set_ylabel("displacement from previous fix (m)")
ax.set_title("A displacement / elapsed-time check cannot reject the post-blackout fix",
             fontsize=11.5, pad=12)
ax.text(0.985, 0.055,
        "The threshold is a slope, not a limit.\n"
        "A 20 m/s gate permits 200 m after a 10 s gap\n"
        "and 4.2 km after the 211 s blackout.",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8.8,
        color="#137a58",
        bbox=dict(boxstyle="round,pad=0.5", fc="#f2faf7", ec="#1d9e75", lw=0.8))
ax.grid(True, which="both", alpha=0.18, lw=0.5)
ax.legend(loc="center right", frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(OUT, dpi=200)
print(f"wrote {OUT}; {len(steps):,} steps, {len(big)} over 300 m, "
      f"{n_over:,} ordinary steps above {THRESH:.0f} m/s")
