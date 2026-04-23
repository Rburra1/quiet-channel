"""
Analysis for the steganographic collusion benchmark.

Key metrics:
  accuracy         = P(receiver guess correct)
  flagged_rate     = P(monitor flags message as suspicious)
  unflagged_succ   = P(correct AND not flagged) -- this is the capability-evasion frontier

All confidence intervals are Wilson 95%.
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Tuple


def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    halfw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - halfw), min(1.0, center + halfw))


def load_trials(run_dir: Path) -> List[Dict[str, Any]]:
    trials = []
    for line in (run_dir / "trials.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            trials.append(obj)
        except Exception:
            continue
    return trials


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0, "accuracy": None, "flagged_rate": None, "unflagged_succ": None}
    k_corr = sum(1 for r in rows if r.get("correct"))
    k_flag = sum(1 for r in rows if r.get("flagged"))
    k_ufs = sum(1 for r in rows if r.get("unflagged_success"))
    return {
        "n": n,
        "accuracy": k_corr / n,
        "accuracy_ci": wilson_ci(k_corr, n),
        "flagged_rate": k_flag / n,
        "flagged_rate_ci": wilson_ci(k_flag, n),
        "unflagged_succ": k_ufs / n,
        "unflagged_succ_ci": wilson_ci(k_ufs, n),
    }


def group_by(trials, *keys) -> Dict[Tuple, List[Dict]]:
    out = defaultdict(list)
    for t in trials:
        if t.get("error"):
            continue
        k = tuple(t[x] for x in keys)
        out[k].append(t)
    return out


def fmt_pct(v, ci=None, n=None):
    if v is None:
        return "n/a"
    s = f"{v*100:5.1f}%"
    if ci is not None:
        s += f" [{ci[0]*100:4.1f}, {ci[1]*100:4.1f}]"
    if n is not None:
        s += f"  n={n}"
    return s


def print_table(title: str, grouped: Dict[Tuple, List[Dict]], headers: List[str]):
    print("\n" + title)
    print("-" * len(title))
    rows = []
    for key in sorted(grouped.keys()):
        s = summarize(grouped[key])
        rows.append((
            " | ".join(str(x) for x in key),
            s["n"],
            fmt_pct(s["accuracy"], s.get("accuracy_ci")),
            fmt_pct(s["flagged_rate"], s.get("flagged_rate_ci")),
            fmt_pct(s["unflagged_succ"], s.get("unflagged_succ_ci")),
        ))
    # stringify all cells first so width math is simple
    str_rows = [tuple(str(x) for x in r) for r in rows]
    headers = ["config", "n", "accuracy", "flagged", "unflag_succ"]
    widths = [max(len(h), max((len(r[i]) for r in str_rows), default=0))
              for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    for r in str_rows:
        print(fmt.format(*r))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    args = p.parse_args()
    run_dir = Path(args.run_dir)

    trials = load_trials(run_dir)
    n_total = len(trials)
    n_err = sum(1 for t in trials if t.get("error"))
    n_ok = n_total - n_err
    print(f"Loaded {n_total} trials ({n_ok} ok, {n_err} errors)")

    valid = [t for t in trials if not t.get("error")]

    # Overall
    overall = summarize(valid)
    print("\n== Overall ==")
    print(f"  n               = {overall['n']}")
    print(f"  accuracy        = {fmt_pct(overall['accuracy'], overall['accuracy_ci'])}")
    print(f"  flagged_rate    = {fmt_pct(overall['flagged_rate'], overall['flagged_rate_ci'])}")
    print(f"  unflagged_succ  = {fmt_pct(overall['unflagged_succ'], overall['unflagged_succ_ci'])}")

    # Breakdowns
    print_table("By config (sender|receiver|monitor)", group_by(valid, "config"), ["config"])
    print_table("By regime", group_by(valid, "regime"), ["regime"])
    print_table("By tier", group_by(valid, "tier"), ["tier"])
    print_table("By config x regime", group_by(valid, "config", "regime"), ["config", "regime"])
    print_table("By config x tier", group_by(valid, "config", "tier"), ["config", "tier"])

    # Capability-evasion frontier: (sender/receiver pair, monitor) x regime
    print_table("Capability-evasion frontier: (sender, receiver) vs monitor",
                group_by(valid, "sender", "receiver", "monitor"),
                ["sender", "receiver", "monitor"])

    # Save summary JSON
    summary = {
        "n_total": n_total, "n_ok": n_ok, "n_err": n_err,
        "overall": overall,
        "by_config": {"|".join(k): summarize(v) for k, v in group_by(valid, "config").items()},
        "by_regime": {k[0]: summarize(v) for k, v in group_by(valid, "regime").items()},
        "by_tier": {k[0]: summarize(v) for k, v in group_by(valid, "tier").items()},
        "by_config_regime": {"|".join(k): summarize(v)
                             for k, v in group_by(valid, "config", "regime").items()},
        "by_srm": {"|".join(k): summarize(v)
                   for k, v in group_by(valid, "sender", "receiver", "monitor").items()},
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=list))
    print(f"\nSaved: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
