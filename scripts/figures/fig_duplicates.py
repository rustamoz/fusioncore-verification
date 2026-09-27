#!/usr/bin/env python3
"""Figure: duplicate-timestamp rates before and after the harness fix (report section 6)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

TEAL, RED, GREY, AMBER = "#1d9e75", "#a32d2d", "#9fb3c8", "#c26a00"

# ---- Figure B: duplicate rates --------------------------------------
runs  = ["2012-01-08\n3x", "2012-01-08\n1x", "2012-08-20", "ablation\nactive", "60 s test\nafter fix"]
total = [202659, 939242, 558396, 242195, 1234]
uniq  = [126658, 432262, 117813,  11995, 1234]
pct   = [100*(t-u)/t for t, u in zip(total, uniq)]

def k(n):
    return f"{n/1000:.0f}k" if n >= 10000 else f"{n:,}"

fig, ax = plt.subplots(figsize=(8.6, 4.6))
cols = [RED]*4 + [TEAL]
bars = ax.bar(range(len(runs)), pct, 0.62, color=cols)
for i, r in enumerate(bars):
    ax.annotate(f"{pct[i]:.1f}%", xy=(i, pct[i]), xytext=(0, 5),
                textcoords="offset points", ha="center",
                fontsize=11, fontweight="bold")
    inside = pct[i] > 20
    ax.annotate(f"{k(total[i])} to {k(uniq[i])}", xy=(i, pct[i]),
                xytext=(0, -18 if inside else 22),
                textcoords="offset points", ha="center", fontsize=8.5,
                color=("white" if inside else "#2c2c2a"))
ax.set_xticks(range(len(runs)))
ax.set_xticklabels(runs, fontsize=9)
ax.set_ylabel("recorded poses carrying a duplicate timestamp (%)")
ax.set_ylim(0, 112)
ax.set_title("Recorded odometry was mostly duplicates until the harness was fixed",
             fontsize=11.5, pad=10)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.18, lw=0.5)
fig.tight_layout(); fig.savefig("fig_duplicates.png", dpi=200)
print("wrote fig_duplicates.png")
