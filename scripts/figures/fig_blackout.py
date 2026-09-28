#!/usr/bin/env python3
"""Figure: uncertainty growth in a blackout, then good fixes rejected (report section 3).

Reads CSVs from extract_figdata.py for one run with an injected outage.

    python3 fig_blackout.py --data figdata --run blackout_spike_ON --out fig_blackout.png
"""
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _figdata import load_status, load_health, gaps

AMBER, RED, GREY, TEAL, INK = "#c26a00", "#a32d2d", "#9fb3c8", "#1d9e75", "#2c2c2a"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--data", default="figdata")
ap.add_argument("--run", default="blackout_spike_ON")
ap.add_argument("--threshold", type=float, default=16.27)
ap.add_argument("--out", default="fig_blackout.png")
a = ap.parse_args()

st, he = load_status(a.data, a.run), load_health(a.data, a.run)
g0, g1 = max(gaps(st), key=lambda g: g[1] - g[0])           # the injected outage
after = [s for s in st if s["t"] >= g1]
first_acc = next(s for s in after if s["accepted"])
rej = [s for s in after if s["t"] < first_acc["t"] and s["reason"] == "CHI2_FAILED"]
pre = sorted(h[1] for h in he if h[0] < g0)
base = pre[len(pre) // 2]
peak = max((h for h in he if g0 <= h[0] <= first_acc["t"]), key=lambda h: h[1])
peak_sig = max(peak[1], max((s["sigma"] for s in rej), default=0))
lo, hi = g0 - 45, first_acc["t"] + 30

fig, ax = plt.subplots(figsize=(9.6, 5.0))
ax.axvspan(g0, g1, color=GREY, alpha=0.3, lw=0, zorder=0)
ax.text((g0 + g1) / 2, 0.97, f"no GPS: {g1 - g0:.0f} s blackout", transform=ax.get_xaxis_transform(),
        ha="center", va="top", fontsize=9.5, color="#5f5e5a")
hw = [h for h in he if lo <= h[0] <= hi]
ax.plot([h[0] for h in hw], [h[1] for h in hw], color=AMBER, lw=2, zorder=3,
        label="position uncertainty, 1-sigma (left axis)")
ax.set_ylabel("position 1-sigma (m)", color=AMBER)
ax.tick_params(axis="y", labelcolor=AMBER)
ax.set_ylim(0, peak_sig * 1.34)
ax.set_xlim(lo, hi)
ax.set_xlabel("mission time (s)")
ax.plot([g0, peak[0]], [peak_sig, peak_sig], color=AMBER, ls=":", lw=1.1, zorder=2)
ax.text(g0 + 3, peak_sig + 1.2,
        f"peak {peak_sig:.1f} m, {peak_sig / base:.0f}x the {base:.1f} m before the blackout",
        fontsize=9, color=AMBER, va="bottom")

ax2 = ax.twinx()
ax2.set_yscale("log")
win = [s for s in st if lo <= s["t"] <= hi]
ax2.scatter([s["t"] for s in win if s["accepted"]], [max(s["d2"], 0.01) for s in win if s["accepted"]],
            s=10, color=TEAL, alpha=0.6, zorder=4, label="fix accepted (right axis)")
ax2.scatter([s["t"] for s in rej], [s["d2"] for s in rej], s=16, color=RED, zorder=5,
            label="fix rejected (right axis)")
ax2.axhline(a.threshold, color=INK, ls="--", lw=1)
ax2.text(g0 + 4, a.threshold * 1.18, f"gate threshold {a.threshold}", ha="left", fontsize=8.5, color=INK)
ax2.set_ylabel("Mahalanobis $d^2$ of each fix")
ax2.set_ylim(0.01, 1000)
# separate the injected spike from genuine fixes: by ground truth when the CSV has it,
# otherwise by a d2 far above the threshold
def is_spike(f):
    return (f["err"] > 100.0) if f["err"] is not None else (f["d2"] > 3 * a.threshold)
spikes = [f for f in rej if is_spike(f)]
good = [f for f in rej if not is_spike(f)]
for f in spikes:
    ax2.annotate(f"injected spike, rejected\n" + (f"{f['err']:.0f} m off, " if f["err"] is not None else "")
                 + f"$d^2$ {f['d2']:.1f}",
                 xy=(f["t"], f["d2"]), xytext=(g1 - 3, peak_sig + 14.5), textcoords=ax.transData,
                 ha="right", va="bottom", fontsize=9, color=RED,
                 arrowprops=dict(arrowstyle="->", color=RED, lw=1))
ax2.annotate(f"{len(good)} good fixes rejected\n($d^2$ {min(s['d2'] for s in good):.2f} to "
             f"{max(s['d2'] for s in good):.2f})",
             xy=(good[len(good) // 2]["t"], good[len(good) // 2]["d2"]),
             xytext=(g1 - 3, peak_sig + 2.5), textcoords=ax.transData,
             ha="right", va="bottom", fontsize=9, color=RED,
             arrowprops=dict(arrowstyle="->", color=RED, lw=1))
ax2.annotate(f"first accepted: $d^2$ = {first_acc['d2']:.2f}", xy=(first_acc["t"], first_acc["d2"]),
             xytext=(-60, -48), textcoords="offset points", ha="right", fontsize=9, color=TEAL,
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1))

h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=8.5)
ax.grid(alpha=0.15, lw=0.5)
ax.set_title("After a blackout the gate rejects good fixes until one scrapes under the threshold",
             fontsize=11.5, pad=10)
fig.tight_layout()
fig.canvas.draw(); _r = fig.canvas.get_renderer(); _ab = ax.get_window_extent(_r)
for _t in ax.texts + ax2.texts:
    _b = _t.get_window_extent(_r)
    if _t.get_text() and (_b.x0 < _ab.x0 - 1 or _b.x1 > _ab.x1 + 1 or _b.y1 > _ab.y1 + 1):
        raise SystemExit(f"label outside the axes: {_t.get_text()!r}")
fig.savefig(a.out, dpi=200)
print(f"wrote {a.out}; baseline {base:.2f} m, peak {peak_sig:.2f} m, {len(rej)} rejected "
      f"({len(spikes)} spike, {len(good)} good), first accept d2 {first_acc['d2']:.2f}")
