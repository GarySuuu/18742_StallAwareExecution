#!/usr/bin/env python3
"""
Generate charts from the unified experiment CSV.

Produces:
  1. Bar charts: baseline vs adaptive per microbenchmark (IPC, power, energy)
  2. Scatter plot: performance loss vs energy saved (Pareto frontier)
  3. Heatmap: sweep parameter vs energy delta (if sweep data available)

Usage:
    python3 scripts/generate_charts.py --csv results/all_experiments.csv \
                                       --out-dir results/charts/
"""

import argparse
import csv
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEM5_ROOT = os.path.dirname(SCRIPT_DIR)

MICROBENCHMARKS = [
    "serialized_pointer_chase",
    "branch_entropy",
    "hash_probe_chain",
    "phase_scan_mix",
    "stream_cluster_reduce",
    "compute_queue_pressure",
]

# Short labels for display
SHORT_NAMES = {
    "serialized_pointer_chase": "ptr_chase",
    "branch_entropy": "br_entropy",
    "hash_probe_chain": "hash_probe",
    "phase_scan_mix": "phase_mix",
    "stream_cluster_reduce": "stream_red",
    "compute_queue_pressure": "cmp_press",
}


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def pct_change(base, new):
    if base == 0:
        return 0.0
    return 100.0 * (new - base) / base


def load_csv(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def find_pairs(rows: list[dict]) -> list[tuple[str, dict, dict]]:
    """Find baseline/adaptive_v2 pairs for microbenchmarks."""
    baseline_map = {}
    adaptive_map = {}
    for r in rows:
        if r["type"] == "baseline":
            baseline_map[r["experiment"]] = r
        elif r["type"] == "adaptive_v2":
            adaptive_map[r["experiment"]] = r

    pairs = []
    for wl in MICROBENCHMARKS:
        if wl in baseline_map and wl in adaptive_map:
            pairs.append((wl, baseline_map[wl], adaptive_map[wl]))
    return pairs


def chart_bar_comparison(pairs, out_dir):
    """Bar chart: baseline vs adaptive for IPC, power, energy."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available, skipping bar chart", file=sys.stderr)
        return

    workloads = [SHORT_NAMES.get(wl, wl) for wl, _, _ in pairs]
    n = len(workloads)
    if n == 0:
        return

    metrics = [
        ("IPC", "ipc", False),
        ("Power (W)", "runtime_dynamic_power_W", False),
        ("Energy (J)", "total_runtime_energy_J", False),
    ]

    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 5))
    if len(metrics) == 1:
        axes = [axes]

    x = np.arange(n)
    width = 0.35

    for ax, (label, key, _) in zip(axes, metrics):
        baseline_vals = [safe_float(b.get(key)) for _, b, _ in pairs]
        adaptive_vals = [safe_float(a.get(key)) for _, _, a in pairs]

        if all(v == 0 for v in baseline_vals):
            ax.set_title(f"{label}\n(no data)")
            continue

        bars_b = ax.bar(x - width / 2, baseline_vals, width, label="Baseline", color="#4477AA")
        bars_a = ax.bar(x + width / 2, adaptive_vals, width, label="Adaptive V2", color="#EE6677")

        ax.set_ylabel(label)
        ax.set_title(label)
        ax.set_xticks(x)
        ax.set_xticklabels(workloads, rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8)

    plt.tight_layout()
    path = os.path.join(out_dir, "baseline_vs_adaptive_bars.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def chart_pareto(pairs, out_dir):
    """Scatter: performance loss (%) vs energy saved (%)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping pareto chart", file=sys.stderr)
        return

    fig, ax = plt.subplots(figsize=(8, 6))

    for wl, baseline, adaptive in pairs:
        b_ticks = safe_float(baseline.get("simTicks"))
        a_ticks = safe_float(adaptive.get("simTicks"))
        b_energy = safe_float(baseline.get("total_runtime_energy_J"))
        a_energy = safe_float(adaptive.get("total_runtime_energy_J"))

        if b_ticks == 0 or b_energy == 0:
            continue

        perf_loss = pct_change(b_ticks, a_ticks)  # positive = slower
        energy_saved = -pct_change(b_energy, a_energy)  # positive = saved

        ax.scatter(perf_loss, energy_saved, s=80, zorder=5)
        ax.annotate(SHORT_NAMES.get(wl, wl), (perf_loss, energy_saved),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)

    ax.axhline(0, color="gray", linestyle="--", linewidth=0.5)
    ax.axvline(0, color="gray", linestyle="--", linewidth=0.5)
    ax.set_xlabel("Performance Change (%, positive = slower)")
    ax.set_ylabel("Energy Saved (%, positive = saved)")
    ax.set_title("Performance vs Energy Tradeoff (Adaptive V2)")

    # Shade the "win-win" quadrant (faster AND energy saved)
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.fill_between([min(xlim[0], -1), 0], [0, 0], [max(ylim[1], 1), max(ylim[1], 1)],
                    alpha=0.1, color="green", label="Win-win")
    ax.legend(fontsize=8)

    plt.tight_layout()
    path = os.path.join(out_dir, "pareto_perf_vs_energy.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def chart_all_v2_pareto(rows, out_dir):
    """Scatter of ALL v2 experiments showing performance vs energy tradeoff."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    # Group v2 experiments by their base workload
    baseline_map = {r["experiment"]: r for r in rows if r["type"] == "baseline"}
    v2_rows = [r for r in rows if r["type"] == "adaptive_v2"]

    fig, ax = plt.subplots(figsize=(10, 8))

    for r in v2_rows:
        # Try to find matching baseline
        exp = r["experiment"]
        base_wl = None
        for wl in MICROBENCHMARKS:
            if exp.startswith(wl):
                base_wl = wl
                break
        if not base_wl or base_wl not in baseline_map:
            continue

        baseline = baseline_map[base_wl]
        b_ticks = safe_float(baseline.get("simTicks"))
        a_ticks = safe_float(r.get("simTicks"))
        b_energy = safe_float(baseline.get("total_runtime_energy_J"))
        a_energy = safe_float(r.get("total_runtime_energy_J"))

        if b_ticks == 0 or b_energy == 0:
            continue

        perf_loss = pct_change(b_ticks, a_ticks)
        energy_saved = -pct_change(b_energy, a_energy)

        color_map = {
            "serialized_pointer_chase": "#4477AA",
            "branch_entropy": "#EE6677",
            "hash_probe_chain": "#228833",
            "phase_scan_mix": "#CCBB44",
            "stream_cluster_reduce": "#66CCEE",
            "compute_queue_pressure": "#AA3377",
        }
        ax.scatter(perf_loss, energy_saved, s=30, alpha=0.6,
                   color=color_map.get(base_wl, "gray"))

    # Add legend
    import matplotlib.patches as mpatches
    color_map = {
        "ptr_chase": "#4477AA", "br_entropy": "#EE6677",
        "hash_probe": "#228833", "phase_mix": "#CCBB44",
        "stream_red": "#66CCEE", "cmp_press": "#AA3377",
    }
    handles = [mpatches.Patch(color=c, label=l) for l, c in color_map.items()]
    ax.legend(handles=handles, fontsize=7, loc="upper left")

    ax.axhline(0, color="gray", linestyle="--", linewidth=0.5)
    ax.axvline(0, color="gray", linestyle="--", linewidth=0.5)
    ax.set_xlabel("Performance Change (%, positive = slower)")
    ax.set_ylabel("Energy Saved (%, positive = saved)")
    ax.set_title("All V2 Experiments: Performance vs Energy")

    plt.tight_layout()
    path = os.path.join(out_dir, "all_v2_pareto.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def main():
    ap = argparse.ArgumentParser(description="Generate charts from experiment data")
    ap.add_argument(
        "--csv",
        default=os.path.join(GEM5_ROOT, "results", "all_experiments.csv"),
        help="Input CSV from extract_all_results.py",
    )
    ap.add_argument(
        "--out-dir",
        default=os.path.join(GEM5_ROOT, "results", "charts"),
        help="Output directory for charts",
    )
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"Error: {args.csv} not found. Run extract_all_results.py first.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    rows = load_csv(args.csv)
    print(f"Loaded {len(rows)} experiments")

    pairs = find_pairs(rows)
    print(f"Found {len(pairs)} baseline/adaptive pairs for microbenchmarks")

    chart_bar_comparison(pairs, args.out_dir)
    chart_pareto(pairs, args.out_dir)
    chart_all_v2_pareto(rows, args.out_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
