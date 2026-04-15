#!/usr/bin/env python3
"""
Visualize adaptive mode timeline from window logs.

Reads adaptive_window_log.csv and produces:
  1. Mode timeline (color bands showing which mode is active per window)
  2. Key metrics over time (IPC proxy, mem_block_ratio, branch_recovery_ratio)
  3. Classification distribution pie chart

Usage:
    python3 scripts/visualize_mode_timeline.py \
        --log runs/adaptive/v2/phase_scan_mix/latest/adaptive_window_log.csv \
        --out-dir results/mode_analysis/phase_scan_mix/

    # Batch: analyze all v2 experiments
    python3 scripts/visualize_mode_timeline.py --batch --out-dir results/mode_analysis/
"""

import argparse
import csv
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEM5_ROOT = os.path.dirname(SCRIPT_DIR)

# Mode colors
MODE_COLORS = {
    "aggressive": "#4477AA",
    "conservative": "#EE6677",
    "serialized-profile": "#CC6677",
    "high-mlp-profile": "#44AA77",
    "control-profile": "#DDCC77",
    "resource-profile": "#88CCEE",
}

CLASS_COLORS = {
    "High-MLP memory dominated": "#44AA77",
    "Serialized-memory dominated": "#CC6677",
    "Control dominated": "#DDCC77",
    "Resource-contention / compute dominated": "#88CCEE",
}


def load_window_log(csv_path: str) -> list[dict]:
    with open(csv_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f))


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def analyze_single(csv_path: str, out_dir: str, name: str = ""):
    """Analyze a single window log file."""
    rows = load_window_log(csv_path)
    if not rows:
        print(f"  Skipping {csv_path}: empty log")
        return

    if not name:
        name = os.path.basename(os.path.dirname(os.path.dirname(csv_path)))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available", file=sys.stderr)
        return

    os.makedirs(out_dir, exist_ok=True)

    window_ids = [int(r.get("window_id", i)) for i, r in enumerate(rows)]
    cycles = [safe_float(r.get("cycles", 5000)) for r in rows]
    cum_cycles = np.cumsum(cycles)

    modes = [(r.get("applied_mode") or "").strip() for r in rows]
    classes = [(r.get("class") or "").strip() for r in rows]
    switched = [
        (r.get("switched") or "").strip().lower() in ("1", "true", "yes")
        for r in rows
    ]

    # Compute per-window IPC proxy
    ipc_proxy = []
    for r in rows:
        committed = safe_float(r.get("committed_insts", 0))
        cyc = safe_float(r.get("cycles", 5000))
        ipc_proxy.append(committed / max(cyc, 1))

    # Key signal metrics
    mem_block = [safe_float(r.get("commit_blocked_mem_cycles", 0)) / max(safe_float(r.get("cycles", 5000)), 1) for r in rows]
    branch_rec = [safe_float(r.get("branch_recovery_ratio", 0)) for r in rows]
    squash = [safe_float(r.get("squash_ratio", 0)) for r in rows]
    iq_sat = [safe_float(r.get("iq_saturation_ratio", 0)) for r in rows]
    avg_inflight = [safe_float(r.get("avg_inflight_proxy", 0)) for r in rows]

    # ---------- Figure 1: Mode Timeline + Metrics ----------
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True,
                             gridspec_kw={"height_ratios": [1, 2, 2, 2]})

    # Subplot 1: Mode color bands
    ax = axes[0]
    for i, mode in enumerate(modes):
        color = MODE_COLORS.get(mode, "#AAAAAA")
        ax.barh(0, cycles[i], left=cum_cycles[i] - cycles[i], height=1,
                color=color, edgecolor="none")
    # Mark switch events
    for i, sw in enumerate(switched):
        if sw:
            ax.axvline(cum_cycles[i], color="black", linewidth=0.5, alpha=0.5)
    ax.set_yticks([])
    ax.set_ylabel("Mode")
    ax.set_title(f"Adaptive Mode Timeline: {name}")

    # Legend for modes
    from collections import Counter
    mode_counts = Counter(modes)
    legend_items = []
    import matplotlib.patches as mpatches
    for mode_name in sorted(mode_counts.keys()):
        color = MODE_COLORS.get(mode_name, "#AAAAAA")
        pct = 100 * mode_counts[mode_name] / len(modes)
        legend_items.append(mpatches.Patch(color=color, label=f"{mode_name} ({pct:.1f}%)"))
    ax.legend(handles=legend_items, fontsize=7, loc="upper right", ncol=3)

    # Subplot 2: IPC proxy
    ax = axes[1]
    ax.plot(cum_cycles, ipc_proxy, linewidth=0.5, color="#4477AA")
    ax.fill_between(cum_cycles, ipc_proxy, alpha=0.3, color="#4477AA")
    ax.set_ylabel("IPC Proxy")
    ax.grid(True, alpha=0.3)

    # Subplot 3: Memory + branch signals
    ax = axes[2]
    ax.plot(cum_cycles, mem_block, linewidth=0.5, label="mem_block_ratio", color="#EE6677")
    ax.plot(cum_cycles, branch_rec, linewidth=0.5, label="branch_recovery_ratio", color="#DDCC77")
    ax.plot(cum_cycles, squash, linewidth=0.5, label="squash_ratio", color="#228833")
    ax.set_ylabel("Ratio")
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(True, alpha=0.3)

    # Subplot 4: IQ saturation + inflight
    ax = axes[3]
    ax.plot(cum_cycles, iq_sat, linewidth=0.5, label="iq_saturation_ratio", color="#AA3377")
    ax2 = ax.twinx()
    ax2.plot(cum_cycles, avg_inflight, linewidth=0.5, label="avg_inflight_proxy", color="#66CCEE")
    ax.set_ylabel("IQ Sat Ratio")
    ax2.set_ylabel("Avg Inflight")
    ax.set_xlabel("Cumulative Cycles")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="upper right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(out_dir, f"{name}_mode_timeline.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # ---------- Figure 2: Classification Distribution ----------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Pie chart: class distribution
    class_counts = Counter(classes)
    labels = list(class_counts.keys())
    sizes = list(class_counts.values())
    colors = [CLASS_COLORS.get(l, "#AAAAAA") for l in labels]
    ax1.pie(sizes, labels=[f"{l}\n({100*s/sum(sizes):.1f}%)" for l, s in zip(labels, sizes)],
            colors=colors, startangle=90)
    ax1.set_title(f"Classification Distribution: {name}")

    # Pie chart: mode distribution
    labels_m = list(mode_counts.keys())
    sizes_m = list(mode_counts.values())
    colors_m = [MODE_COLORS.get(l, "#AAAAAA") for l in labels_m]
    ax2.pie(sizes_m, labels=[f"{l}\n({100*s/sum(sizes_m):.1f}%)" for l, s in zip(labels_m, sizes_m)],
            colors=colors_m, startangle=90)
    ax2.set_title(f"Mode Distribution: {name}")

    plt.tight_layout()
    path = os.path.join(out_dir, f"{name}_class_distribution.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # ---------- Text Summary ----------
    total_switches = sum(switched)
    summary = f"""# Mode Analysis: {name}

## Statistics
- Total windows: {len(rows)}
- Total cycles: {cum_cycles[-1]:.0f}
- Mode switches: {total_switches} ({100*total_switches/len(rows):.2f}%)

## Classification Distribution
"""
    for cls_name, cnt in sorted(class_counts.items(), key=lambda x: -x[1]):
        summary += f"- {cls_name}: {cnt} ({100*cnt/len(rows):.1f}%)\n"

    summary += "\n## Mode Distribution\n"
    for mode_name, cnt in sorted(mode_counts.items(), key=lambda x: -x[1]):
        summary += f"- {mode_name}: {cnt} ({100*cnt/len(rows):.1f}%)\n"

    summary += f"\n## Average Metrics\n"
    summary += f"- IPC proxy: {sum(ipc_proxy)/len(ipc_proxy):.4f}\n"
    summary += f"- Avg inflight: {sum(avg_inflight)/len(avg_inflight):.2f}\n"
    summary += f"- Avg mem_block_ratio: {sum(mem_block)/len(mem_block):.4f}\n"
    summary += f"- Avg branch_recovery_ratio: {sum(branch_rec)/len(branch_rec):.4f}\n"

    summary_path = os.path.join(out_dir, f"{name}_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"  Saved: {summary_path}")


def batch_analyze(runs_dir: str, out_dir: str):
    """Analyze all v2 experiments that have window logs."""
    v2_dir = os.path.join(runs_dir, "adaptive", "v2")
    if not os.path.isdir(v2_dir):
        print(f"Error: {v2_dir} not found", file=sys.stderr)
        return

    for entry in sorted(os.listdir(v2_dir)):
        exp_dir = os.path.join(v2_dir, entry)
        if not os.path.isdir(exp_dir):
            continue

        # Try latest/ first, then archive/
        log_path = os.path.join(exp_dir, "latest", "adaptive_window_log.csv")
        if not os.path.exists(log_path):
            archive_dir = os.path.join(exp_dir, "archive")
            if os.path.isdir(archive_dir):
                candidates = sorted(os.listdir(archive_dir), reverse=True)
                for c in candidates:
                    p = os.path.join(archive_dir, c, "adaptive_window_log.csv")
                    if os.path.exists(p):
                        log_path = p
                        break

        if not os.path.exists(log_path):
            continue

        exp_out = os.path.join(out_dir, entry)
        print(f"Analyzing: {entry}")
        analyze_single(log_path, exp_out, entry)


def main():
    ap = argparse.ArgumentParser(description="Visualize adaptive mode timeline")
    ap.add_argument("--log", help="Single adaptive_window_log.csv to analyze")
    ap.add_argument("--name", help="Experiment name (auto-detected if omitted)")
    ap.add_argument("--batch", action="store_true",
                    help="Batch analyze all v2 experiments")
    ap.add_argument(
        "--runs-dir",
        default=os.path.join(GEM5_ROOT, "runs"),
        help="Root runs directory (for batch mode)",
    )
    ap.add_argument(
        "--out-dir",
        default=os.path.join(GEM5_ROOT, "results", "mode_analysis"),
        help="Output directory",
    )
    args = ap.parse_args()

    if args.batch:
        batch_analyze(args.runs_dir, args.out_dir)
    elif args.log:
        analyze_single(args.log, args.out_dir, args.name or "")
    else:
        print("Specify --log <path> or --batch", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
