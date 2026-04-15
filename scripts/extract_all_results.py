#!/usr/bin/env python3
"""
Extract performance, power, and classification data from all gem5 runs.

Walks runs/baseline/ and runs/adaptive/v2/, extracts stats.txt, mcpat.out,
adaptive_window_log.csv, and run_meta.txt from each experiment, and writes
a single unified CSV.

Usage:
    python3 scripts/extract_all_results.py --out-csv results/all_experiments.csv
"""

import argparse
import csv
import os
import re
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEM5_ROOT = os.path.dirname(SCRIPT_DIR)

# ---------------------------------------------------------------------------
# Parsers (adapted from analyze_week11.py)
# ---------------------------------------------------------------------------

def parse_stats(stats_path: str) -> dict:
    """Extract key metrics from gem5 stats.txt."""
    out = {}
    if not os.path.exists(stats_path):
        return out
    wanted = {
        "simTicks": "simTicks",
        "simInsts": "simInsts",
        "simSeconds": "simSeconds",
        "simOps": "simOps",
        "hostSeconds": "hostSeconds",
        "system.cpu.ipc": "ipc",
        "system.cpu.cpi": "cpi",
        "system.cpu.numCycles": "numCycles",
    }
    with open(stats_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            key, val = parts[0], parts[1]
            if key in wanted:
                out[wanted[key]] = val
    return out


def parse_mcpat(mcpat_path: str) -> dict:
    """Extract power/energy from McPAT output."""
    out = {}
    if not os.path.exists(mcpat_path):
        return out
    with open(mcpat_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # System-level metrics (first occurrence)
    patterns = {
        "runtime_dynamic_power_W": r"Runtime Dynamic Power\s*=\s*([\d.e+-]+)\s*W",
        "runtime_dynamic_energy_J": r"Runtime Dynamic Energy\s*=\s*([\d.e+-]+)\s*J",
        "total_runtime_energy_J": r"Total Runtime Energy\s*=\s*([\d.e+-]+)\s*J",
        "subthreshold_leakage_W": r"Subthreshold Leakage Power\s*=\s*([\d.e+-]+)\s*W",
        "gate_leakage_W": r"Gate Leakage Power\s*=\s*([\d.e+-]+)\s*W",
    }
    for key, pat in patterns.items():
        m = re.search(pat, content)
        if m:
            out[key] = m.group(1)
    return out


def parse_window_log(csv_path: str) -> dict:
    """Extract classification/mode distribution from adaptive_window_log.csv."""
    out = {}
    if not os.path.exists(csv_path):
        return out
    with open(csv_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    out["total_windows"] = str(len(rows))
    if not rows:
        return out

    # Class distribution
    class_counts = Counter((r.get("class") or "").strip() for r in rows)
    total = len(rows)
    for cls_name, cnt in class_counts.items():
        if not cls_name:
            continue
        safe_name = cls_name.replace(" ", "_").replace("/", "_").replace("-", "_")
        out[f"class_{safe_name}_pct"] = f"{100 * cnt / total:.2f}"
        out[f"class_{safe_name}_count"] = str(cnt)

    # Mode distribution
    mode_counts = Counter((r.get("applied_mode") or "").strip() for r in rows)
    for mode_name, cnt in mode_counts.items():
        if not mode_name:
            continue
        safe_name = mode_name.replace("-", "_")
        out[f"mode_{safe_name}_pct"] = f"{100 * cnt / total:.2f}"
        out[f"mode_{safe_name}_count"] = str(cnt)

    # Switch events
    switched = sum(
        1 for r in rows
        if (r.get("switched") or "").strip().lower() in ("1", "true", "yes")
    )
    out["switch_count"] = str(switched)
    out["switch_pct"] = f"{100 * switched / total:.2f}"

    # Average metrics
    metric_cols = [
        "avg_outstanding_misses_proxy", "iq_saturation_ratio",
        "branch_recovery_ratio", "squash_ratio", "commit_activity_ratio",
        "avg_inflight_proxy",
    ]
    for col in metric_cols:
        vals = []
        for r in rows:
            try:
                vals.append(float(r.get(col, "0")))
            except (ValueError, TypeError):
                pass
        if vals:
            out[f"avg_{col}"] = f"{sum(vals) / len(vals):.6f}"

    return out


def parse_run_meta(meta_path: str) -> dict:
    """Extract parameter values from run_meta.txt."""
    out = {}
    if not os.path.exists(meta_path):
        return out
    with open(meta_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, _, val = line.partition("=")
                out[f"meta_{key.strip()}"] = val.strip()
    return out


# ---------------------------------------------------------------------------
# Directory walking
# ---------------------------------------------------------------------------

def find_result_dir(run_dir: str) -> str | None:
    """
    Given a run directory, find the actual results.
    Tries: run_dir/latest/, run_dir/archive/<newest>/, run_dir/ directly.
    """
    # Check for latest/ symlink or directory
    latest = os.path.join(run_dir, "latest")
    if os.path.isdir(latest):
        stats = os.path.join(latest, "stats.txt")
        if os.path.exists(stats):
            return latest

    # Check for archive/<timestamp>/ pattern
    archive = os.path.join(run_dir, "archive")
    if os.path.isdir(archive):
        candidates = []
        for name in os.listdir(archive):
            p = os.path.join(archive, name)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, "stats.txt")):
                candidates.append(p)
        if candidates:
            candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return candidates[0]

    # Direct check
    if os.path.exists(os.path.join(run_dir, "stats.txt")):
        return run_dir

    return None


def walk_experiment_tree(base_dir: str, experiment_type: str) -> list[dict]:
    """Walk a directory of experiments and extract data from each."""
    rows = []
    if not os.path.isdir(base_dir):
        return rows

    for entry in sorted(os.listdir(base_dir)):
        run_dir = os.path.join(base_dir, entry)
        if not os.path.isdir(run_dir):
            continue

        result_dir = find_result_dir(run_dir)
        if result_dir is None:
            continue

        stats = parse_stats(os.path.join(result_dir, "stats.txt"))
        if not stats:
            continue

        mcpat = parse_mcpat(os.path.join(result_dir, "mcpat.out"))
        window = parse_window_log(
            os.path.join(result_dir, "adaptive_window_log.csv")
        )
        meta = parse_run_meta(os.path.join(result_dir, "run_meta.txt"))

        row = {
            "experiment": entry,
            "type": experiment_type,
            "result_dir": result_dir,
            **stats,
            **mcpat,
            **window,
            **meta,
        }
        rows.append(row)

    return rows


def main():
    ap = argparse.ArgumentParser(description="Extract all gem5 experiment results")
    ap.add_argument(
        "--out-csv",
        default=os.path.join(GEM5_ROOT, "results", "all_experiments.csv"),
        help="Output CSV path",
    )
    ap.add_argument(
        "--runs-dir",
        default=os.path.join(GEM5_ROOT, "runs"),
        help="Root runs directory",
    )
    args = ap.parse_args()

    all_rows = []

    # Baseline runs
    baseline_dirs = [
        os.path.join(args.runs_dir, "baseline"),
    ]
    for bdir in baseline_dirs:
        rows = walk_experiment_tree(bdir, "baseline")
        all_rows.extend(rows)
        print(f"  baseline: {len(rows)} experiments from {bdir}")

    # Adaptive v1 runs
    v1_dir = os.path.join(args.runs_dir, "adaptive", "v1")
    rows = walk_experiment_tree(v1_dir, "adaptive_v1")
    all_rows.extend(rows)
    print(f"  adaptive_v1: {len(rows)} experiments from {v1_dir}")

    # Adaptive v2 runs
    v2_dir = os.path.join(args.runs_dir, "adaptive", "v2")
    rows = walk_experiment_tree(v2_dir, "adaptive_v2")
    all_rows.extend(rows)
    print(f"  adaptive_v2: {len(rows)} experiments from {v2_dir}")

    if not all_rows:
        print("No experiments found.")
        return

    # Build stable header from union of all keys
    all_keys = []
    seen = set()
    # Put important columns first
    priority_keys = [
        "experiment", "type", "simTicks", "simInsts", "ipc", "cpi",
        "runtime_dynamic_power_W", "runtime_dynamic_energy_J",
        "total_runtime_energy_J", "total_windows", "switch_count",
    ]
    for k in priority_keys:
        if any(k in r for r in all_rows):
            all_keys.append(k)
            seen.add(k)
    for r in all_rows:
        for k in sorted(r.keys()):
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_csv)), exist_ok=True)
    with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_keys)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    print(f"\nWrote {len(all_rows)} experiments to {args.out_csv}")


if __name__ == "__main__":
    main()
