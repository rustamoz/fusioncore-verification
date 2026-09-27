#!/usr/bin/env python3
"""Render the GPS lockout animation (report section 5).

Two synchronised map panels, the 23rd state active and frozen, both with the
200 s injected outage, over the stretch where every run locks out. Reads the
CSVs written by export_anim.py; optionally the 1 Hz health CSVs from
extract_figdata.py for the uncertainty during GPS gaps.

    python3 render_lockout.py --data anim_export --health figdata --out lockout.mp4
    python3 render_lockout.py ... --preview 4 9 12 20 26 32 38   # PNG frames only
"""
import argparse
import bisect
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.animation import FFMpegWriter
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from animdata import load_run

# ---- site visual system (CLAUDE.md section 4) ------------------------------
BG, INK, MUTED, LINE, ACC = "#F5F5F2", "#111111", "#6B6B67", "#D9D9D4", "#1E7F4F"
REJ = "#A32D2D"          # rejected fixes; shape (x) also distinguishes them
SANS, MONO = "Geist", "JetBrains Mono"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--data", default="anim_export")
ap.add_argument("--health", default=None, help="folder with <run>_health.csv (optional)")
ap.add_argument("--fonts", default="fonts")
ap.add_argument("--out", default="lockout.mp4")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--dpi", type=int, default=100)
ap.add_argument("--preview", type=float, nargs="*", help="render PNGs at these video times (s) instead")
a = ap.parse_args()

for f in os.listdir(a.fonts):
    if f.endswith(".ttf"):
        font_manager.fontManager.addfont(os.path.join(a.fonts, f))
plt.rcParams.update({"font.family": SANS, "text.color": INK, "axes.edgecolor": LINE,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})

# ---- data on one absolute clock -------------------------------------------
RUNS = [("out3_ON", "23rd state active"), ("out3_OFF", "23rd state frozen")]
raw = {n: load_run(a.data, n) for n, _ in RUNS}
REF = raw["out3_OFF"]["t0"]                   # zero of the clock shown, as in results/


def shift(n):
    return raw[n]["t0"] - REF


def health_sigma(n):
    """1 Hz sigma from the health CSV if available, else None."""
    if not a.health:
        return None
    p = os.path.join(a.health, f"{n}_health.csv")
    if not os.path.exists(p):
        return None
    return [(float(r["t"]) + shift(n), float(r["sigma"])) for r in csv.DictReader(open(p))]


runs = {}
for n, label in RUNS:
    d, s = raw[n], shift(n)
    odom = [(t + s, x, y) for t, x, y, _ in d["odom"]]
    fixes = [dict(f, t=f["t"] + s) for f in d["fixes"]]
    sig = health_sigma(n)
    src = "health"
    if sig is None:
        # stand-in: per-fix sigma; across gaps, variance interpolated linearly
        sig = [(f["t"], f["sigma"]) for f in fixes]
        src = "per-fix"
    runs[n] = {"label": label, "odom": odom, "ot": [o[0] for o in odom], "fixes": fixes,
               "ft": [f["t"] for f in fixes], "sig": sig, "st": [q[0] for q in sig], "sigsrc": src}
for r in runs.values():
    # where an accepted fix moves the estimate visibly, the estimate's timestamps can lag
    # the update by a sample; hold the pre-update uncertainty until the jump appears
    r["pending"] = []
    od, acc = r["odom"], [f for f in r["fixes"] if f["accepted"]]
    at = [f["t"] for f in acc]
    for k in range(1, len(od)):
        if math.hypot(od[k][1] - od[k - 1][1], od[k][2] - od[k - 1][2]) > 10.0:
            i = bisect.bisect_right(at, od[k][0]) - 1
            if i >= 0 and od[k][0] - at[i] < 1.0:
                r["pending"].append((at[i], od[k][0], acc[i]["sigma"]))
truth = [(t + shift("out3_OFF"), x, y) for t, x, y in raw["out3_OFF"]["rtk"]]
tt = [q[0] for q in truth]

T0, T1 = 3340.0, 3990.0
# mission time -> video time; every caption phase gets at least ~4 s on screen
KEYS = [(3340.0, 0.0),      # normal operation
        (3380.0, 5.0),      # signal lost
        (3492.45, 10.5),    # signal returns: the bad fix appears and is accepted, very slowly
        (3492.70, 16.5),
        (3497.5, 22.0),     # uncertainty collapsed; the settling fixes are rejected
        (3713.0, 27.0),     # locked out
        (3916.0, 31.0),     # signal lost again
        (3941.73, 36.0),    # GPS returns; estimates far away
        (3990.0, 40.0)]     # frozen run recovers, active never does
HOLD = 5.0
DURATION = KEYS[-1][1] + HOLD

CAPTIONS = [
    (3340.0, "Normal operation. Each GPS fix is accepted and keeps the estimate on the true path."),
    (3380.0, "The receiver loses its signal. The filter dead-reckons, and its uncertainty grows."),
    (3492.45, "The signal returns. The first fix is 157 m from the truth, but the enlarged gate lets it through."),
    (3492.70, "Uncertainty collapses to 3 m at the wrong place. The good fixes that follow are all rejected."),
    (3497.5, "Locked out. Every fix is refused, so nothing can correct the drift."),
    (3713.0, "The signal is lost again, this time for 203 s."),
    (3916.0, "GPS returns and the fixes are good, but both estimates are now hundreds of metres away."),
    (3941.73, "Frozen run: one fix scores 16.25 against the 16.27 threshold, and the estimate snaps back. Active run: never."),
]
BAD_T = 3492.53


def mission_time(v):
    if v >= KEYS[-1][1]:
        return KEYS[-1][0], 0.0
    for (m0, v0), (m1, v1) in zip(KEYS, KEYS[1:]):
        if v0 <= v < v1:
            return m0 + (m1 - m0) * (v - v0) / (v1 - v0), (m1 - m0) / (v1 - v0)
    return KEYS[0][0], 0.0


def step_xy(series, ts, t):
    """Last sample at or before t. Filter updates are instantaneous, so the
    estimate must jump, never slide between samples."""
    i = bisect.bisect_right(ts, t) - 1
    i = min(max(i, 0), len(series) - 1)
    return series[i][1], series[i][2]


def sigma_at(r, t):
    """Each fix records the covariance just before its update. While fixes are
    dense, the next fix's value is the current uncertainty. Across a gap, use
    the 1 Hz health data, or failing that interpolate variance linearly."""
    # evaluate at the displayed estimate sample, so position and uncertainty change together
    k = bisect.bisect_right(r["ot"], t) - 1
    td = r["ot"][k] if k >= 0 else t
    for a_, b_, s0 in r["pending"]:
        if a_ <= td < b_:
            return s0
    j = bisect.bisect_right(r["ft"], td)
    if j < len(r["ft"]) and r["ft"][j] - td <= 1.0:
        return r["fixes"][j]["sigma"]
    ts, sig = r["st"], r["sig"]
    i = bisect.bisect_left(ts, t)
    if i <= 0:
        return sig[0][1]
    if i >= len(sig):
        return sig[-1][1]
    (t1, s1), (t2, s2) = sig[i - 1], sig[i]
    w = (t - t1) / (t2 - t1) if t2 > t1 else 0.0
    return math.sqrt(s1 * s1 + w * (s2 * s2 - s1 * s1))      # variance grows linearly


def truth_at(t, tol=1.5):   # same tolerance as the 157 m measurement in results/
    i = bisect.bisect_left(tt, t)
    best = None
    for k in (i - 1, i):
        if 0 <= k < len(truth) and abs(tt[k] - t) <= tol:
            if best is None or abs(tt[k] - t) < abs(tt[best] - t):
                best = k
    return None if best is None else truth[best][1:]


def streak(r, t):
    """Consecutive chi-squared rejections up to time t."""
    i = bisect.bisect_right(r["ft"], t) - 1
    n = 0
    while i >= 0 and not r["fixes"][i]["accepted"]:
        n += r["fixes"][i]["reason"] == "CHI2_FAILED"
        i -= 1
    return n


# ---- figure ----------------------------------------------------------------
W, H = 16, 9
fig = plt.figure(figsize=(W, H), dpi=a.dpi, facecolor=BG)
cap = fig.text(0.04, 0.935, "", fontsize=17, color=INK, va="center")
clock = fig.text(0.96, 0.935, "", fontsize=12, color=MUTED, ha="right", va="center", family=MONO)
fig.text(0.04, 0.975, "GPS LOCKOUT  /  NCLT 2012-01-08  /  TWO RUNS, SAME DATA", fontsize=10,
         color=MUTED, family=MONO, va="center")

xs = [o[1] for r in runs.values() for o in r["odom"] if T0 <= o[0] <= T1] + [q[1] for q in truth if T0 <= q[0] <= T1]
ys = [o[2] for r in runs.values() for o in r["odom"] if T0 <= o[0] <= T1] + [q[2] for q in truth if T0 <= q[0] <= T1]
for r in runs.values():                     # keep the whole uncertainty circle on the map
    for t_ in range(int(T0), int(T1) + 1, 2):
        ex_, ey_ = step_xy(r["odom"], r["ot"], t_); s_ = min(sigma_at(r, t_), 120)
        xs += [ex_ - s_, ex_ + s_]; ys += [ey_ - s_, ey_ + s_]
cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 30

panels = {}
for k, (n, label) in enumerate(RUNS):
    ax = fig.add_axes([0.04 + k * 0.475, 0.235, 0.445, 0.64], facecolor=BG)
    ax.set_xlim(cx - half * 1.12, cx + half * 1.12); ax.set_ylim(cy - half, cy + half)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(LINE)
    tw = [q for q in truth if T0 <= q[0] <= T1]
    # draw truth with its gaps left as gaps
    seg = [tw[0]]
    for q in tw[1:]:
        if q[0] - seg[-1][0] > 3:
            ax.plot([p[1] for p in seg], [p[2] for p in seg], color=MUTED, lw=1.6, alpha=0.5, zorder=1)
            seg = []
        seg.append(q)
    ax.plot([p[1] for p in seg], [p[2] for p in seg], color=MUTED, lw=1.6, alpha=0.5, zorder=1)
    # 100 m scale bar
    sx, sy = cx + half * 1.05 - 100, cy - half * 0.93
    ax.plot([sx, sx + 100], [sy, sy], color=MUTED, lw=1.5)
    ax.text(sx + 50, sy + half * 0.025, "100 m", ha="center", va="bottom", fontsize=9, color=MUTED, family=MONO)
    p = {
        "ax": ax,
        "circle": ax.add_patch(Circle((0, 0), 1, facecolor=INK, alpha=0.08, edgecolor=INK, lw=0.8, zorder=2)),
        "trail": ax.plot([], [], color=INK, lw=1.4, alpha=0.8, zorder=3)[0],
        "acc": ax.scatter([], [], s=22, marker="o", zorder=4),
        "rej": ax.scatter([], [], s=34, marker="x", linewidths=1.3, zorder=4),
        "true": ax.plot([], [], marker="o", ms=11, mfc="none", mec=MUTED, mew=1.6, ls="", zorder=5)[0],
        "est": ax.plot([], [], marker="o", ms=8, color=INK, ls="", zorder=6)[0],
        "badring": ax.plot([], [], marker="o", ms=26, mfc="none", mec=INK, mew=1.6, ls="", zorder=5)[0],
        "badlab": ax.text(0, 0, "", fontsize=10.5, color=INK, zorder=7, family=MONO, ha="right", va="top"),
        "title": ax.text(0.03, 0.965, label.upper(), transform=ax.transAxes, fontsize=12,
                         fontweight="semibold", va="top", family=SANS),
        "stat": ax.text(0.03, 0.905, "", transform=ax.transAxes, fontsize=10.5, va="top",
                        family=MONO, color=INK, linespacing=1.55),
        "verdict": ax.text(0.03, 0.66, "", transform=ax.transAxes, fontsize=13, va="top",
                           ha="left", fontweight="semibold"),
    }
    panels[n] = p

legend = [Line2D([], [], color=MUTED, lw=1.6, alpha=0.5, label="true path (RTK)"),
          Line2D([], [], marker="o", ms=10, mfc="none", mec=MUTED, mew=1.6, ls="", label="true position"),
          Line2D([], [], color=INK, marker="o", ms=7, lw=1.4, label="filter estimate"),
          Line2D([], [], marker="o", ms=13, color=INK, alpha=0.15, ls="", label="uncertainty, 1-sigma"),
          Line2D([], [], marker="o", ms=6, color=ACC, ls="", label="GPS fix accepted"),
          Line2D([], [], marker="x", ms=7, mew=1.3, color=REJ, ls="", label="GPS fix rejected")]
fig.legend(handles=legend, loc="center", bbox_to_anchor=(0.5, 0.2), ncol=6, frameon=False, fontsize=10.5)

# timeline strip: mission time, gaps, accept/reject marks per run, playhead
tl = fig.add_axes([0.04, 0.065, 0.92, 0.085], facecolor=BG)
tl.set_xlim(T0, T1); tl.set_ylim(-0.6, 1.6)
tl.set_yticks([1, 0]); tl.set_yticklabels(["active", "frozen"], fontsize=9, family=MONO)
tl.tick_params(axis="x", labelsize=9)
for lab in tl.get_xticklabels():
    lab.set_family(MONO)
for sp in ("top", "right", "left"):
    tl.spines[sp].set_visible(False)
ft = runs["out3_OFF"]["ft"]
for i in range(1, len(ft)):
    if ft[i] - ft[i - 1] > 10 and ft[i] > T0 and ft[i - 1] < T1:
        tl.axvspan(ft[i - 1], ft[i], color=LINE, alpha=0.7, lw=0, zorder=0)
for row, n in ((1, "out3_ON"), (0, "out3_OFF")):
    fw = [f for f in runs[n]["fixes"] if T0 <= f["t"] <= T1]
    tl.scatter([f["t"] for f in fw if f["accepted"]], [row] * sum(f["accepted"] for f in fw),
               marker="|", s=40, color=ACC, lw=0.6, zorder=2)
    rj = [f["t"] for f in fw if f["reason"] == "CHI2_FAILED"]
    tl.scatter(rj, [row] * len(rj), marker="|", s=40, color=REJ, lw=0.6, zorder=2)
tl.text(T0, 1.55, "mission time (s)   grey: no GPS signal", fontsize=9, color=MUTED, family=MONO, va="bottom")
play = tl.axvline(T0, color=INK, lw=1.4, zorder=3)
fig.text(0.96, 0.012, "Data: NCLT dataset, University of Michigan (ODbL). Filter: FusionCore by M. Kharwar.",
         fontsize=8.5, color=MUTED, ha="right", va="bottom")


def rgba(hexcol, alpha):
    h = hexcol.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha)


FIX_WINDOW = 45.0


def draw(v):
    t, speed = mission_time(v)
    txt = [c for c in CAPTIONS if c[0] <= t][-1][1]
    cap.set_text(txt)
    rate = "paused" if speed == 0 else (f"{speed:.0f}x speed" if speed >= 1.5 else
                                         f"{speed:.2f}x speed, slowed down")
    clock.set_text(f"t+{t:7.1f} s   {rate}")
    play.set_xdata([t, t])
    for n, p in panels.items():
        r = runs[n]
        ex, ey = step_xy(r["odom"], r["ot"], t)
        i0 = bisect.bisect_left(r["ot"], t - 90); i1 = bisect.bisect_right(r["ot"], t)
        tr = r["odom"][i0:i1] or [(t, ex, ey)]
        p["trail"].set_data([q[1] for q in tr], [q[2] for q in tr])
        p["est"].set_data([ex], [ey])
        s = sigma_at(r, t)
        p["circle"].center = (ex, ey); p["circle"].set_radius(s)
        j0 = bisect.bisect_left(r["ft"], t - FIX_WINDOW); j1 = bisect.bisect_right(r["ft"], t)
        win = r["fixes"][j0:j1]
        acc = [f for f in win if f["accepted"]]
        rej = [f for f in win if not f["accepted"]]
        for key, group, col in (("acc", acc, ACC), ("rej", rej, REJ)):
            p[key].set_offsets([(f["x"], f["y"]) for f in group] or [(math.nan, math.nan)])
            p[key].set_color([rgba(col, max(0.12, 1 - (t - f["t"]) / FIX_WINDOW)) for f in group] or [rgba(col, 0)])
        g = truth_at(t)
        p["true"].set_data(([g[0]], [g[1]]) if g else ([], []))
        # the corrupted first fix after the signal returns
        bad = next((f for f in r["fixes"] if f["t"] >= BAD_T - 0.2), None)
        if bad and BAD_T - 0.05 <= t <= BAD_T + 25:
            p["badring"].set_data([bad["x"]], [bad["y"]])
            p["badlab"].set_position((bad["x"] - 16, bad["y"] - 14))
            p["badlab"].set_text("first fix back:\n157 m off, accepted")
        else:
            p["badring"].set_data([], []); p["badlab"].set_text("")
        err = f"{math.hypot(ex - g[0], ey - g[1]):5.0f} m" if g else "  n/a (no RTK)"
        jl = bisect.bisect_right(r["ft"], t) - 1
        last = r["fixes"][jl] if jl >= 0 and t - r["ft"][jl] < 3.0 else None
        d2txt = (f"{last['d2']:7.2f} {'accepted' if last['accepted'] else 'rejected'}"
                 if last else "    n/a (no GPS)")
        p["stat"].set_text(f"error vs truth  {err}\nuncertainty     {s:5.1f} m\n"
                           f"latest fix d² {d2txt}\ngate threshold    16.27\n"
                           f"rejected in a row {streak(r, t):4d}")
        if t >= 3941.8:
            ok = n == "out3_OFF"
            p["verdict"].set_text("RECOVERED" if ok else "NEVER RECOVERS")
            p["verdict"].set_color(ACC if ok else REJ)
        else:
            p["verdict"].set_text("")


if a.preview:
    for v in a.preview:
        draw(v)
        out = os.path.splitext(a.out)[0] + f"_preview_{v:05.1f}.png"
        fig.savefig(out, dpi=a.dpi, facecolor=BG)
        print("wrote", out, "| sigma source:", {n: r["sigsrc"] for n, r in runs.items()})
else:
    writer = FFMpegWriter(fps=a.fps, codec="libx264", bitrate=-1,
                          extra_args=["-pix_fmt", "yuv420p", "-crf", "26", "-preset", "slow",
                                      "-movflags", "+faststart"])
    frames = int(DURATION * a.fps)
    with writer.saving(fig, a.out, dpi=a.dpi):
        for k in range(frames):
            draw(k / a.fps)
            writer.grab_frame(facecolor=BG)
    print(f"wrote {a.out}: {frames} frames, {DURATION:.1f} s | sigma source:",
          {n: r["sigsrc"] for n, r in runs.items()})
