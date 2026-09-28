#!/usr/bin/env python3
"""Figure: rejected fixes were as accurate as accepted ones (report section 5).

Cumulative distribution of each fix's error against RTK ground truth,
split by the gate's decision. Reads CSVs from extract_figdata.py.

    python3 fig_fix_accuracy.py --data figdata --out fig_fix_accuracy.png
"""
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _figdata import load_status

RUNS = [("noout_ON", "23rd state active, no outage"),
        ("out3_ON",  "23rd state active, 200 s outage (never recovers)")]
TEAL, RED = "#1d9e75", "#a32d2d"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--data", default="figdata")
ap.add_argument("--xmax", type=float, default=20.0)
ap.add_argument("--out", default="fig_fix_accuracy.png")
a = ap.parse_args()

fig, axes = plt.subplots(1, len(RUNS), figsize=(10.4, 4.4), sharey=True)
for ax, (name, label) in zip(axes, RUNS):
    st = load_status(a.data, name)
    groups = [("accepted", TEAL, sorted(s["err"] for s in st if s["accepted"] and s["err"] is not None)),
              ("rejected", RED, sorted(s["err"] for s in st
                                       if s["reason"] == "CHI2_FAILED" and s["err"] is not None))]
    for lab, col, v in groups:
        if not v:
            continue
        n = len(v); med = v[n // 2]
        ax.step(v, [(i + 1) / n for i in range(n)], where="post", color=col, lw=1.8,
                label=f"{lab}: n={n:,}, median {med:.1f} m")
        ax.axvline(med, color=col, ls=":", lw=1)
    ax.set_xlim(0, a.xmax); ax.set_ylim(0, 1.01)
    ax.set_title(label, fontsize=10)
    ax.set_xlabel("fix error against RTK ground truth (m)")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.grid(alpha=0.15, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("fraction of fixes")
fig.text(0.5, 0.005, "For scale: the corrupted fixes on 2012-08-20 were about 820 to 840 m from the truth.",
         ha="center", fontsize=9, color="#5f5e5a")
fig.suptitle("The fixes the gate rejected were ordinary GPS, within a few metres of the truth",
             fontsize=12, y=0.99)
fig.tight_layout(rect=(0, 0.04, 1, 0.95))
fig.savefig(a.out, dpi=200)
print(f"wrote {a.out}")
