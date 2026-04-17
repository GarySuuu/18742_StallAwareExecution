#!/usr/bin/env python3
"""Analyze V3 multi-level results with WPE."""
import os, re, csv

def get_stat(path, pattern):
    if not os.path.exists(path): return None
    with open(path) as f:
        for line in f:
            m = re.search(pattern, line)
            if m: return float(m.group(1))
    return None

def get_ipc(p): return get_stat(p, r'system\.cpu\.ipc\s+([\d.]+)')
def get_ticks(p): return get_stat(p, r'simTicks\s+(\d+)')

def get_mcpat(p):
    if not os.path.exists(p): return None, None
    power = energy = None
    in_sys = False
    with open(p) as f:
        for line in f:
            if 'System:' in line: in_sys = True; continue
            if in_sys:
                m = re.search(r'Runtime Dynamic Power\s*=\s*([\d.]+)\s*W', line)
                if m and power is None: power = float(m.group(1))
                m2 = re.search(r'Total Runtime Energy\s*=\s*([\d.]+)\s*J', line)
                if m2 and energy is None: energy = float(m2.group(1))
                if power is not None and energy is not None: break
    return power, energy

def get_all(d):
    ipc = get_ipc(os.path.join(d, 'stats.txt'))
    power, energy = get_mcpat(os.path.join(d, 'mcpat.out'))
    return ipc, power, energy

def get_modes(d):
    log = os.path.join(d, 'adaptive_window_log.csv')
    if not os.path.exists(log): return {}
    modes = {}
    total = 0
    with open(log) as f:
        for r in csv.DictReader(f):
            total += 1
            m = r.get('applied_mode', '')
            modes[m] = modes.get(m, 0) + 1
    return {k: f"{v/total*100:.0f}%" for k, v in modes.items()} if total else {}

def wpe(ipc, energy, bl_ipc, bl_energy):
    if None in (ipc, energy, bl_ipc, bl_energy) or bl_ipc == 0 or bl_energy == 0:
        return None
    return ((ipc/bl_ipc)**0.8) * ((bl_energy/energy)**0.2)

def fmt(v): return f"{(v-1)*100:>+6.1f}%" if v else "    N/A"
def d_pct(n, b): return f"{(n/b-1)*100:>+6.1f}%" if n and b and b!=0 else "    N/A"

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ml = os.path.join(gem5, 'runs', 'v3_multilevel')

# Also load old V2 results for comparison
old_v2_micro = lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest')
old_v2_gapbs = lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest')
old_bl_micro = lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest')
old_bl_gapbs = lambda b: os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest')

print("=" * 150)
print("  V3 Multi-Level Results: WPE = (IPC_ratio)^0.8 × (Energy_bl/Energy_new)^0.2")
print("  Modes: Aggressive / LightConservative (sweet spot) / Conservative (deep)")
print("=" * 150)

micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

print(f"\n  MICROBENCHMARKS")
print(f"{'Workload':<28} | {'BL IPC':>7} {'V2 IPC':>7} {'V3ml IPC':>8} | {'V2 dEng':>7} {'V3ml dEng':>9} | {'V2 WPE':>7} {'V3ml WPE':>8} | Mode distribution")
print("-" * 140)

for wl in micro_wl:
    bl = get_all(os.path.join(ml, f'baseline/{wl}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml/{wl}/latest'))
    # V2 from old runs
    v2_data = get_all(old_v2_micro(wl))
    bl_old = get_all(old_bl_micro(wl))

    v2_wpe = wpe(v2_data[0], v2_data[2], bl_old[0], bl_old[2])
    v3_wpe = wpe(v3[0], v3[2], bl[0], bl[2])

    modes = get_modes(os.path.join(ml, f'v3ml/{wl}/latest'))
    mode_str = ' '.join(f"{k}:{v}" for k, v in sorted(modes.items()))

    print(f"{wl:<28} | {bl[0] or 0:>7.3f} {v2_data[0] or 0:>7.3f} {v3[0] or 0:>8.3f} "
          f"| {d_pct(v2_data[2], bl_old[2]):>7} {d_pct(v3[2], bl[2]):>9} "
          f"| {fmt(v2_wpe):>7} {fmt(v3_wpe):>8} | {mode_str}")

gapbs = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']

print(f"\n  GAPBS")
print(f"{'Benchmark':<28} | {'BL IPC':>7} {'V2t IPC':>7} {'V3ml IPC':>8} | {'V2t dEng':>8} {'V3ml dEng':>9} | {'V2t WPE':>7} {'V3ml WPE':>8} | Mode distribution")
print("-" * 140)

for b in gapbs:
    bl = get_all(os.path.join(ml, f'baseline/gapbs_{b}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml/gapbs_{b}/latest'))
    v2_data = get_all(old_v2_gapbs(b))
    bl_old = get_all(old_bl_gapbs(b))

    v2_wpe = wpe(v2_data[0], v2_data[2], bl_old[0], bl_old[2])
    v3_wpe = wpe(v3[0], v3[2], bl[0], bl[2])

    modes = get_modes(os.path.join(ml, f'v3ml/gapbs_{b}/latest'))
    mode_str = ' '.join(f"{k}:{v}" for k, v in sorted(modes.items()))

    print(f"GAPBS-{b:<22} | {bl[0] or 0:>7.3f} {v2_data[0] or 0:>7.3f} {v3[0] or 0:>8.3f} "
          f"| {d_pct(v2_data[2], bl_old[2]):>8} {d_pct(v3[2], bl[2]):>9} "
          f"| {fmt(v2_wpe):>7} {fmt(v3_wpe):>8} | {mode_str}")

# Summary
print(f"\n{'='*80}")
print(f"  WPE SUMMARY: V2 vs V3-MultiLevel")
print(f"{'='*80}")
print(f"\n{'Workload':<28} {'V2 WPE':>8} {'V3ml WPE':>9} {'Winner':>8}")
print("-" * 58)

v2w = v3w = 0
v2_all = []; v3_all = []

for wl in micro_wl:
    bl = get_all(os.path.join(ml, f'baseline/{wl}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml/{wl}/latest'))
    v2_data = get_all(old_v2_micro(wl))
    bl_old = get_all(old_bl_micro(wl))
    v2_w = wpe(v2_data[0], v2_data[2], bl_old[0], bl_old[2])
    v3_w = wpe(v3[0], v3[2], bl[0], bl[2])
    v2_v = (v2_w-1)*100 if v2_w else None
    v3_v = (v3_w-1)*100 if v3_w else None
    if v2_v is not None: v2_all.append(v2_v)
    if v3_v is not None: v3_all.append(v3_v)
    w = "V3ml" if (v3_v or -999) > (v2_v or -999) else "V2"
    if w == "V3ml": v3w += 1
    else: v2w += 1
    print(f"{wl:<28} {fmt(v2_w):>8} {fmt(v3_w):>9} {w:>8}")

for b in gapbs:
    bl = get_all(os.path.join(ml, f'baseline/gapbs_{b}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml/gapbs_{b}/latest'))
    v2_data = get_all(old_v2_gapbs(b))
    bl_old = get_all(old_bl_gapbs(b))
    v2_w = wpe(v2_data[0], v2_data[2], bl_old[0], bl_old[2])
    v3_w = wpe(v3[0], v3[2], bl[0], bl[2])
    v2_v = (v2_w-1)*100 if v2_w else None
    v3_v = (v3_w-1)*100 if v3_w else None
    if v2_v is not None: v2_all.append(v2_v)
    if v3_v is not None: v3_all.append(v3_v)
    w = "V3ml" if (v3_v or -999) > (v2_v or -999) else "V2"
    if w == "V3ml": v3w += 1
    else: v2w += 1
    print(f"GAPBS-{b:<22} {fmt(v2_w):>8} {fmt(v3_w):>9} {w:>8}")

print(f"\nV2 wins: {v2w}, V3ml wins: {v3w}")
if v2_all: print(f"V2 average WPE: {sum(v2_all)/len(v2_all):+.1f}%")
if v3_all: print(f"V3ml average WPE: {sum(v3_all)/len(v3_all):+.1f}%")
