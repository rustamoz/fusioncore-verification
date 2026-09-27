#!/usr/bin/env python3
"""Figures for the B_EWZ ablation: the 2x2 result, and the mechanism.
All values are measured; edit here if runs are repeated."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---- measured values -------------------------------------------------
ate      = {"no outage": (66.504, 60.723), "200 s outage": (294.611, 75.123)}
rl_ctrl  = [254.445, 253.812, 254.599, 254.557]
plr      = {"active\nno outage": 1.0024, "frozen\nno outage": 0.9974,
            "active\n200 s outage": 0.8757, "frozen\n200 s outage": 1.0152}
rpe      = {"active\nno outage": 26.511, "frozen\nno outage": 25.362,
            "active\n200 s outage": 20.077, "frozen\n200 s outage": 26.894}

ACT, FRZ, GREY = "#c26a00", "#1d9e75", "#9fb3c8"

# ---- Figure A: the 2x2 result ---------------------------------------
fig, ax = plt.subplots(figsize=(7.2, 4.8))
labels = list(ate.keys())
x = np.arange(len(labels)); w = 0.34
a = [ate[k][0] for k in labels]; f = [ate[k][1] for k in labels]
b1 = ax.bar(x - w/2, a, w, label="23rd state active", color=ACT)
b2 = ax.bar(x + w/2, f, w, label="23rd state frozen", color=FRZ)
for bars in (b1, b2):
    for r in bars:
        ax.annotate(f"{r.get_height():.1f} m",
                    xy=(r.get_x() + r.get_width()/2, r.get_height()),
                    xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9.5, fontweight="bold")
lo, hi = min(rl_ctrl), max(rl_ctrl)
ax.axhline(np.mean(rl_ctrl), color=GREY, ls="--", lw=1.3, zorder=0)
ax.fill_between([-0.6, 1.6], lo, hi, color=GREY, alpha=0.35, zorder=0)
ax.text(-0.54, np.mean(rl_ctrl) + 9,
        f"untouched control filter: {lo:.1f}–{hi:.1f} m across all four runs",
        ha="left", fontsize=8.5, color="#5f5e5a")
for i, k in enumerate(labels):
    d = ate[k][0] - ate[k][1]
    ax.annotate(f"frozen better\nby {d:.1f} m ({100*d/ate[k][0]:.0f}%)",
                xy=(i, max(ate[k]) + 26), ha="center", fontsize=9, color="#2c2c2a")
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("ATE RMSE, 3D (m)   lower is better")
ax.set_xlim(-0.6, 1.6); ax.set_ylim(0, 360)
ax.set_title("Freezing the 23rd state improves accuracy in both conditions",
             fontsize=11.5, pad=10)
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.18, lw=0.5)
fig.tight_layout(); fig.savefig("fig_ablation_result.png", dpi=200)
print("wrote fig_ablation_result.png")

# ---- Figure B: the mechanism ----------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.4))
keys = list(plr.keys())
cols = [ACT if k.startswith("active") else FRZ for k in keys]

v = [plr[k] for k in keys]
ax1.axhline(1.0, color="#5f5e5a", lw=1.1, ls="--", zorder=0)
bars = ax1.bar(range(len(keys)), v, 0.6, color=cols)
for i, r in enumerate(bars):
    ax1.annotate(f"{v[i]:.3f}", xy=(i, v[i]), xytext=(0, 4),
                 textcoords="offset points", ha="center",
                 fontsize=9.5, fontweight="bold")
ax1.annotate("12.4% short", xy=(2, 0.8757), xytext=(0, -46),
             textcoords="offset points", ha="center", fontsize=9.5,
             color="#a32d2d", fontweight="bold",
             arrowprops=dict(arrowstyle="->", color="#a32d2d", lw=1.1))
ax1.set_xticks(range(len(keys))); ax1.set_xticklabels(keys, fontsize=8.5)
ax1.set_ylim(0.82, 1.06); ax1.set_ylabel("path length ratio  (1.0 = correct)")
ax1.set_title("Estimated distance travelled", fontsize=10.5)
ax1.spines[["top", "right"]].set_visible(False)
ax1.grid(axis="y", alpha=0.18, lw=0.5)

v2 = [rpe[k] for k in keys]
bars = ax2.bar(range(len(keys)), v2, 0.6, color=cols)
for i, r in enumerate(bars):
    ax2.annotate(f"{v2[i]:.1f}", xy=(i, v2[i]), xytext=(0, 4),
                 textcoords="offset points", ha="center",
                 fontsize=9.5, fontweight="bold")
ax2.annotate("lowest of the four", xy=(2, 20.077), xytext=(0, -52),
             textcoords="offset points", ha="center", fontsize=9.5,
             color="#137a58", fontweight="bold",
             arrowprops=dict(arrowstyle="->", color="#137a58", lw=1.1))
ax2.set_xticks(range(len(keys))); ax2.set_xticklabels(keys, fontsize=8.5)
ax2.set_ylim(0, 34); ax2.set_ylabel("RPE at 10 m segments (m)")
ax2.set_title("Local accuracy over short segments", fontsize=10.5)
ax2.spines[["top", "right"]].set_visible(False)
ax2.grid(axis="y", alpha=0.18, lw=0.5)

fig.suptitle("Locally accurate, globally short: a scale error, not a local one",
             fontsize=11.5, y=0.99)
fig.tight_layout(); fig.savefig("fig_ablation_mechanism.png", dpi=200)
print("wrote fig_ablation_mechanism.png")
