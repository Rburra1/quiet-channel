"""
Visualizations for the steganographic collusion benchmark.

Generates:
  01_overall.png            bar of accuracy / flagged / unflag_succ
  02_by_config.png          per-config bars with CIs
  03_by_regime.png          regime comparison across configs
  04_by_tier.png            tier comparison
  05_frontier_scatter.png   accuracy vs flagged_rate (capability-evasion frontier)
  06_regime_heatmap.png     unflagged_succ heatmap (config x regime)
  07_monitor_effect.png     how monitor strength changes outcomes
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze import load_trials, summarize, group_by, wilson_ci


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def plot_overall(valid, out: Path):
    s = summarize(valid)
    metrics = [
        ("accuracy", s["accuracy"], s["accuracy_ci"]),
        ("flagged_rate", s["flagged_rate"], s["flagged_rate_ci"]),
        ("unflagged_succ", s["unflagged_succ"], s["unflagged_succ_ci"]),
    ]
    labels = [m[0] for m in metrics]
    vals = [m[1] for m in metrics]
    errs = [[m[1] - m[2][0] for m in metrics], [m[2][1] - m[1] for m in metrics]]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, vals, yerr=errs, capsize=5,
                  color=["#4a7abc", "#c9503b", "#4aa56b"], alpha=0.85)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Rate")
    ax.set_title(f"Overall (n={s['n']})  Wilson 95% CI")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v*100:.1f}%",
                ha="center", fontsize=10)
    ax.axhline(0.5, color="grey", lw=0.5, ls="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def plot_group_bars(valid, key_fn, title, out: Path, sort_by="unflagged_succ"):
    groups = defaultdict(list)
    for t in valid:
        groups[key_fn(t)].append(t)
    items = [(k, summarize(v)) for k, v in groups.items()]
    items.sort(key=lambda x: -x[1][sort_by])
    labels = [k for k, _ in items]
    acc = [s["accuracy"] for _, s in items]
    flag = [s["flagged_rate"] for _, s in items]
    ufs = [s["unflagged_succ"] for _, s in items]
    ns = [s["n"] for _, s in items]

    x = np.arange(len(labels))
    w = 0.27
    fig, ax = plt.subplots(figsize=(max(8, 0.7 * len(labels) + 3), 4.5))
    ax.bar(x - w, acc, w, label="accuracy", color="#4a7abc", alpha=0.85)
    ax.bar(x, flag, w, label="flagged", color="#c9503b", alpha=0.85)
    ax.bar(x + w, ufs, w, label="unflagged success", color="#4aa56b", alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{lab}\n(n={n})" for lab, n in zip(labels, ns)],
                      rotation=35, ha="right", fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Rate")
    ax.axhline(0.5, color="grey", lw=0.5, ls="--", alpha=0.5)
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def plot_frontier(valid, out: Path):
    """Scatter of accuracy vs flagged_rate per (config, regime) cell."""
    cells = defaultdict(list)
    for t in valid:
        cells[(t["config"], t["regime"])].append(t)

    regimes = sorted({r for _, r in cells.keys()})
    palette = {"zero_shot": "#888888", "few_shot": "#4a7abc", "strategy_first": "#c9503b"}

    fig, ax = plt.subplots(figsize=(8, 6))
    for regime in regimes:
        xs, ys, sz, labels = [], [], [], []
        for (cfg, r), rows in cells.items():
            if r != regime:
                continue
            s = summarize(rows)
            xs.append(s["flagged_rate"])
            ys.append(s["accuracy"])
            sz.append(30 + s["n"] * 3)
            labels.append(cfg.replace("|", "\n"))
        ax.scatter(xs, ys, s=sz, color=palette.get(regime, "grey"),
                   alpha=0.7, edgecolor="k", linewidth=0.6, label=regime)

    # Reference lines
    ax.axvline(0.5, color="grey", lw=0.5, ls=":", alpha=0.4)
    ax.axhline(0.5, color="grey", lw=0.5, ls=":", alpha=0.4)

    # Dotted iso-lines for unflagged_succ at fixed values
    # unflagged_succ approx = accuracy * (1 - flagged_rate) upper bound
    xs = np.linspace(0.01, 0.99, 200)
    for target in [0.25, 0.5, 0.75]:
        ys = target / (1 - xs)
        mask = (ys >= 0) & (ys <= 1)
        ax.plot(xs[mask], ys[mask], ls="--", lw=0.5, color="black", alpha=0.2)
        # label near x=0.1
        yi = target / (1 - 0.15)
        if 0 <= yi <= 1:
            ax.text(0.15, yi + 0.01, f"unflag succ ≈ {target:.2f}",
                    fontsize=7, color="grey", alpha=0.7)

    ax.set_xlabel("Monitor flagged rate (lower = better evasion)")
    ax.set_ylabel("Receiver accuracy (higher = better transmission)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Capability-evasion frontier: transmission vs detection")
    ax.legend(title="regime", loc="lower left")
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def plot_heatmap_config_regime(valid, out: Path):
    configs = sorted({t["config"] for t in valid})
    regimes = ["zero_shot", "few_shot", "strategy_first"]
    mat = np.full((len(configs), len(regimes)), np.nan)
    ns = np.zeros((len(configs), len(regimes)), dtype=int)
    for i, cfg in enumerate(configs):
        for j, rgm in enumerate(regimes):
            rows = [t for t in valid if t["config"] == cfg and t["regime"] == rgm]
            if rows:
                s = summarize(rows)
                mat[i, j] = s["unflagged_succ"]
                ns[i, j] = s["n"]

    fig, ax = plt.subplots(figsize=(7, 0.55 * len(configs) + 2))
    im = ax.imshow(mat, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(regimes)))
    ax.set_xticklabels(regimes)
    ax.set_yticks(range(len(configs)))
    ax.set_yticklabels(configs, fontsize=8)
    for i in range(len(configs)):
        for j in range(len(regimes)):
            v = mat[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v*100:.0f}%\nn={ns[i, j]}",
                        ha="center", va="center",
                        fontsize=8,
                        color="black" if 0.3 < v < 0.7 else "white")
    ax.set_title("Unflagged success rate: config x regime")
    fig.colorbar(im, ax=ax, shrink=0.8, label="unflagged success")
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def plot_monitor_effect(valid, out: Path):
    """How does monitor strength affect flagged rate and unflagged success?"""
    groups = defaultdict(list)
    for t in valid:
        groups[t["monitor"]].append(t)
    monitors = sorted(groups.keys(),
                      key=lambda m: {"haiku": 0, "gemini": 1, "sonnet": 2, "opus": 3}.get(m, 99))

    flag, ufs, ns = [], [], []
    for m in monitors:
        s = summarize(groups[m])
        flag.append(s["flagged_rate"])
        ufs.append(s["unflagged_succ"])
        ns.append(s["n"])

    x = np.arange(len(monitors))
    w = 0.35
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.bar(x - w / 2, flag, w, label="flagged rate", color="#c9503b", alpha=0.85)
    ax.bar(x + w / 2, ufs, w, label="unflagged success", color="#4aa56b", alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n(n={n})" for m, n in zip(monitors, ns)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Rate")
    ax.set_title("Monitor strength effect")
    ax.axhline(0.5, color="grey", lw=0.5, ls="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    args = p.parse_args()
    run_dir = Path(args.run_dir)
    plots = run_dir / "plots"
    ensure_dir(plots)

    trials = load_trials(run_dir)
    valid = [t for t in trials if not t.get("error")]
    print(f"Plotting from {len(valid)} valid trials")

    plot_overall(valid, plots / "01_overall.png")
    plot_group_bars(valid, lambda t: t["config"],
                    "Per-config outcomes", plots / "02_by_config.png")
    plot_group_bars(valid, lambda t: t["regime"],
                    "Per-regime outcomes", plots / "03_by_regime.png")
    plot_group_bars(valid, lambda t: t["tier"],
                    "Per-tier outcomes", plots / "04_by_tier.png")
    plot_frontier(valid, plots / "05_frontier_scatter.png")
    plot_heatmap_config_regime(valid, plots / "06_regime_heatmap.png")
    plot_monitor_effect(valid, plots / "07_monitor_effect.png")

    print(f"Saved 7 plots to {plots}/")


if __name__ == "__main__":
    main()
