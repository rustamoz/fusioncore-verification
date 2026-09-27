#!/usr/bin/env python3
"""Figure: GPS lockout in all four ablation runs (report section 5).

Reads CSVs from extract_figdata.py.

    python3 fig_lockout.py --data figdata --out fig_lockout.png
"""
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from _figdata import load_status, load_health, gaps, episodes

RUNS = [("noout_ON",  "23rd state active, no outage"),
        ("noout_OFF", "23rd state frozen, no outage"),
        ("out3_ON",   "23rd state active, 200 s outage"),
        ("out3_OFF",  "23rd state frozen, 200 s outage")]
AMBER, RED, GREY, INK = "#c26a00", "#a32d2d", "#9fb3c8", "#2c2c2a"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--data", default="figdata")
ap.add_argument("--out", default="fig_lockout.png")
a = ap.parse_args()

fig, axes = plt.subplots(len(RUNS), 1, figsize=(10.4, 8.8), sharex=True)
starts = []
for ax, (name, label) in zip(axes, RUNS):
    st, he = load_status(a.data, name), load_health(a.data, name)
    for g0, g1 in gaps(st):
        ax.axvspan(g0, g1, color=GREY, alpha=0.35, lw=0, zorder=0)
    ax.plot([h[0] for h in he], [max(h[1], 0.5) for h in he], color=AMBER, lw=1.1, zorder=2)
    rej = [s["t"] for s in st if s["reason"] == "CHI2_FAILED"]
    ax.scatter(rej, [0.64] * len(rej), marker="|", s=70, color=RED, lw=0.5, zorder=3)
    ax.set_yscale("log"); ax.set_ylim(0.5, 4000)
    ax.set_ylabel("sigma (m)", fontsize=9)
    ax.grid(alpha=0.15, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    eps = episodes(st)
    longest = max(eps, key=lambda e: e["n"])
    starts.append(longest["start"])
    ax.text(0.005, 0.95, label, transform=ax.transAxes,
            fontsize=9.5, fontweight="bold", color=INK, va="top")
    ax.text(0.005, 0.77, f"{len(rej):,} of {len(st):,} fixes rejected "
            f"({100 * len(rej) / len(st):.1f}%)", transform=ax.transAxes,
            fontsize=8.5, color=INK, va="top")
    if longest["open"]:
        msg = f"locked out to the end of the run: {longest['n']:,} consecutive rejections"
        col = RED
    else:
        msg = (f"longest lockout: {longest['n']:,} rejections, "
               f"t+{longest['start']:.0f} to {longest['end']:.0f} s")
        col = INK
    ax.text(0.995, 0.95, msg, transform=ax.transAxes, fontsize=9, color=col,
            ha="right", va="top", fontweight="bold" if longest["open"] else "normal")

t_lock = min(starts)
for ax in axes:
    ax.axvline(t_lock, color=INK, ls="--", lw=0.9, zorder=1)
axes[0].annotate(f"lockout begins, t+{t_lock:.0f} s", xy=(t_lock, 1.0),
                 xycoords=("data", "axes fraction"), xytext=(0, 3),
                 textcoords="offset points", ha="center", va="bottom",
                 fontsize=8.5, color=INK, annotation_clip=False)
axes[-1].set_xlabel("mission time (s)")
handles = [Line2D([], [], color=AMBER, lw=1.4, label="filter position uncertainty, 1-sigma"),
           Line2D([], [], color=RED, marker="|", ls="", ms=10, label="GPS fix rejected by the chi-squared gate"),
           Patch(color=GREY, alpha=0.5, label="no GPS fixes (gaps in the data, or the injected outage)")]
fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=9,
           bbox_to_anchor=(0.5, 0.0))
fig.suptitle("Every run locks out of GPS after the same natural gap. One never recovers.",
             fontsize=12, y=0.995)
fig.tight_layout(rect=(0, 0.035, 1, 0.975))
fig.savefig(a.out, dpi=200)
print(f"wrote {a.out}; lockout starts t+{t_lock:.0f} s")
