#!/usr/bin/env python3
"""Compare baseline / V2 / V3 / V3a / V3b across all workloads."""
import os, re

def get_stat(stats_path, pattern):
    if not os.path.exists(stats_path):
        return None
    with open(stats_path) as f:
        for line in f:
            m = re.search(pattern, line)
            if m:
                return float(m.group(1))
    return None

def get_ipc(p): return get_stat(p, r'system\.cpu\.ipc\s+([\d.]+)')
def get_ticks(p): return get_stat(p, r'simTicks\s+(\d+)')

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

workloads = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
             'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

configs = [
    ('baseline', lambda wl: os.path.join(gem5, f'runs/baseline/{wl}/latest/stats.txt')),
    ('V2',       lambda wl: os.path.join(gem5, f'runs/adaptive/v3/{wl}_v2/latest/stats.txt')),
    ('V3',       lambda wl: os.path.join(gem5, f'runs/adaptive/v3/{wl}_v3/latest/stats.txt')),
    ('V3a',      lambda wl: os.path.join(gem5, f'runs/adaptive/v3/{wl}_v3a/latest/stats.txt')),
    ('V3b',      lambda wl: os.path.join(gem5, f'runs/adaptive/v3/{wl}_v3b/latest/stats.txt')),
]

# IPC table
print("=" * 120)
print("  IPC Comparison: Baseline / V2 / V3 / V3a / V3b")
print("=" * 120)
header = f"{'Workload':<28}"
for name, _ in configs:
    header += f" {name:>9}"
header += "  |"
for name, _ in configs[1:]:
    header += f" {name+' vs BL':>10}"
print(header)
print("-" * 120)

for wl in workloads:
    ipcs = {}
    for name, path_fn in configs:
        ipcs[name] = get_ipc(path_fn(wl))

    bl = ipcs.get('baseline')
    if bl is None or bl == 0:
        continue

    row = f"{wl:<28}"
    for name, _ in configs:
        v = ipcs[name]
        row += f" {v:>9.3f}" if v else "       N/A"
    row += "  |"
    for name, _ in configs[1:]:
        v = ipcs[name]
        if v and bl:
            row += f" {(v/bl-1)*100:>+9.1f}%"
        else:
            row += "        N/A"
    print(row)

# simTicks table
print()
print("=" * 120)
print("  simTicks Comparison (lower = faster)")
print("=" * 120)
header = f"{'Workload':<28}"
for name, _ in configs:
    header += f" {name:>12}"
header += "  |"
for name, _ in configs[1:]:
    header += f" {name+' vs BL':>10}"
print(header)
print("-" * 120)

for wl in workloads:
    ticks = {}
    for name, path_fn in configs:
        ticks[name] = get_ticks(path_fn(wl))

    bl = ticks.get('baseline')
    if bl is None or bl == 0:
        continue

    row = f"{wl:<28}"
    for name, _ in configs:
        v = ticks[name]
        row += f" {v/1e9:>12.2f}" if v else "          N/A"
    row += "  |"
    for name, _ in configs[1:]:
        v = ticks[name]
        if v and bl:
            row += f" {(v/bl-1)*100:>+9.1f}%"
        else:
            row += "        N/A"
    print(row)

# Window log analysis
print()
print("=" * 120)
print("  Conservative Window % (from adaptive_window_log.csv)")
print("=" * 120)
header = f"{'Workload':<28}"
for name, _ in configs[1:]:
    header += f" {name:>12}"
print(header)
print("-" * 80)

import csv
for wl in workloads:
    row = f"{wl:<28}"
    for name, path_fn in configs[1:]:
        stats_dir = os.path.dirname(path_fn(wl))
        log_path = os.path.join(stats_dir, 'adaptive_window_log.csv')
        if not os.path.exists(log_path):
            row += "          N/A"
            continue
        try:
            with open(log_path) as f:
                reader = csv.DictReader(f)
                total = 0
                cons = 0
                for r in reader:
                    total += 1
                    if 'conservative' in r.get('applied_mode', '').lower():
                        cons += 1
            if total > 0:
                row += f" {cons/total*100:>10.1f}%"
            else:
                row += "          N/A"
        except:
            row += "          N/A"
    print(row)
