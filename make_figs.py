"""
Generate publication-quality figures for paper.md.

Usage:
  python make_figs.py --run-dir results/run_YYYYMMDD_HHMMSS

Writes to ./fig/:
  fig1_heatmap.png        (hero) unflagged success rate, config x regime
  fig2_frontier.png       capability-evasion scatter
  fig3_monitor_effect.png sonnet-sonnet, haiku vs opus monitor
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

from analyze import load_trials, summarize, wilson_ci


# Typography
plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.titlesize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


# Rescaled colormap: 0 to 0.6 instead of 0 to 1 so that 44% and 55% pop
SUCCESS_CMAP = LinearSegmentedColormap.from_list(
    "success",
    [(0.98, 0.96, 0.94), (0.95, 0.77, 0.30), (0.85, 0.33, 0.10)],
    N=256,
)


def fig1_heatmap(valid, out: Path):
    # Order configs by max unflagged_succ across regimes, descending
    configs = sorted({t["config"] for t in valid})
    regimes = ["zero_shot", "few_shot", "strategy_first"]

    mat = np.full((len(configs), len(regimes)), np.nan)
    ns = np.zeros_like(mat, dtype=int)
    for i, cfg in enumerate(configs):
        for j, rgm in enumerate(regimes):
            rows = [t for t in valid if t["config"] == cfg and t["regime"] == rgm]
            if rows:
                s = summarize(rows)
                mat[i, j] = s["unflagged_succ"]
                ns[i, j] = s["n"]

    # Sort rows by strategy_first column, descending
    order = np.argsort(-mat[:, 2])
    mat = mat[order]
    ns = ns[order]
    configs = [configs[i] for i in order]

    fig, ax = plt.subplots(figsize=(6.8, 0.48 * len(configs) + 1.4))
    im = ax.imshow(mat, cmap=SUCCESS_CMAP, vmin=0, vmax=0.6, aspect="auto")

    ax.set_xticks(range(len(regimes)))
    ax.set_xticklabels([r.replace("_", "-") for r in regimes])
    ax.set_yticks(range(len(configs)))
    ax.set_yticklabels([c.replace("|", " / ") for c in configs], fontsize=9)

    for i in range(len(configs)):
        for j in range(len(regimes)):
            v = mat[i, j]
            if np.isnan(v):
                continue
            txt_color = "white" if v > 0.35 else "#222"
            ax.text(j, i, f"{v*100:.0f}%",
                    ha="center", va="center", fontsize=10,
                    color=txt_color, fontweight="bold")

    ax.set_xlabel("Regime", fontsize=10, labelpad=8)
    ax.set_title("Unflagged success rate by configuration and regime",
                 pad=10, fontsize=11)
    cbar = fig.colorbar(im, ax=ax, shrink=0.78, pad=0.02)
    cbar.set_label("Unflagged success", fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig2_frontier(valid, out: Path):
    """Scatter of (flagged_rate, accuracy) per (config, regime) cell."""
    cells = defaultdict(list)
    for t in valid:
        cells[(t["config"], t["regime"])].append(t)

    palette = {
        "zero_shot":      "#9e9e9e",
        "few_shot":       "#3b6ab6",
        "strategy_first": "#c03d2a",
    }
    marker_order = ["zero_shot", "few_shot", "strategy_first"]

    fig, ax = plt.subplots(figsize=(7.4, 5.6))

    # Iso-curves for reference: unflag = acc * (1 - flagged), so acc = target/(1-flagged)
    fx = np.linspace(0.001, 0.99, 300)
    for target, color in [(0.25, "#cccccc"), (0.50, "#aaaaaa"), (0.75, "#888888")]:
        fy = target / (1 - fx)
        m = (fy >= 0) & (fy <= 1)
        ax.plot(fx[m], fy[m], ls="--", lw=0.7, color=color, alpha=0.7, zorder=1)
        # Label near left edge
        xlab = 0.02
        ylab = target / (1 - xlab)
        if 0 < ylab < 0.98:
            ax.text(xlab, ylab + 0.015,
                    f"unflagged succ = {target:.2f}",
                    fontsize=7.5, color="#666", alpha=0.9, zorder=1)

    # Points by regime
    for regime in marker_order:
        xs, ys, sizes, annotate = [], [], [], []
        for (cfg, r), rows in cells.items():
            if r != regime:
                continue
            s = summarize(rows)
            xs.append(s["flagged_rate"])
            ys.append(s["accuracy"])
            sizes.append(60 + s["n"] * 3)
            annotate.append((s["accuracy"], s["flagged_rate"], cfg))
        ax.scatter(xs, ys, s=sizes, color=palette[regime],
                   alpha=0.82, edgecolor="black", linewidth=0.7,
                   label=regime.replace("_", "-"), zorder=3)

    # Annotate strategy_first sonnet cells
    callouts = [
        ("sonnet|sonnet|haiku", "strategy_first", "sonnet-sonnet vs haiku", (0.06, 0.66)),
        ("sonnet|sonnet|opus",  "strategy_first", "sonnet-sonnet vs opus",  (0.30, 0.56)),
        ("sonnet|haiku|haiku",  "strategy_first", "sonnet-haiku vs haiku",  (0.005, 0.44)),
    ]
    for cfg, regime, label, tgt in callouts:
        rows = cells.get((cfg, regime), [])
        if not rows:
            continue
        s = summarize(rows)
        x, y = s["flagged_rate"], s["accuracy"]
        ax.annotate(label, xy=(x, y), xytext=tgt,
                    fontsize=8.5,
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="#333",
                                    connectionstyle="arc3,rad=0.1"),
                    zorder=4)

    ax.set_xlim(-0.02, 1.0)
    ax.set_ylim(-0.02, 1.0)
    ax.set_xlabel("Monitor flagged rate (lower = better evasion)")
    ax.set_ylabel("Receiver accuracy (higher = better transmission)")
    ax.set_title("Capability-evasion frontier: transmission vs detection", pad=10)
    leg = ax.legend(title="Regime", loc="upper right", frameon=True,
                    fontsize=9, title_fontsize=9)
    leg.get_frame().set_edgecolor("#cccccc")

    fig.tight_layout()
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig3_monitor_effect(valid, out: Path):
    """Monitor-scaling decomposition: sonnet-sonnet under haiku vs opus monitor."""
    targets = [
        ("sonnet|sonnet|haiku", "strategy_first", "Haiku monitor"),
        ("sonnet|sonnet|opus",  "strategy_first", "Opus monitor"),
    ]

    rows_per = []
    for cfg, rgm, label in targets:
        rows = [t for t in valid if t["config"] == cfg and t["regime"] == rgm]
        rows_per.append((label, summarize(rows)))

    labels = [r[0] for r in rows_per]
    acc   = [r[1]["accuracy"]       for r in rows_per]
    flag  = [r[1]["flagged_rate"]   for r in rows_per]
    ufs   = [r[1]["unflagged_succ"] for r in rows_per]

    x = np.arange(len(labels))
    w = 0.26
    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    b1 = ax.bar(x - w, acc,  w, label="Sender accuracy",      color="#3b6ab6", alpha=0.92)
    b2 = ax.bar(x,     flag, w, label="Monitor flagged rate", color="#c03d2a", alpha=0.92)
    b3 = ax.bar(x + w, ufs,  w, label="Unflagged success",    color="#3f8a4c", alpha=0.92)

    for bars in (b1, b2, b3):
        for b in bars:
            v = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, v + 0.015,
                    f"{v*100:.1f}%", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, max(max(acc), max(flag), max(ufs)) * 1.28)
    ax.set_ylabel("Rate")
    ax.set_title("Monitor scaling effect (sonnet-sonnet sender, strategy-first)", pad=10)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    p.add_argument("--out-dir", default="fig")
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    trials = load_trials(run_dir)
    valid = [t for t in trials if not t.get("error")]
    print(f"Loaded {len(valid)} valid trials from {run_dir}")

    fig1_heatmap(valid,        out_dir / "fig1_heatmap.png")
    fig2_frontier(valid,       out_dir / "fig2_frontier.png")
    fig3_monitor_effect(valid, out_dir / "fig3_monitor_effect.png")
    print(f"Saved 3 publication figures to {out_dir}/")


if __name__ == "__main__":
    main()
