#!/usr/bin/env python3
"""
Analyze classification quality from adaptive window logs.

For each window, checks whether mode switches led to better or worse
performance (IPC proxy), identifies oscillation patterns, and produces
a quality report.

Usage:
    python3 scripts/analyze_classification_quality.py \
        --log runs/adaptive/v2/phase_scan_mix/latest/adaptive_window_log.csv
"""

import argparse
import csv
import os
import sys
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEM5_ROOT = os.path.dirname(SCRIPT_DIR)


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def load_window_log(csv_path: str) -> list[dict]:
    with open(csv_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f))


def analyze(csv_path: str, out_path: str | None = None):
    rows = load_window_log(csv_path)
    if len(rows) < 3:
        print("Not enough windows to analyze")
        return

    name = os.path.basename(os.path.dirname(os.path.dirname(csv_path)))

    # Compute per-window IPC proxy
    for r in rows:
        committed = safe_float(r.get("committed_insts", 0))
        cyc = safe_float(r.get("cycles", 5000))
        r["_ipc"] = committed / max(cyc, 1)

    modes = [(r.get("applied_mode") or "").strip() for r in rows]
    classes = [(r.get("class") or "").strip() for r in rows]
    switched = [
        (r.get("switched") or "").strip().lower() in ("1", "true", "yes")
        for r in rows
    ]

    # --- Switch Quality Analysis ---
    # For each switch event, compare avg IPC of 3 windows before vs 3 windows after
    switch_results = []
    lookback = 3
    for i, sw in enumerate(switched):
        if not sw:
            continue
        if i < lookback or i + lookback >= len(rows):
            continue

        before_ipc = sum(rows[j]["_ipc"] for j in range(i - lookback, i)) / lookback
        after_ipc = sum(rows[j]["_ipc"] for j in range(i + 1, i + 1 + lookback)) / lookback

        old_mode = modes[i - 1] if i > 0 else "?"
        new_mode = modes[i]

        delta = after_ipc - before_ipc
        beneficial = delta > 0
        switch_results.append({
            "window": i,
            "old_mode": old_mode,
            "new_mode": new_mode,
            "before_ipc": before_ipc,
            "after_ipc": after_ipc,
            "delta_ipc": delta,
            "beneficial": beneficial,
        })

    # --- Oscillation Detection ---
    # Find sequences where mode switches back and forth within N windows
    oscillation_windows = []
    for i in range(1, len(switched) - 1):
        if switched[i] and any(switched[j] for j in range(max(0, i - 3), i)):
            oscillation_windows.append(i)

    # --- Class Stability Analysis ---
    # How often does the class change?
    class_changes = sum(1 for i in range(1, len(classes)) if classes[i] != classes[i - 1])

    # --- Class-to-Mode Confusion Matrix ---
    class_mode_pairs = Counter(zip(classes, modes))

    # --- IPC by Mode ---
    mode_ipcs = {}
    for mode in set(modes):
        ipcs = [rows[i]["_ipc"] for i in range(len(rows)) if modes[i] == mode]
        if ipcs:
            mode_ipcs[mode] = {
                "count": len(ipcs),
                "mean": sum(ipcs) / len(ipcs),
                "min": min(ipcs),
                "max": max(ipcs),
            }

    # --- Report ---
    lines = []
    lines.append(f"# Classification Quality Report: {name}\n")
    lines.append(f"**Log**: `{csv_path}`\n")
    lines.append(f"**Total windows**: {len(rows)}\n")

    lines.append(f"\n## Switch Quality ({len(switch_results)} switches analyzed)\n")
    if switch_results:
        beneficial = sum(1 for s in switch_results if s["beneficial"])
        harmful = len(switch_results) - beneficial
        lines.append(f"- Beneficial switches (IPC improved): {beneficial} ({100*beneficial/len(switch_results):.1f}%)")
        lines.append(f"- Harmful switches (IPC degraded): {harmful} ({100*harmful/len(switch_results):.1f}%)")
        lines.append(f"- Average IPC delta after switch: {sum(s['delta_ipc'] for s in switch_results)/len(switch_results):.6f}\n")

        lines.append("| Window | Old Mode | New Mode | Before IPC | After IPC | Delta | Beneficial? |")
        lines.append("|--------|----------|----------|------------|-----------|-------|-------------|")
        for s in switch_results[:30]:  # Cap at 30 rows
            lines.append(
                f"| {s['window']} | {s['old_mode']} | {s['new_mode']} | "
                f"{s['before_ipc']:.4f} | {s['after_ipc']:.4f} | "
                f"{s['delta_ipc']:+.4f} | {'Yes' if s['beneficial'] else 'No'} |"
            )
    else:
        lines.append("No switches with enough surrounding windows to analyze.\n")

    lines.append(f"\n## Oscillation Detection\n")
    lines.append(f"- Rapid re-switches (within 3 windows): {len(oscillation_windows)}")
    if oscillation_windows:
        lines.append(f"- Oscillation windows: {oscillation_windows[:20]}{'...' if len(oscillation_windows) > 20 else ''}")

    lines.append(f"\n## Class Stability\n")
    lines.append(f"- Class changes: {class_changes} / {len(rows)} windows ({100*class_changes/len(rows):.1f}%)")

    lines.append(f"\n## IPC by Mode\n")
    lines.append("| Mode | Windows | Mean IPC | Min IPC | Max IPC |")
    lines.append("|------|---------|----------|---------|---------|")
    for mode, stats in sorted(mode_ipcs.items()):
        lines.append(
            f"| {mode} | {stats['count']} | {stats['mean']:.4f} | "
            f"{stats['min']:.4f} | {stats['max']:.4f} |"
        )

    lines.append(f"\n## Class -> Mode Mapping (observed)\n")
    lines.append("| Class | Mode | Count |")
    lines.append("|-------|------|-------|")
    for (cls, mode), cnt in sorted(class_mode_pairs.items(), key=lambda x: -x[1]):
        lines.append(f"| {cls} | {mode} | {cnt} |")

    report = "\n".join(lines) + "\n"

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Saved: {out_path}")
    else:
        print(report)


def main():
    ap = argparse.ArgumentParser(description="Analyze classification quality")
    ap.add_argument("--log", required=True, help="adaptive_window_log.csv path")
    ap.add_argument("--out", help="Output report path (prints to stdout if omitted)")
    args = ap.parse_args()

    analyze(args.log, args.out)


if __name__ == "__main__":
    main()
