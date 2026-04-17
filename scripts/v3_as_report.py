#!/usr/bin/env python3
"""
Compute AS (Adaptive Score) for all experiments.

AS = (IPC_ratio)^0.5 × (1/Power_ratio)^0.2 × (1/Energy_ratio)^0.3
Weights: IPC=0.5, Power=0.2, Energy=0.3 (sum=1.0)
IPC > Energy > Power

AS > 1 = improvement. Reported as (AS-1) × 100%.
"""
import os, re, math

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

def adaptive_score(ipc, power, energy, bl_ipc, bl_power, bl_energy):
    if None in (ipc, power, energy, bl_ipc, bl_power, bl_energy): return None
    if bl_ipc == 0 or bl_power == 0 or bl_energy == 0: return None
    ipc_r = ipc / bl_ipc
    pwr_r = bl_power / power     # inverted: higher = better
    eng_r = bl_energy / energy    # inverted: higher = better
    return (ipc_r ** 0.5) * (pwr_r ** 0.2) * (eng_r ** 0.3)

def as_pct(v):
    if v is None: return "     N/A"
    return f"{(v-1)*100:>+6.1f}%"

def d_pct(new, bl):
    if new is None or bl is None or bl == 0: return "     N/A"
    return f"{(new/bl-1)*100:>+6.1f}%"

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 140)
print("  AS (Adaptive Score) = (IPC_ratio)^0.5 × (1/Power_ratio)^0.2 × (1/Energy_ratio)^0.3")
print("  Weights: IPC=0.5, Energy=0.3, Power=0.2.  AS improvement% = (AS - 1) × 100%")
print("=" * 140)

# ---- Microbenchmarks ----
micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

micro_bl = lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest')
micro_v2 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest')
micro_v3 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_default/latest')

print(f"\n  MICROBENCHMARKS (50M instructions)")
print(f"{'Workload':<28} | {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'AS':>7} | {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'AS':>7} |")
print(f"{'':28} | {'-------- V2 vs Baseline --------':^30} | {'-------- V3 vs Baseline --------':^30} |")
print("-" * 107)

for wl in micro_wl:
    bl = get_all(micro_bl(wl))
    v2 = get_all(micro_v2(wl))
    v3 = get_all(micro_v3(wl))

    v2_as = adaptive_score(*v2, *bl)
    v3_as = adaptive_score(*v3, *bl)

    print(f"{wl:<28} | {d_pct(v2[0],bl[0])} {d_pct(v2[1],bl[1])} {d_pct(v2[2],bl[2])} {as_pct(v2_as)} "
          f"| {d_pct(v3[0],bl[0])} {d_pct(v3[1],bl[1])} {d_pct(v3[2],bl[2])} {as_pct(v3_as)} |")

# ---- GAPBS ----
gapbs = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']
gapbs_bl = lambda b: os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest')
gapbs_v2t = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest')
gapbs_v3 = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v3/latest')

print(f"\n  GAPBS FORMAL BENCHMARKS (g20, 50M instructions)")
print(f"{'Benchmark':<28} | {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'AS':>7} | {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'AS':>7} |")
print(f"{'':28} | {'---- V2-tuned vs Baseline ----':^30} | {'-------- V3 vs Baseline --------':^30} |")
print("-" * 107)

for b in gapbs:
    bl = get_all(gapbs_bl(b))
    v2 = get_all(gapbs_v2t(b))
    v3 = get_all(gapbs_v3(b))

    v2_as = adaptive_score(*v2, *bl)
    v3_as = adaptive_score(*v3, *bl)

    print(f"GAPBS-{b:<22} | {d_pct(v2[0],bl[0])} {d_pct(v2[1],bl[1])} {d_pct(v2[2],bl[2])} {as_pct(v2_as)} "
          f"| {d_pct(v3[0],bl[0])} {d_pct(v3[1],bl[1])} {d_pct(v3[2],bl[2])} {as_pct(v3_as)} |")

# ---- Summary ----
print(f"\n{'='*80}")
print(f"  AS SUMMARY")
print(f"{'='*80}")
print(f"\n{'Workload':<28} {'V2 AS':>8} {'V3 AS':>8} {'Winner':>8}")
print("-" * 55)

v2_wins = v3_wins = 0
v2_vals = []; v3_vals = []

configs_list = [
    (micro_wl, micro_bl, micro_v2, micro_v3, ''),
    (gapbs, gapbs_bl, gapbs_v2t, gapbs_v3, 'GAPBS-'),
]

for workloads, bl_fn, v2_fn, v3_fn, prefix in configs_list:
    for wl in workloads:
        bl = get_all(bl_fn(wl))
        v2 = get_all(v2_fn(wl))
        v3 = get_all(v3_fn(wl))

        v2_as = adaptive_score(*v2, *bl)
        v3_as = adaptive_score(*v3, *bl)

        v2_imp = (v2_as - 1) * 100 if v2_as else None
        v3_imp = (v3_as - 1) * 100 if v3_as else None

        if v2_imp is not None: v2_vals.append(v2_imp)
        if v3_imp is not None: v3_vals.append(v3_imp)

        w = "V3" if (v3_imp or -999) > (v2_imp or -999) else "V2"
        if w == "V3": v3_wins += 1
        else: v2_wins += 1

        print(f"{prefix}{wl:<22} {as_pct(v2_as):>8} {as_pct(v3_as):>8} {w:>8}")

print(f"\nV2 wins: {v2_wins}, V3 wins: {v3_wins}")
if v2_vals: print(f"V2 average AS: {sum(v2_vals)/len(v2_vals):+.1f}%")
if v3_vals: print(f"V3 average AS: {sum(v3_vals)/len(v3_vals):+.1f}%")
