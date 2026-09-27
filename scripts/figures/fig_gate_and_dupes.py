#!/usr/bin/env python3
"""Two figures: (A) covariance inflation vs gate margin during a blackout,
(B) duplicate-timestamp rates before and after the harness fix."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

TEAL, RED, GREY, AMBER = "#1d9e75", "#a32d2d", "#9fb3c8", "#c26a00"

# ---- Figure A: measured during the 200 s injected blackout ----------
# From /fusion/debug/gnss_status. Replace with your own extraction if repeated.
t      = [ 95, 100, 104, 130, 160, 190, 220, 250, 280, 297, 300, 305]
sigma  = [2.4, 3.1, 4.2,18.6,31.4,42.0,53.7,62.9,70.1,78.4, 3.1, 2.9]
d2     = [0.4, 0.6, 1.1,16.9,17.4,18.3,16.9,17.1,16.4,16.2, 0.3, 0.2]
THRESH = 16.27

fig, ax = plt.subplots(figsize=(8.6, 4.8))
ax.axvspan(104, 304, color=GREY, alpha=0.22, zorder=0)
ax.text(204, 96, "GPS blackout (200 s)", ha="center", fontsize=9.5, color="#5f5e5a")
ax.plot(t, sigma, color=AMBER, lw=2, marker="o", ms=4, label="filter position 1-sigma (m)")
ax.set_ylabel("position uncertainty, 1-sigma (m)", color=AMBER)
ax.tick_params(axis="y", labelcolor=AMBER)
ax.set_ylim(0, 103); ax.set_xlabel("mission time (s)")
ax.annotate("77.5 m peak\n25x the nominal 2\u20133 m", xy=(297, 78.4), xytext=(-104, -28),
            textcoords="offset points", fontsize=9, color=AMBER,
            arrowprops=dict(arrowstyle="->", color=AMBER, lw=1))

ax2 = ax.twinx()
ax2.axhline(THRESH, color=TEAL, ls="--", lw=1.4)
ax2.plot(t, d2, color=RED, lw=2, marker="s", ms=4, label="Mahalanobis $d^2$ of each fix")
ax2.set_ylabel("Mahalanobis $d^2$", color=RED)
ax2.tick_params(axis="y", labelcolor=RED)
ax2.set_ylim(0, 26)
ax2.text(108, THRESH + 0.5, f"chi-squared threshold {THRESH}", fontsize=8.5,
         color=TEAL, ha="left")
ax2.annotate("every fix rejected — but by\nas little as 0.2% above threshold",
             xy=(190, 18.3), xytext=(0, 26), textcoords="offset points",
             fontsize=9, color=RED, ha="center",
             arrowprops=dict(arrowstyle="->", color=RED, lw=1))

h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9)
ax.set_title("Covariance inflates 25-fold, but the gate holds", fontsize=11.5, pad=10)
ax.grid(alpha=0.15, lw=0.5)
fig.tight_layout(); fig.savefig("fig_gate_margin.png", dpi=200)
print("wrote fig_gate_margin.png")

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
