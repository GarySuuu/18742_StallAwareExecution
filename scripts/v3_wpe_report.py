#!/usr/bin/env python3
"""
WPE (Weighted Performance-Efficiency) Score.
WPE = (IPC_ratio)^0.8 × (1/Power_ratio)^0.08 × (1/Energy_ratio)^0.12
Exchange rate: 1% IPC ≈ 7% Energy ≈ 10.5% Power
"""
import os, re

def get_stat(path, pattern):
    if not os.path.exists(path): return None
    with open(path) as f:
        for line in f:
            m = re.search(pattern, line)
            if m: return float(m.group(1))
    return None

def get_ipc(p): return get_stat(p, r'system\.cpu\.ipc\s+([\d.]+)')

def get_mcpat(mcpat_path):
    if not os.path.exists(mcpat_path): return None, None
    power = energy = None
    in_system = False
    with open(mcpat_path) as f:
        for line in f:
            if 'System:' in line: in_system = True; continue
            if in_system:
                m = re.search(r'Runtime Dynamic Power\s*=\s*([\d.]+)\s*W', line)
                if m and power is None: power = float(m.group(1))
                m2 = re.search(r'Total Runtime Energy\s*=\s*([\d.]+)\s*J', line)
                if m2 and energy is None: energy = float(m2.group(1))
                if power is not None and energy is not None: break
    return power, energy

def get_all(run_dir):
    ipc = get_ipc(os.path.join(run_dir, 'stats.txt'))
    power, energy = get_mcpat(os.path.join(run_dir, 'mcpat.out'))
    return ipc, power, energy

def wpe(ipc, power, energy, bl_ipc, bl_power, bl_energy):
    if None in (ipc, energy, bl_ipc, bl_energy): return None
    if bl_ipc == 0 or bl_energy == 0: return None
    return ((ipc/bl_ipc)**0.8) * ((bl_energy/energy)**0.2)

def fmt(v):
    if v is not None: return f"{(v-1)*100:>+6.1f}%"
    return "    N/A"

def d(new, bl):
    if new is None or bl is None or bl == 0: return "     N/A"
    return f"{(new/bl-1)*100:>+6.1f}%"

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 150)
print("  WPE (Weighted Performance-Efficiency) = (IPC_ratio)^0.8 × (Energy_bl/Energy_new)^0.2")
print("  Two independent dimensions (no double-counting: Energy = Power × Time)")
print("  Weights: IPC=0.8, Energy=0.2.  Exchange rate: 1% IPC ≈ 4% Energy")
print("=" * 150)

micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']
micro_bl = lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest')
micro_v2 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest')
micro_v3 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_default/latest')

gapbs = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']
gapbs_bl = lambda b: os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest')
gapbs_v2t = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest')
gapbs_v3 = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v3/latest')

# Full detail table
for label, workloads, bl_fn, v2_fn, v3_fn, prefix, v2_label in [
    ("MICROBENCHMARKS", micro_wl, micro_bl, micro_v2, micro_v3, '', 'V2'),
    ("GAPBS FORMAL BENCHMARKS", gapbs, gapbs_bl, gapbs_v2t, gapbs_v3, 'GAPBS-', 'V2t'),
]:
    print(f"\n  {label}")
    print(f"{'Workload':<28} | {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'WPE':>7} | {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'WPE':>7} |")
    print(f"{'':28} | {'--- '+v2_label+' vs Baseline ---':^30} | {'--- V3 vs Baseline ---':^30} |")
    print("-" * 107)
    for wl in workloads:
        bl = get_all(bl_fn(wl))
        v2 = get_all(v2_fn(wl))
        v3 = get_all(v3_fn(wl))
        v2w = wpe(*v2, *bl)
        v3w = wpe(*v3, *bl)
        name = f"{prefix}{wl}" if prefix else wl
        print(f"{name:<28} | {d(v2[0],bl[0])} {d(v2[1],bl[1])} {d(v2[2],bl[2])} {fmt(v2w)} "
              f"| {d(v3[0],bl[0])} {d(v3[1],bl[1])} {d(v3[2],bl[2])} {fmt(v3w)} |")

# Summary
print(f"\n{'='*80}")
print(f"  WPE SUMMARY")
print(f"{'='*80}")
print(f"\n{'Workload':<28} {'V2 WPE':>8} {'V3 WPE':>8} {'Winner':>8}")
print("-" * 55)

v2w_all = 0; v3w_all = 0; v2_vals = []; v3_vals = []
for workloads, bl_fn, v2_fn, v3_fn, prefix in [
    (micro_wl, micro_bl, micro_v2, micro_v3, ''),
    (gapbs, gapbs_bl, gapbs_v2t, gapbs_v3, 'GAPBS-'),
]:
    for wl in workloads:
        bl = get_all(bl_fn(wl))
        v2 = get_all(v2_fn(wl))
        v3 = get_all(v3_fn(wl))
        v2w = wpe(*v2, *bl); v3w = wpe(*v3, *bl)
        v2i = (v2w-1)*100 if v2w else None
        v3i = (v3w-1)*100 if v3w else None
        if v2i is not None: v2_vals.append(v2i)
        if v3i is not None: v3_vals.append(v3i)
        w = "V3" if (v3i or -999) > (v2i or -999) else "V2"
        if w == "V3": v3w_all += 1
        else: v2w_all += 1
        name = f"{prefix}{wl}" if prefix else wl
        print(f"{name:<28} {fmt(v2w):>8} {fmt(v3w):>8} {w:>8}")

print(f"\nV2 wins: {v2w_all}, V3 wins: {v3w_all}")
if v2_vals: print(f"V2 average WPE: {sum(v2_vals)/len(v2_vals):+.1f}%")
if v3_vals: print(f"V3 average WPE: {sum(v3_vals)/len(v3_vals):+.1f}%")
