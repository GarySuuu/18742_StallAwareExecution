#!/usr/bin/env python3
"""Extract power/energy from McPAT outputs and generate V3 comparison report."""
import os, re

def get_stat(path, pattern):
    if not os.path.exists(path): return None
    with open(path) as f:
        for line in f:
            m = re.search(pattern, line)
            if m: return float(m.group(1))
    return None

def get_ipc(p): return get_stat(p, r'system\.cpu\.ipc\s+([\d.]+)')
def get_ticks(p): return get_stat(p, r'simTicks\s+(\d+)')

def get_mcpat_power(mcpat_path):
    """Extract Runtime Dynamic Power and Total Runtime Energy from mcpat.out"""
    if not os.path.exists(mcpat_path): return None, None
    power = energy = None
    in_system = False
    with open(mcpat_path) as f:
        for line in f:
            # We want the System-level (first occurrence) values
            if 'System:' in line:
                in_system = True
                continue
            if in_system:
                m = re.search(r'Runtime Dynamic Power\s*=\s*([\d.]+)\s*W', line)
                if m and power is None:
                    power = float(m.group(1))
                m2 = re.search(r'Total Runtime Energy\s*=\s*([\d.]+)\s*J', line)
                if m2 and energy is None:
                    energy = float(m2.group(1))
                if power is not None and energy is not None:
                    break
    return power, energy

def get_power_energy(run_dir):
    """Get IPC, simTicks, power, and energy from McPAT."""
    stats = os.path.join(run_dir, 'stats.txt')
    mcpat = os.path.join(run_dir, 'mcpat.out')
    ipc = get_ipc(stats)
    ticks = get_ticks(stats)
    power, energy = get_mcpat_power(mcpat)
    return ipc, ticks, power, energy

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def delta(v, bl):
    if v and bl and bl != 0:
        return f"{(v/bl-1)*100:>+6.1f}%"
    return "    N/A"

def fmt(v, d=3):
    return f"{v:.{d}f}" if v is not None else "N/A"

# =====================================================================
print("=" * 160)
print("  V3 COMPLETE RESULTS: IPC + Power + Energy")
print("=" * 160)

# Microbenchmarks
print("\n" + "=" * 160)
print("  MICROBENCHMARKS (50M instructions)")
print("=" * 160)

micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

micro_paths = {
    'BL': lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest'),
    'V2': lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest'),
    'V3': lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_default/latest'),
}

print(f"\n{'Workload':<28} | {'IPC':>20} | {'Dyn Power (W)':>24} | {'Energy (J)':>24} |")
print(f"{'':28} | {'BL':>6} {'V2':>6} {'V3':>6} | {'BL':>7} {'V2':>7} {'V3':>7} | {'BL':>7} {'V2':>7} {'V3':>7} |")
print("-" * 120)

for wl in micro_wl:
    data = {}
    for cfg, fn in micro_paths.items():
        data[cfg] = get_power_energy(fn(wl))

    bl_ipc, bl_t, bl_p, bl_e = data['BL']
    v2_ipc, v2_t, v2_p, v2_e = data['V2']
    v3_ipc, v3_t, v3_p, v3_e = data['V3']

    print(f"{wl:<28} | {fmt(bl_ipc):>6} {fmt(v2_ipc):>6} {fmt(v3_ipc):>6} "
          f"| {fmt(bl_p,1):>7} {fmt(v2_p,1):>7} {fmt(v3_p,1):>7} "
          f"| {fmt(bl_e,3):>7} {fmt(v2_e,3):>7} {fmt(v3_e,3):>7} |")

# Delta table
print(f"\n{'Workload':<28} | {'IPC vs BL':>14} | {'Power vs BL':>14} | {'Energy vs BL':>14} | {'IPC V3vV2':>10} {'Pwr V3vV2':>10} {'Eng V3vV2':>10}")
print(f"{'':28} | {'V2':>6} {'V3':>6} | {'V2':>6} {'V3':>6} | {'V2':>6} {'V3':>6} |")
print("-" * 130)

for wl in micro_wl:
    data = {}
    for cfg, fn in micro_paths.items():
        data[cfg] = get_power_energy(fn(wl))

    bl_ipc, bl_t, bl_p, bl_e = data['BL']
    v2_ipc, v2_t, v2_p, v2_e = data['V2']
    v3_ipc, v3_t, v3_p, v3_e = data['V3']

    print(f"{wl:<28} | {delta(v2_ipc,bl_ipc):>6} {delta(v3_ipc,bl_ipc):>6} "
          f"| {delta(v2_p,bl_p):>6} {delta(v3_p,bl_p):>6} "
          f"| {delta(v2_e,bl_e):>6} {delta(v3_e,bl_e):>6} "
          f"| {delta(v3_ipc,v2_ipc):>10} {delta(v3_p,v2_p):>10} {delta(v3_e,v2_e):>10}")

# GAPBS
print("\n\n" + "=" * 160)
print("  GAPBS FORMAL BENCHMARKS (g20, 50M instructions)")
print("=" * 160)

gapbs = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']

gapbs_paths = {
    'BL': lambda b: os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest'),
    'V2t': lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest'),
    'V3': lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v3/latest'),
}

print(f"\n{'Bench':<8} | {'IPC':>20} | {'Dyn Power (W)':>24} | {'Energy (J)':>24} |")
print(f"{'':8} | {'BL':>6} {'V2t':>6} {'V3':>6} | {'BL':>7} {'V2t':>7} {'V3':>7} | {'BL':>7} {'V2t':>7} {'V3':>7} |")
print("-" * 105)

for b in gapbs:
    data = {}
    for cfg, fn in gapbs_paths.items():
        data[cfg] = get_power_energy(fn(b))

    bl_ipc, bl_t, bl_p, bl_e = data['BL']
    v2_ipc, v2_t, v2_p, v2_e = data['V2t']
    v3_ipc, v3_t, v3_p, v3_e = data['V3']

    print(f"{b:<8} | {fmt(bl_ipc):>6} {fmt(v2_ipc):>6} {fmt(v3_ipc):>6} "
          f"| {fmt(bl_p,1):>7} {fmt(v2_p,1):>7} {fmt(v3_p,1):>7} "
          f"| {fmt(bl_e,3):>7} {fmt(v2_e,3):>7} {fmt(v3_e,3):>7} |")

print(f"\n{'Bench':<8} | {'IPC vs BL':>14} | {'Power vs BL':>14} | {'Energy vs BL':>14} | {'V3 vs V2t':>30}")
print(f"{'':8} | {'V2t':>6} {'V3':>6} | {'V2t':>6} {'V3':>6} | {'V2t':>6} {'V3':>6} | {'IPC':>9} {'Power':>9} {'Energy':>9}")
print("-" * 120)

for b in gapbs:
    data = {}
    for cfg, fn in gapbs_paths.items():
        data[cfg] = get_power_energy(fn(b))

    bl_ipc, bl_t, bl_p, bl_e = data['BL']
    v2_ipc, v2_t, v2_p, v2_e = data['V2t']
    v3_ipc, v3_t, v3_p, v3_e = data['V3']

    print(f"{b:<8} | {delta(v2_ipc,bl_ipc):>6} {delta(v3_ipc,bl_ipc):>6} "
          f"| {delta(v2_p,bl_p):>6} {delta(v3_p,bl_p):>6} "
          f"| {delta(v2_e,bl_e):>6} {delta(v3_e,bl_e):>6} "
          f"| {delta(v3_ipc,v2_ipc):>9} {delta(v3_p,v2_p):>9} {delta(v3_e,v2_e):>9}")
