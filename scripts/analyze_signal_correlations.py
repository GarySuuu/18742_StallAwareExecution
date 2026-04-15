#!/usr/bin/env python3
"""
Analyze signal correlations in adaptive window logs.

Computes correlations between input signals and output classifications,
identifies which thresholds are on decision boundaries, and highlights
borderline windows.

Usage:
    python3 scripts/analyze_signal_correlations.py \
        --log runs/adaptive/v2/phase_scan_mix/latest/adaptive_window_log.csv
"""

import argparse
import csv
import math
import os
import sys
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEM5_ROOT = os.path.dirname(SCRIPT_DIR)

# Default V2 thresholds
THRESHOLDS = {
    "mem_block_ratio": 0.12,
    "avg_outstanding_misses_proxy": 12.0,
    "branch_recovery_ratio": 0.10,
    "squash_ratio": 0.20,
    "iq_saturation_ratio": 0.10,
    "commit_activity_ratio": 0.20,
    "avg_inflight_proxy": 32.0,  # HighMLP guard
}

SIGNAL_COLS = [
    "avg_outstanding_misses_proxy",
    "iq_saturation_ratio",
    "branch_recovery_ratio",
    "squash_ratio",
    "commit_activity_ratio",
    "avg_inflight_proxy",
]


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def load_window_log(csv_path: str) -> list[dict]:
    with open(csv_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f))


def pearson_r(xs, ys):
    """Compute Pearson correlation coefficient."""
    n = len(xs)
    if n < 3:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = math.sqrt(max(0, sum((x - mx) ** 2 for x in xs) / n))
    sy = math.sqrt(max(0, sum((y - my) ** 2 for y in ys) / n))
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    return cov / (sx * sy)


def analyze(csv_path: str, out_path: str | None = None):
    rows = load_window_log(csv_path)
    if len(rows) < 5:
        print("Not enough windows to analyze correlations")
        return

    name = os.path.basename(os.path.dirname(os.path.dirname(csv_path)))

    # Compute derived metrics
    for r in rows:
        committed = safe_float(r.get("committed_insts", 0))
        cyc = safe_float(r.get("cycles", 5000))
        r["_ipc"] = committed / max(cyc, 1)
        blocked = safe_float(r.get("commit_blocked_mem_cycles", 0))
        r["_mem_block_ratio"] = blocked / max(cyc, 1)

    classes = [(r.get("class") or "").strip() for r in rows]
    modes = [(r.get("applied_mode") or "").strip() for r in rows]

    # Encode class as numeric for correlation
    class_set = sorted(set(classes))
    class_to_num = {c: i for i, c in enumerate(class_set)}
    class_nums = [class_to_num[c] for c in classes]

    # Encode mode as 0 (aggressive) or 1 (conservative/throttled)
    mode_nums = [0 if m == "aggressive" else 1 for m in modes]

    ipcs = [r["_ipc"] for r in rows]

    lines = []
    lines.append(f"# Signal Correlation Report: {name}\n")
    lines.append(f"**Log**: `{csv_path}`\n")
    lines.append(f"**Windows**: {len(rows)}\n")

    # --- Signal-to-Class Correlation ---
    lines.append("\n## Signal-to-Classification Correlations\n")
    lines.append("| Signal | Corr(class) | Corr(mode) | Corr(IPC) | Mean | Std |")
    lines.append("|--------|-------------|------------|-----------|------|-----|")

    all_signals = ["_mem_block_ratio"] + SIGNAL_COLS
    for col in all_signals:
        vals = [safe_float(r.get(col, r.get(col.lstrip("_"), 0))) for r in rows]
        mean_val = sum(vals) / len(vals) if vals else 0
        std_val = math.sqrt(sum((v - mean_val) ** 2 for v in vals) / max(len(vals), 1))

        corr_class = pearson_r(vals, class_nums)
        corr_mode = pearson_r(vals, mode_nums)
        corr_ipc = pearson_r(vals, ipcs)

        lines.append(
            f"| {col} | {corr_class:+.3f} | {corr_mode:+.3f} | "
            f"{corr_ipc:+.3f} | {mean_val:.4f} | {std_val:.4f} |"
        )

    # --- Threshold Boundary Analysis ---
    lines.append("\n## Threshold Boundary Analysis\n")
    lines.append("Windows where signals are within 20% of decision thresholds:\n")

    boundary_margin = 0.20
    for signal, threshold in THRESHOLDS.items():
        if threshold == 0:
            continue
        col = signal
        if signal == "mem_block_ratio":
            col = "_mem_block_ratio"

        borderline_count = 0
        for r in rows:
            val = safe_float(r.get(col, r.get(signal, 0)))
            if abs(val - threshold) <= boundary_margin * threshold:
                borderline_count += 1

        pct = 100 * borderline_count / len(rows)
        lines.append(f"- **{signal}** (threshold={threshold}): {borderline_count} borderline windows ({pct:.1f}%)")

    # --- Per-Class Signal Statistics ---
    lines.append("\n## Signal Statistics by Class\n")
    for cls in class_set:
        cls_rows = [r for r, c in zip(rows, classes) if c == cls]
        if not cls_rows:
            continue
        lines.append(f"\n### {cls} ({len(cls_rows)} windows)\n")
        lines.append("| Signal | Mean | Min | Max | Std |")
        lines.append("|--------|------|-----|-----|-----|")

        for col in all_signals:
            vals = [safe_float(r.get(col, r.get(col.lstrip("_"), 0))) for r in cls_rows]
            if not vals:
                continue
            mean_v = sum(vals) / len(vals)
            std_v = math.sqrt(sum((v - mean_v) ** 2 for v in vals) / max(len(vals), 1))
            lines.append(
                f"| {col} | {mean_v:.4f} | {min(vals):.4f} | "
                f"{max(vals):.4f} | {std_v:.4f} |"
            )

    # --- IPC Distribution by Class ---
    lines.append("\n## IPC Distribution by Class\n")
    lines.append("| Class | Windows | Mean IPC | Std IPC |")
    lines.append("|-------|---------|----------|---------|")
    for cls in class_set:
        cls_ipcs = [r["_ipc"] for r, c in zip(rows, classes) if c == cls]
        if not cls_ipcs:
            continue
        mean_ipc = sum(cls_ipcs) / len(cls_ipcs)
        std_ipc = math.sqrt(sum((v - mean_ipc) ** 2 for v in cls_ipcs) / max(len(cls_ipcs), 1))
        lines.append(f"| {cls} | {len(cls_ipcs)} | {mean_ipc:.4f} | {std_ipc:.4f} |")

    report = "\n".join(lines) + "\n"

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Saved: {out_path}")
    else:
        print(report)


def main():
    ap = argparse.ArgumentParser(description="Analyze signal correlations")
    ap.add_argument("--log", required=True, help="adaptive_window_log.csv path")
    ap.add_argument("--out", help="Output report path (prints to stdout if omitted)")
    args = ap.parse_args()

    analyze(args.log, args.out)


if __name__ == "__main__":
    main()
