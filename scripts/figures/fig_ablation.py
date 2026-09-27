#!/usr/bin/env python3
"""Figure for the B_EWZ ablation: the 2x2 result (report section 4).
All values are measured; edit here if runs are repeated."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---- measured values -------------------------------------------------
ate      = {"no outage": (66.504, 60.723), "200 s outage": (294.611, 75.123)}
rl_ctrl  = [254.445, 253.812, 254.599, 254.557]

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
ax.set_title("Freezing the 23rd state gave lower error in both conditions",
             fontsize=11.5, pad=10)
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.18, lw=0.5)
fig.tight_layout(); fig.savefig("fig_ablation_result.png", dpi=200)
print("wrote fig_ablation_result.png")
