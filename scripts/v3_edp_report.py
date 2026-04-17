#!/usr/bin/env python3
"""
Compute EDP family metrics for V2/V3 evaluation.

Metrics reported:
  - EDP  (Energy × Delay):     E × T,   standard equal-weight metric
  - ED⁰·⁵P (Energy × √Delay): E × √T,  energy-primary metric (n=0.5)
  - EWGM (Energy-Weighted Geometric Mean): (E/E_bl)^0.7 × (T/T_bl)^0.3
      α=0.7 energy weight, β=0.3 performance weight.

All three are "lower = better". Improvements reported as reduction%.
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
def get_ticks(p): return get_stat(p, r'simTicks\s+(\d+)')

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
    stats = os.path.join(run_dir, 'stats.txt')
    mcpat = os.path.join(run_dir, 'mcpat.out')
    ipc = get_ipc(stats)
    ticks = get_ticks(stats)
    power, energy = get_mcpat(mcpat)
    return ipc, ticks, power, energy

def edp(energy, ticks):
    """EDP = E × T (Joule-seconds). T = ticks / 1e12."""
    if energy is None or ticks is None: return None
    return energy * (ticks / 1e12)

def edhp(energy, ticks):
    """ED^0.5P = E × sqrt(T). Energy-primary metric."""
    if energy is None or ticks is None: return None
    return energy * math.sqrt(ticks / 1e12)

def ewgm(energy, ticks, bl_energy, bl_ticks, alpha=0.7, beta=0.3):
    """Energy-Weighted Geometric Mean = (E/E_bl)^alpha × (T/T_bl)^beta.
    alpha + beta = 1. alpha > beta means energy-primary."""
    if None in (energy, ticks, bl_energy, bl_ticks): return None
    if bl_energy == 0 or bl_ticks == 0: return None
    e_ratio = energy / bl_energy
    t_ratio = ticks / bl_ticks
    return (e_ratio ** alpha) * (t_ratio ** beta)

def improvement(v, bl):
    """Reduction % (positive = better)."""
    if v is None or bl is None or bl == 0: return None
    return (1 - v / bl) * 100

def fmt(v):
    if v is not None: return f"{v:>+6.1f}%"
    return "    N/A"

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 150)
print("  Composite Metrics: EDP / ED⁰·⁵P / EWGM")
print("  EDP = E × T (equal weight performance & energy)")
print("  ED⁰·⁵P = E × √T (energy-primary, n=0.5)")
print("  EWGM = (E/E_bl)^0.7 × (T/T_bl)^0.3 (70% energy weight, 30% performance weight)")
print("  All: positive improvement% = better")
print("=" * 150)

# ---- Microbenchmarks ----
micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

micro_bl = lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest')
micro_v2 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest')
micro_v3 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_default/latest')

print(f"\n  MICROBENCHMARKS")
print(f"{'Workload':<28} | {'---- V2 vs Baseline ----':^26} | {'---- V3 vs Baseline ----':^26} |")
print(f"{'':28} | {'EDP':>7} {'ED⁰·⁵P':>7} {'EWGM':>7} | {'EDP':>7} {'ED⁰·⁵P':>7} {'EWGM':>7} |")
print("-" * 95)

for wl in micro_wl:
    bl_ipc, bl_t, bl_p, bl_e = get_all(micro_bl(wl))
    v2_ipc, v2_t, v2_p, v2_e = get_all(micro_v2(wl))
    v3_ipc, v3_t, v3_p, v3_e = get_all(micro_v3(wl))

    bl_edp = edp(bl_e, bl_t); v2_edp = edp(v2_e, v2_t); v3_edp = edp(v3_e, v3_t)
    bl_ehp = edhp(bl_e, bl_t); v2_ehp = edhp(v2_e, v2_t); v3_ehp = edhp(v3_e, v3_t)
    bl_ewgm = 1.0  # baseline EWGM is always 1
    v2_ewgm_val = ewgm(v2_e, v2_t, bl_e, bl_t)
    v3_ewgm_val = ewgm(v3_e, v3_t, bl_e, bl_t)

    print(f"{wl:<28} | {fmt(improvement(v2_edp,bl_edp))} {fmt(improvement(v2_ehp,bl_ehp))} {fmt(improvement(v2_ewgm_val,1.0))} "
          f"| {fmt(improvement(v3_edp,bl_edp))} {fmt(improvement(v3_ehp,bl_ehp))} {fmt(improvement(v3_ewgm_val,1.0))} |")

# ---- GAPBS ----
gapbs = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']
gapbs_bl = lambda b: os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest')
gapbs_v2t = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest')
gapbs_v3 = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v3/latest')

print(f"\n  GAPBS FORMAL BENCHMARKS")
print(f"{'Benchmark':<28} | {'-- V2-tuned vs Baseline --':^26} | {'---- V3 vs Baseline ----':^26} |")
print(f"{'':28} | {'EDP':>7} {'ED⁰·⁵P':>7} {'EWGM':>7} | {'EDP':>7} {'ED⁰·⁵P':>7} {'EWGM':>7} |")
print("-" * 95)

for b in gapbs:
    bl_ipc, bl_t, bl_p, bl_e = get_all(gapbs_bl(b))
    v2_ipc, v2_t, v2_p, v2_e = get_all(gapbs_v2t(b))
    v3_ipc, v3_t, v3_p, v3_e = get_all(gapbs_v3(b))

    bl_edp = edp(bl_e, bl_t); v2_edp = edp(v2_e, v2_t); v3_edp = edp(v3_e, v3_t)
    bl_ehp = edhp(bl_e, bl_t); v2_ehp = edhp(v2_e, v2_t); v3_ehp = edhp(v3_e, v3_t)
    v2_ewgm_val = ewgm(v2_e, v2_t, bl_e, bl_t)
    v3_ewgm_val = ewgm(v3_e, v3_t, bl_e, bl_t)

    print(f"GAPBS-{b:<22} | {fmt(improvement(v2_edp,bl_edp))} {fmt(improvement(v2_ehp,bl_ehp))} {fmt(improvement(v2_ewgm_val,1.0))} "
          f"| {fmt(improvement(v3_edp,bl_edp))} {fmt(improvement(v3_ehp,bl_ehp))} {fmt(improvement(v3_ewgm_val,1.0))} |")

# ---- Summary ----
print(f"\n{'='*100}")
print(f"  SUMMARY (using EWGM as primary metric — 70% energy, 30% performance)")
print(f"{'='*100}")
print(f"\n{'Workload':<28} {'V2 EWGM':>9} {'V3 EWGM':>9} {'Winner':>8}")
print("-" * 58)

v2_wins = v3_wins = 0
v2_vals = []; v3_vals = []

all_configs = [
    (micro_wl, micro_bl, micro_v2, micro_v3, ''),
    (gapbs, gapbs_bl, gapbs_v2t, gapbs_v3, 'GAPBS-'),
]

for workloads, bl_fn, v2_fn, v3_fn, prefix in all_configs:
    for wl in workloads:
        bl_ipc, bl_t, bl_p, bl_e = get_all(bl_fn(wl))
        v2_ipc, v2_t, v2_p, v2_e = get_all(v2_fn(wl))
        v3_ipc, v3_t, v3_p, v3_e = get_all(v3_fn(wl))

        v2_ew = improvement(ewgm(v2_e, v2_t, bl_e, bl_t), 1.0)
        v3_ew = improvement(ewgm(v3_e, v3_t, bl_e, bl_t), 1.0)

        if v2_ew is not None: v2_vals.append(v2_ew)
        if v3_ew is not None: v3_vals.append(v3_ew)

        w = "V3" if (v3_ew or -999) > (v2_ew or -999) else "V2"
        if w == "V3": v3_wins += 1
        else: v2_wins += 1

        print(f"{prefix}{wl:<28} {fmt(v2_ew)} {fmt(v3_ew)} {w:>8}")

print(f"\nV2 wins: {v2_wins}, V3 wins: {v3_wins}")
if v2_vals: print(f"V2 average EWGM improvement: {sum(v2_vals)/len(v2_vals):+.1f}%")
if v3_vals: print(f"V3 average EWGM improvement: {sum(v3_vals)/len(v3_vals):+.1f}%")
