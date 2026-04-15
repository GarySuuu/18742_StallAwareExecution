#!/usr/bin/env python3
"""
Extract low-level architectural signals from parameter sweep experiments.

Reads stats.txt from each sweep run and the baseline, extracts pipeline-level
signals (not just IPC/power), and outputs a unified CSV for analysis.
"""

import csv
import os
import re
import sys

# Signals to extract, grouped by pipeline stage
SIGNALS = {
    # High-level
    "simTicks": r"simTicks\s+(\d+)",
    "simInsts": r"simInsts\s+(\d+)",
    "ipc": r"system\.cpu\.ipc\s+([\d.]+)",

    # Fetch stage
    "fetch_cycles": r"system\.cpu\.fetch\.cycles\s+(\d+)",
    "fetch_squashCycles": r"system\.cpu\.fetch\.squashCycles\s+(\d+)",
    "fetch_nisnDist_mean": r"system\.cpu\.fetch\.nisnDist::mean\s+([\d.]+)",
    "fetch_nisnDist_0": r"system\.cpu\.fetch\.nisnDist::0\s+(\d+)",
    "fetch_nisnDist_8": r"system\.cpu\.fetch\.nisnDist::8\s+(\d+)",
    "fetch_nisnDist_samples": r"system\.cpu\.fetch\.nisnDist::samples\s+(\d+)",
    "fetch_predictedBranches": r"system\.cpu\.fetch\.predictedBranches\s+(\d+)",
    "fetch_cacheLines": r"system\.cpu\.fetch\.cacheLines\s+(\d+)",
    "fetch_icacheSquashes": r"system\.cpu\.fetch\.icacheSquashes\s+(\d+)",

    # Decode stage
    "decode_decodedInsts": r"system\.cpu\.decode\.decodedInsts\s+(\d+)",
    "decode_idleCycles": r"system\.cpu\.decode\.idleCycles\s+(\d+)",
    "decode_blockedCycles": r"system\.cpu\.decode\.blockedCycles\s+(\d+)",
    "decode_runCycles": r"system\.cpu\.decode\.runCycles\s+(\d+)",

    # Rename stage
    "rename_renamedInsts": r"system\.cpu\.rename\.renamedInsts\s+(\d+)",
    "rename_idleCycles": r"system\.cpu\.rename\.idleCycles\s+(\d+)",
    "rename_blockCycles": r"system\.cpu\.rename\.blockCycles\s+(\d+)",
    "rename_runCycles": r"system\.cpu\.rename\.runCycles\s+(\d+)",
    "rename_IQFullEvents": r"system\.cpu\.rename\.IQFullEvents\s+(\d+)",
    "rename_LQFullEvents": r"system\.cpu\.rename\.LQFullEvents\s+(\d+)",
    "rename_SQFullEvents": r"system\.cpu\.rename\.SQFullEvents\s+(\d+)",
    "rename_ROBFullEvents": r"system\.cpu\.rename\.ROBFullEvents\s+(\d+)",
    "rename_renamedOperands": r"system\.cpu\.rename\.renamedOperands\s+(\d+)",

    # Issue / IQ
    "numIssuedDist_mean": r"system\.cpu\.numIssuedDist::mean\s+([\d.]+)",
    "numIssuedDist_0": r"system\.cpu\.numIssuedDist::0\s+(\d+)",
    "numIssuedDist_samples": r"system\.cpu\.numIssuedDist::samples\s+(\d+)",

    # LSQ
    "lsq_forwLoads": r"system\.cpu\.lsq0\.forwLoads\s+(\d+)",
    "lsq_blockedByCache": r"system\.cpu\.lsq0\.blockedByCache\s+(\d+)",
    "lsq_memOrderViolation": r"system\.cpu\.lsq0\.memOrderViolation\s+(\d+)",

    # Commit
    "commit_numCommittedDist_mean": r"system\.cpu\.commit\.numCommittedDist::mean\s+([\d.]+)",
    "commit_numCommittedDist_0": r"system\.cpu\.commit\.numCommittedDist::0\s+(\d+)",
    "commit_numCommittedDist_8": r"system\.cpu\.commit\.numCommittedDist::8\s+(\d+)",
    "commit_branchMispredicts": r"system\.cpu\.commit\.branchMispredicts\s+(\d+)",

    # ROB
    "rob_reads": r"system\.cpu\.rob\.reads\s+(\d+)",
    "rob_writes": r"system\.cpu\.rob\.writes\s+(\d+)",

    # IEW
    "iew_memOrderViolation": r"system\.cpu\.iew\.memOrderViolationEvents\s+(\d+)",
}


def extract_signals(stats_path):
    """Extract all signals from a stats.txt file."""
    result = {}
    try:
        with open(stats_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return result

    for name, pattern in SIGNALS.items():
        m = re.search(pattern, content)
        result[name] = m.group(1) if m else ""

    return result


def parse_sweep_tag(dirname):
    """Parse sweep tag to extract parameter name and value."""
    # e.g. sweep_fw2, sweep_iqcap32, sweep_robcap64, sweep_fw2_cap96
    tag = dirname.replace("sweep_", "")
    return tag


def main():
    gem5_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sweep_dir = os.path.join(gem5_root, "runs", "adaptive", "v2")
    baseline_stats = os.path.join(
        gem5_root, "runs", "baseline", "balanced_pipeline_stress", "latest", "stats.txt"
    )
    output_csv = os.path.join(gem5_root, "results", "sweep_signals.csv")

    rows = []

    # Baseline
    if os.path.exists(baseline_stats):
        signals = extract_signals(baseline_stats)
        signals["experiment"] = "baseline"
        signals["sweep_param"] = "none"
        signals["sweep_value"] = "baseline"
        rows.append(signals)

    # Sweep experiments
    if os.path.isdir(sweep_dir):
        for entry in sorted(os.listdir(sweep_dir)):
            if not entry.startswith("sweep_"):
                continue
            stats_path = os.path.join(sweep_dir, entry, "latest", "stats.txt")
            if not os.path.exists(stats_path):
                continue
            signals = extract_signals(stats_path)
            tag = parse_sweep_tag(entry)
            signals["experiment"] = entry
            signals["sweep_param"] = tag
            signals["sweep_value"] = tag
            rows.append(signals)

    if not rows:
        print("No experiments found.", file=sys.stderr)
        sys.exit(1)

    # Write CSV
    fieldnames = ["experiment", "sweep_param", "sweep_value"] + list(SIGNALS.keys())
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} experiments to {output_csv}")


if __name__ == "__main__":
    main()
