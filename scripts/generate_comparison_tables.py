#!/usr/bin/env python3
"""
Generate comparison tables from the unified experiment CSV.

Produces:
  1. Baseline vs Adaptive summary per workload
  2. Parameter sensitivity tables (grouped by sweep dimension)
  3. Cross-workload summary

Usage:
    python3 scripts/generate_comparison_tables.py --csv results/all_experiments.csv
"""

import argparse
import csv
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEM5_ROOT = os.path.dirname(SCRIPT_DIR)

# Known microbenchmark names
MICROBENCHMARKS = [
    "serialized_pointer_chase",
    "branch_entropy",
    "hash_probe_chain",
    "phase_scan_mix",
    "stream_cluster_reduce",
    "compute_queue_pressure",
]

# Sweep patterns to group experiments
SWEEP_PATTERNS = {
    "guard_threshold": re.compile(r"(.+)_guardthr(\d+)_5m$"),
    "window_size": re.compile(r"(.+)_win(\d+)_5m$"),
    "resource_tight": re.compile(r"(.+)_restight_5m$"),
    "resource_mod": re.compile(r"(.+)_resmod_5m$"),
    "serial_mod": re.compile(r"(.+)_sermod_5m$"),
    "serial_tight": re.compile(r"(.+)_sertight_5m$"),
}


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def pct_change(baseline, adaptive):
    if baseline == 0:
        return 0.0
    return 100.0 * (adaptive - baseline) / baseline


def load_csv(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def find_baseline(rows: list[dict], workload: str) -> dict | None:
    """Find baseline experiment for a given workload name."""
    for r in rows:
        if r["type"] == "baseline" and r["experiment"] == workload:
            return r
    return None


def print_table(title: str, headers: list[str], data: list[list[str]]):
    """Print a formatted markdown table."""
    print(f"\n## {title}\n")
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_line = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"
    print(header_line)
    print(sep_line)
    for row in data:
        cells = []
        for i, cell in enumerate(row):
            w = col_widths[i] if i < len(col_widths) else 10
            cells.append(str(cell).ljust(w))
        print("| " + " | ".join(cells) + " |")


def generate_baseline_vs_adaptive(rows: list[dict]):
    """Table 1: Baseline vs Adaptive V2 for each microbenchmark."""
    headers = [
        "Workload", "B.simTicks", "A.simTicks", "dTicks%",
        "B.IPC", "A.IPC", "dIPC%",
        "B.Power(W)", "A.Power(W)", "dPower%",
        "B.Energy(J)", "A.Energy(J)", "dEnergy%",
    ]
    data = []

    for wl in MICROBENCHMARKS:
        baseline = find_baseline(rows, wl)
        # Find v2 adaptive run (exact name match)
        adaptive = None
        for r in rows:
            if r["type"] == "adaptive_v2" and r["experiment"] == wl:
                adaptive = r
                break

        if not baseline or not adaptive:
            continue

        b_ticks = safe_float(baseline.get("simTicks"))
        a_ticks = safe_float(adaptive.get("simTicks"))
        b_ipc = safe_float(baseline.get("ipc"))
        a_ipc = safe_float(adaptive.get("ipc"))
        b_power = safe_float(baseline.get("runtime_dynamic_power_W"))
        a_power = safe_float(adaptive.get("runtime_dynamic_power_W"))
        b_energy = safe_float(baseline.get("total_runtime_energy_J"))
        a_energy = safe_float(adaptive.get("total_runtime_energy_J"))

        data.append([
            wl,
            f"{b_ticks:.0f}", f"{a_ticks:.0f}", f"{pct_change(b_ticks, a_ticks):+.3f}%",
            f"{b_ipc:.6f}", f"{a_ipc:.6f}", f"{pct_change(b_ipc, a_ipc):+.3f}%",
            f"{b_power:.4f}" if b_power else "N/A",
            f"{a_power:.4f}" if a_power else "N/A",
            f"{pct_change(b_power, a_power):+.3f}%" if b_power and a_power else "N/A",
            f"{b_energy:.6f}" if b_energy else "N/A",
            f"{a_energy:.6f}" if a_energy else "N/A",
            f"{pct_change(b_energy, a_energy):+.3f}%" if b_energy and a_energy else "N/A",
        ])

    print_table("Baseline vs Adaptive V2 (Microbenchmarks)", headers, data)


def generate_formal_comparison(rows: list[dict]):
    """Table 2: GAPBS formal benchmark results."""
    headers = [
        "Benchmark", "Variant", "simTicks", "IPC",
        "Power(W)", "Energy(J)", "Windows", "Switches",
    ]
    data = []

    formal_rows = [
        r for r in rows
        if r["type"] == "adaptive_v2" and r["experiment"].startswith("formal_gapbs")
    ]
    formal_rows.sort(key=lambda r: r["experiment"])

    for r in formal_rows:
        data.append([
            r["experiment"],
            r.get("type", ""),
            r.get("simTicks", "N/A"),
            r.get("ipc", "N/A"),
            r.get("runtime_dynamic_power_W", "N/A"),
            r.get("total_runtime_energy_J", "N/A"),
            r.get("total_windows", "N/A"),
            r.get("switch_count", "N/A"),
        ])

    if data:
        print_table("GAPBS Formal Benchmark Results", headers, data)


def generate_sweep_tables(rows: list[dict]):
    """Table 3: Parameter sensitivity grouped by sweep dimension."""
    v2_rows = [r for r in rows if r["type"] == "adaptive_v2"]

    for sweep_name, pattern in SWEEP_PATTERNS.items():
        sweep_data = []
        for r in v2_rows:
            m = pattern.match(r["experiment"])
            if m:
                sweep_data.append((m.groups(), r))

        if not sweep_data:
            continue

        headers = ["Experiment", "simTicks", "IPC", "Power(W)", "Energy(J)", "Windows", "Conservative%"]
        data = []
        for groups, r in sorted(sweep_data, key=lambda x: x[0]):
            cons_pct = r.get("mode_conservative_pct", "N/A")
            data.append([
                r["experiment"],
                r.get("simTicks", "N/A"),
                r.get("ipc", "N/A"),
                r.get("runtime_dynamic_power_W", "N/A"),
                r.get("total_runtime_energy_J", "N/A"),
                r.get("total_windows", "N/A"),
                cons_pct,
            ])

        print_table(f"Parameter Sweep: {sweep_name}", headers, data)


def generate_cross_workload_summary(rows: list[dict]):
    """Table 4: One-line summary per workload."""
    headers = [
        "Workload", "Type", "simTicks", "IPC", "Power(W)", "Energy(J)",
        "Dominant Class", "Conservative%",
    ]
    data = []

    v2_rows = [r for r in rows if r["type"] == "adaptive_v2"]
    # Only include the "base" run for each microbenchmark (exact name match)
    for wl in MICROBENCHMARKS:
        for r in v2_rows:
            if r["experiment"] == wl:
                # Find dominant class
                class_cols = {k: v for k, v in r.items() if k.startswith("class_") and k.endswith("_pct")}
                dominant = max(class_cols, key=lambda k: safe_float(class_cols[k]), default="N/A")
                dominant_name = dominant.replace("class_", "").replace("_pct", "") if dominant != "N/A" else "N/A"

                data.append([
                    wl, "micro",
                    r.get("simTicks", "N/A"),
                    r.get("ipc", "N/A"),
                    r.get("runtime_dynamic_power_W", "N/A"),
                    r.get("total_runtime_energy_J", "N/A"),
                    dominant_name,
                    r.get("mode_conservative_pct", "0"),
                ])
                break

    print_table("Cross-Workload Summary (V2 Adaptive)", headers, data)


def main():
    ap = argparse.ArgumentParser(description="Generate comparison tables")
    ap.add_argument(
        "--csv",
        default=os.path.join(GEM5_ROOT, "results", "all_experiments.csv"),
        help="Input CSV from extract_all_results.py",
    )
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"Error: {args.csv} not found. Run extract_all_results.py first.", file=sys.stderr)
        sys.exit(1)

    rows = load_csv(args.csv)
    print(f"Loaded {len(rows)} experiments from {args.csv}")

    generate_baseline_vs_adaptive(rows)
    generate_formal_comparison(rows)
    generate_sweep_tables(rows)
    generate_cross_workload_summary(rows)


if __name__ == "__main__":
    main()
