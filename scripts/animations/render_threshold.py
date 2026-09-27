#!/usr/bin/env python3
"""Render the threshold-sweep animation (report section 3 and section 5).

A cursor sweeps the time since the last accepted fix from 0.1 s to 1000 s.
The proposed check allows 20 m/s times that time, so the distance it will
accept grows with the gap. Three real fixes appear as the cursor reaches
them. All values are measured; see results/benchmark_tables.md.

    python3 render_threshold.py --fonts fonts --out threshold.mp4
    python3 render_threshold.py --fonts fonts --out threshold.mp4 --preview 2 5 9 13 17
"""
import argparse
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.animation import FFMpegWriter

BG, INK, MUTED, LINE, ACC = "#F5F5F2", "#111111", "#6B6B67", "#D9D9D4", "#1E7F4F"
REJ = "#A32D2D"
SANS, MONO = "Geist", "JetBrains Mono"
LIMIT = 20.0                                   # m/s, the pre-gate threshold

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--fonts", default="fonts")
ap.add_argument("--out", default="threshold.mp4")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--dpi", type=int, default=100)
ap.add_argument("--preview", type=float, nargs="*")
a = ap.parse_args()
for f in os.listdir(a.fonts):
    if f.endswith(".ttf"):
        font_manager.fontManager.addfont(os.path.join(a.fonts, f))
plt.rcParams.update({"font.family": SANS, "text.color": INK, "axes.edgecolor": LINE,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})

# events along the sweep: (time since last accepted fix, distance or None, label lines, caption)
EVENTS = [
    (0.2, None, None,
     "Between normal fixes, 0.2 s apart, it allows 4 m of movement."),
    (111.8, 166.0, ["2012-01-08, t+3493 s", "157 m from the truth", "1.48 m/s: passes"],
     "After a real 112 s signal loss, a fix 157 m from the truth implies 1.48 m/s. It passes."),
    (211.19, 713.8, ["2012-08-20, t+3960 s", "fix the paper cites", "3.4 m/s: passes"],
     "After 211 s, the fix the paper cites implies 3.4 m/s, not 3,400. It passes."),
]
FIXES = [e for e in EVENTS if e[1] is not None]
X0, X1 = 0.1, 1000.0
SWEEP, HOLD_EACH, INTRO, OUTRO = 10.0, 5.5, 7.5, 7.5


def u_of(x):
    return (math.log10(x) - math.log10(X0)) / (math.log10(X1) - math.log10(X0))


# timeline: intro, sweep with a hold at each fix, outro
events = sorted(EVENTS, key=lambda f: f[0])
segs, v = [], INTRO
u_prev = 0.0
for f in events:
    u = u_of(f[0]); dur = SWEEP * (u - u_prev)
    segs.append((v, v + dur, u_prev, u)); v += dur
    segs.append((v, v + HOLD_EACH, u, u)); v += HOLD_EACH
    u_prev = u
dur = SWEEP * (1 - u_prev)
segs.append((v, v + dur, u_prev, 1.0)); v += dur
DURATION = v + OUTRO


def cursor(vt):
    if vt < INTRO:
        return None
    for s0, s1, u0, u1 in segs:
        if s0 <= vt < s1:
            return 10 ** (math.log10(X0) + (u0 + (u1 - u0) * (vt - s0) / (s1 - s0))
                          * (math.log10(X1) - math.log10(X0)))
    return X1


fig = plt.figure(figsize=(16, 9), dpi=a.dpi, facecolor=BG)
fig.text(0.06, 0.955, "THE PROPOSED VELOCITY CHECK  /  20 m/s LIMIT", fontsize=10, color=MUTED,
         family=MONO, va="center")
cap = fig.text(0.06, 0.905, "", fontsize=17, va="center")
readout = fig.text(0.94, 0.905, "", fontsize=12, color=MUTED, ha="right", va="center", family=MONO)
ax = fig.add_axes([0.08, 0.13, 0.86, 0.71], facecolor=BG)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(X0, X1); ax.set_ylim(1, 30000)
ax.set_xlabel("time since the last accepted GPS fix (s)", fontsize=12)
ax.set_ylabel("distance of the new fix from it (m)", fontsize=12)
for lab in ax.get_xticklabels() + ax.get_yticklabels():
    lab.set_family(MONO); lab.set_fontsize(10)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.grid(True, which="major", color=LINE, lw=0.6)
xs = [10 ** (math.log10(X0) + k * (math.log10(X1) - math.log10(X0)) / 400) for k in range(401)]
ax.fill_between(xs, [LIMIT * x for x in xs], 1e6, color=REJ, alpha=0.05, lw=0)
ax.plot(xs, [LIMIT * x for x in xs], color=LINE, lw=1.2, ls="--")
ax.text(0.14, 9000, "fails the check: faster than 20 m/s", fontsize=11, color=REJ, family=MONO)
ax.text(120, 1.6, "passes the check", fontsize=11, color=ACC, family=MONO)
drawn = ax.plot([], [], color=INK, lw=2.2)[0]
cur = ax.axvline(X0, color=INK, lw=1, alpha=0.0)
budget = ax.plot([], [], marker="o", ms=7, color=INK, ls="")[0]
blab = ax.text(0, 0, "", fontsize=10.5, family=MONO, color=INK, va="bottom", ha="right")
arts = []
for gx, gy, lines, _ in FIXES:
    caught = gy / gx > LIMIT
    col = REJ if caught else ACC
    m = ax.plot([gx], [gy], marker="x" if caught else "o", ms=13, mew=2.4, color=col, ls="", alpha=0)[0]
    # below-right of the point: empty space, well clear of the threshold line
    t = ax.text(gx * 1.3, gy * 0.8, "\n".join(lines), fontsize=10.5, family=MONO,
                color=col, va="top", ha="left", alpha=0, linespacing=1.5)
    arts.append((gx, m, t))
fig.text(0.94, 0.02, "Values from the NCLT dataset (University of Michigan, ODbL); see results/benchmark_tables.md.",
         fontsize=8.5, color=MUTED, ha="right")

INTRO_CAP = ("The proposed check divides a new fix's distance by the time since the last "
             "accepted fix, and rejects anything faster than 20 m/s.")
SWEEP_CAP = "As the gap lengthens, the distance it will accept grows with it."
OUTRO_CAP = "The allowance grows with the gap. After 211 s it is 4.2 km, so the longer the blackout, the less it can catch."


def draw(vt):
    x = cursor(vt)
    if x is None:
        cap.set_text(INTRO_CAP); readout.set_text("")
        drawn.set_data([], []); budget.set_data([], []); blab.set_text(""); cur.set_alpha(0)
        for _, m, t in arts:
            m.set_alpha(0); t.set_alpha(0)
        return
    xx = [p for p in xs if p <= x] + [x]
    drawn.set_data(xx, [LIMIT * p for p in xx])
    cur.set_xdata([x, x]); cur.set_alpha(0.35)
    budget.set_data([x], [LIMIT * x])
    blab.set_position((x / 1.15, LIMIT * x * 1.25))
    blab.set_text(f"allows {LIMIT * x:,.0f} m" if LIMIT * x >= 10 else f"allows {LIMIT * x:.1f} m")
    readout.set_text(f"gap {x:8.2f} s   allowance {LIMIT * x:9,.1f} m")
    reached = [e for e in EVENTS if e[0] <= x * 1.0001]
    if not reached:
        txt = INTRO_CAP                          # no flash before the first event
    elif reached[-1] is EVENTS[-1] or x <= reached[-1][0] * 3.2:
        txt = reached[-1][3]                     # the last event's caption runs into the outro
    else:
        txt = SWEEP_CAP
    if vt >= DURATION - OUTRO:
        txt = OUTRO_CAP
        readout.set_text("")
    cap.set_text(txt)
    for gx, m, t in arts:
        on = gx <= x * 1.0001
        m.set_alpha(1 if on else 0); t.set_alpha(1 if on else 0)


if a.preview:
    for vt in a.preview:
        draw(vt)
        out = os.path.splitext(a.out)[0] + f"_preview_{vt:05.1f}.png"
        fig.savefig(out, dpi=a.dpi, facecolor=BG); print("wrote", out)
else:
    writer = FFMpegWriter(fps=a.fps, codec="libx264", bitrate=-1,
                          extra_args=["-pix_fmt", "yuv420p", "-crf", "26", "-preset", "slow",
                                      "-movflags", "+faststart"])
    frames = int(DURATION * a.fps)
    with writer.saving(fig, a.out, dpi=a.dpi):
        for k in range(frames):
            draw(k / a.fps); writer.grab_frame(facecolor=BG)
    print(f"wrote {a.out}: {frames} frames, {DURATION:.1f} s")
