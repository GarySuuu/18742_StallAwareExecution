#!/usr/bin/env python3
"""
Compute PEB (Performance-Energy Benefit) for all experiments.
PEB = (IPC_gain% + Power_saving% + Energy_saving%) / 3
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
            if 'System:' in line:
                in_system = True
                continue
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

def peb(ipc, power, energy, bl_ipc, bl_power, bl_energy):
    """PEB = (1×dIPC + 2×PowerSaving + 2×EnergySaving) / 5
    Weights: IPC=1, Power=2, Energy=2. Energy/Power improvements valued 2x over IPC."""
    if None in (ipc, power, energy, bl_ipc, bl_power, bl_energy):
        return None
    ipc_gain = (ipc / bl_ipc - 1) * 100
    power_saving = (1 - power / bl_power) * 100
    energy_saving = (1 - energy / bl_energy) * 100
    return (1 * ipc_gain + 2 * power_saving + 2 * energy_saving) / 5

def delta(v, bl):
    if v and bl and bl != 0: return (v/bl-1)*100
    return None

def fmt_pct(v):
    if v is not None: return f"{v:>+6.1f}%"
    return "    N/A"

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 140)
print("  PEB (Performance-Energy Benefit) = (1×dIPC + 2×PowerSaving + 2×EnergySaving) / 5")
print("  Weights: IPC=1, Power=2, Energy=2. PEB > 0 = improvement. Higher = better.")
print("=" * 140)

# ---- Microbenchmarks ----
print("\n  MICROBENCHMARKS")
print(f"{'Workload':<28} | {'dIPC':>7} {'dPower':>7} {'dEnergy':>7} {'PEB':>7} | {'dIPC':>7} {'dPower':>7} {'dEnergy':>7} {'PEB':>7} |")
print(f"{'':28} | {'--- V2 vs Baseline ---':^30} | {'--- V3 vs Baseline ---':^30} |")
print("-" * 105)

micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

micro_bl = lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest')
micro_v2 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest')
micro_v3 = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_default/latest')

for wl in micro_wl:
    bl_ipc, bl_p, bl_e = get_all(micro_bl(wl))
    v2_ipc, v2_p, v2_e = get_all(micro_v2(wl))
    v3_ipc, v3_p, v3_e = get_all(micro_v3(wl))

    v2_peb = peb(v2_ipc, v2_p, v2_e, bl_ipc, bl_p, bl_e)
    v3_peb = peb(v3_ipc, v3_p, v3_e, bl_ipc, bl_p, bl_e)

    v2_di = delta(v2_ipc, bl_ipc)
    v2_dp = delta(v2_p, bl_p)
    v2_de = delta(v2_e, bl_e)
    v3_di = delta(v3_ipc, bl_ipc)
    v3_dp = delta(v3_p, bl_p)
    v3_de = delta(v3_e, bl_e)

    # Negate power/energy delta for display (saving = positive)
    def saving(d): return -d if d is not None else None

    print(f"{wl:<28} | {fmt_pct(v2_di)} {fmt_pct(saving(v2_dp))} {fmt_pct(saving(v2_de))} {fmt_pct(v2_peb)} "
          f"| {fmt_pct(v3_di)} {fmt_pct(saving(v3_dp))} {fmt_pct(saving(v3_de))} {fmt_pct(v3_peb)} |")

# ---- GAPBS ----
print(f"\n  GAPBS FORMAL BENCHMARKS")
print(f"{'Benchmark':<28} | {'dIPC':>7} {'dPower':>7} {'dEnergy':>7} {'PEB':>7} | {'dIPC':>7} {'dPower':>7} {'dEnergy':>7} {'PEB':>7} |")
print(f"{'':28} | {'--- V2-tuned vs Baseline ---':^30} | {'--- V3 vs Baseline ---':^30} |")
print("-" * 105)

gapbs = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']
gapbs_bl = lambda b: os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest')
gapbs_v2t = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest')
gapbs_v3 = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v3/latest')

for b in gapbs:
    bl_ipc, bl_p, bl_e = get_all(gapbs_bl(b))
    v2_ipc, v2_p, v2_e = get_all(gapbs_v2t(b))
    v3_ipc, v3_p, v3_e = get_all(gapbs_v3(b))

    v2_peb_val = peb(v2_ipc, v2_p, v2_e, bl_ipc, bl_p, bl_e)
    v3_peb_val = peb(v3_ipc, v3_p, v3_e, bl_ipc, bl_p, bl_e)

    v2_di = delta(v2_ipc, bl_ipc)
    v2_dp = delta(v2_p, bl_p)
    v2_de = delta(v2_e, bl_e)
    v3_di = delta(v3_ipc, bl_ipc)
    v3_dp = delta(v3_p, bl_p)
    v3_de = delta(v3_e, bl_e)

    def saving(d): return -d if d is not None else None

    print(f"GAPBS-{b:<22} | {fmt_pct(v2_di)} {fmt_pct(saving(v2_dp))} {fmt_pct(saving(v2_de))} {fmt_pct(v2_peb_val)} "
          f"| {fmt_pct(v3_di)} {fmt_pct(saving(v3_dp))} {fmt_pct(saving(v3_de))} {fmt_pct(v3_peb_val)} |")

# ---- Summary ----
print("\n" + "=" * 80)
print("  PEB SUMMARY")
print("=" * 80)
print(f"\n{'Workload':<28} {'V2 PEB':>8} {'V3 PEB':>8} {'Winner':>8}")
print("-" * 55)

v3_wins = v2_wins = ties = 0
v2_pebs = []
v3_pebs = []

for wl in micro_wl:
    bl_ipc, bl_p, bl_e = get_all(micro_bl(wl))
    v2_ipc, v2_p, v2_e = get_all(micro_v2(wl))
    v3_ipc, v3_p, v3_e = get_all(micro_v3(wl))
    v2_peb_val = peb(v2_ipc, v2_p, v2_e, bl_ipc, bl_p, bl_e)
    v3_peb_val = peb(v3_ipc, v3_p, v3_e, bl_ipc, bl_p, bl_e)
    if v2_peb_val is not None: v2_pebs.append(v2_peb_val)
    if v3_peb_val is not None: v3_pebs.append(v3_peb_val)
    w = "V3" if (v3_peb_val or 0) > (v2_peb_val or 0) else ("V2" if (v2_peb_val or 0) > (v3_peb_val or 0) else "tie")
    if w == "V3": v3_wins += 1
    elif w == "V2": v2_wins += 1
    else: ties += 1
    print(f"{wl:<28} {fmt_pct(v2_peb_val)} {fmt_pct(v3_peb_val)} {w:>8}")

for b in gapbs:
    bl_ipc, bl_p, bl_e = get_all(gapbs_bl(b))
    v2_ipc, v2_p, v2_e = get_all(gapbs_v2t(b))
    v3_ipc, v3_p, v3_e = get_all(gapbs_v3(b))
    v2_peb_val = peb(v2_ipc, v2_p, v2_e, bl_ipc, bl_p, bl_e)
    v3_peb_val = peb(v3_ipc, v3_p, v3_e, bl_ipc, bl_p, bl_e)
    if v2_peb_val is not None: v2_pebs.append(v2_peb_val)
    if v3_peb_val is not None: v3_pebs.append(v3_peb_val)
    w = "V3" if (v3_peb_val or 0) > (v2_peb_val or 0) else ("V2" if (v2_peb_val or 0) > (v3_peb_val or 0) else "tie")
    if w == "V3": v3_wins += 1
    elif w == "V2": v2_wins += 1
    else: ties += 1
    print(f"GAPBS-{b:<22} {fmt_pct(v2_peb_val)} {fmt_pct(v3_peb_val)} {w:>8}")

print(f"\nV3 wins: {v3_wins}, V2 wins: {v2_wins}, ties: {ties}")
if v2_pebs: print(f"V2 average PEB: {sum(v2_pebs)/len(v2_pebs):+.1f}%")
if v3_pebs: print(f"V3 average PEB: {sum(v3_pebs)/len(v3_pebs):+.1f}%")
