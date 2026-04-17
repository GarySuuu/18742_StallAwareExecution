#!/usr/bin/env python3
"""Generate complete V3 report: microbenchmarks + GAPBS, baseline/V2/V3 comparison."""
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

def get_cons_pct(stats_dir):
    log = os.path.join(stats_dir, 'adaptive_window_log.csv')
    if not os.path.exists(log): return None
    try:
        with open(log) as f:
            reader = csv.DictReader(f)
            total = cons = 0
            for r in reader:
                total += 1
                if 'conservative' in r.get('applied_mode', '').lower():
                    cons += 1
        return cons / total * 100 if total else None
    except: return None

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def delta(v, bl):
    if v and bl and bl != 0:
        return f"{(v/bl-1)*100:>+6.1f}%"
    return "    N/A"

def fmt(v, decimals=3):
    if v is not None:
        return f"{v:.{decimals}f}"
    return "N/A"

# =====================================================================
# PART 1: Microbenchmarks
# =====================================================================
print("=" * 130)
print("  PART 1: Microbenchmarks (50M instructions)")
print("=" * 130)

micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

micro_configs = {
    'baseline': lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest/stats.txt'),
    'V2': lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest/stats.txt'),
    'V3': lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_default/latest/stats.txt'),
}

print(f"\n{'Workload':<28} {'BL IPC':>8} {'V2 IPC':>8} {'V3 IPC':>8} | {'V2vsBL':>8} {'V3vsBL':>8} {'V3vsV2':>8} | {'V2 cons%':>8} {'V3 cons%':>8}")
print("-" * 120)

for wl in micro_wl:
    bl_ipc = get_ipc(micro_configs['baseline'](wl))
    v2_ipc = get_ipc(micro_configs['V2'](wl))
    v3_ipc = get_ipc(micro_configs['V3'](wl))

    v2_dir = os.path.dirname(micro_configs['V2'](wl))
    v3_dir = os.path.dirname(micro_configs['V3'](wl))
    v2_cons = get_cons_pct(v2_dir)
    v3_cons = get_cons_pct(v3_dir)

    v3_vs_v2 = delta(v3_ipc, v2_ipc) if v2_ipc else "    N/A"

    print(f"{wl:<28} {fmt(bl_ipc):>8} {fmt(v2_ipc):>8} {fmt(v3_ipc):>8} | "
          f"{delta(v2_ipc, bl_ipc):>8} {delta(v3_ipc, bl_ipc):>8} {v3_vs_v2:>8} | "
          f"{f'{v2_cons:.0f}%' if v2_cons is not None else 'N/A':>8} "
          f"{f'{v3_cons:.0f}%' if v3_cons is not None else 'N/A':>8}")

# simTicks for microbenchmarks
print(f"\n{'Workload':<28} {'BL ticks':>12} {'V2 ticks':>12} {'V3 ticks':>12} | {'V2vsBL':>8} {'V3vsBL':>8} {'V3vsV2':>8}")
print("-" * 105)
for wl in micro_wl:
    bl = get_ticks(micro_configs['baseline'](wl))
    v2 = get_ticks(micro_configs['V2'](wl))
    v3 = get_ticks(micro_configs['V3'](wl))
    v3v2 = delta(v3, v2) if v2 else "    N/A"
    print(f"{wl:<28} {bl/1e9 if bl else 0:>11.2f}B {v2/1e9 if v2 else 0:>11.2f}B {v3/1e9 if v3 else 0:>11.2f}B | "
          f"{delta(v2, bl):>8} {delta(v3, bl):>8} {v3v2:>8}")

# =====================================================================
# PART 2: GAPBS Formal Benchmarks
# =====================================================================
print("\n\n" + "=" * 130)
print("  PART 2: GAPBS Formal Benchmarks (g20, 50M instructions)")
print("=" * 130)

gapbs = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']

gapbs_configs = {
    'baseline': lambda b: os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest/stats.txt'),
    'V2': lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_ref/latest/stats.txt'),
    'V2tuned': lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest/stats.txt'),
    'V3': lambda b: os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v3/latest/stats.txt'),
}

print(f"\n{'Benchmark':<12} {'BL IPC':>8} {'V2 IPC':>8} {'V2t IPC':>8} {'V3 IPC':>8} | {'V2vsBL':>8} {'V2tvsBL':>8} {'V3vsBL':>8} {'V3vsV2t':>8} | {'V2 c%':>6} {'V2t c%':>6} {'V3 c%':>6}")
print("-" * 130)

for b in gapbs:
    bl = get_ipc(gapbs_configs['baseline'](b))
    v2 = get_ipc(gapbs_configs['V2'](b))
    v2t = get_ipc(gapbs_configs['V2tuned'](b))
    v3 = get_ipc(gapbs_configs['V3'](b))

    v2_dir = os.path.dirname(gapbs_configs['V2'](b))
    v2t_dir = os.path.dirname(gapbs_configs['V2tuned'](b))
    v3_dir = os.path.dirname(gapbs_configs['V3'](b))

    v2c = get_cons_pct(v2_dir)
    v2tc = get_cons_pct(v2t_dir)
    v3c = get_cons_pct(v3_dir)

    def cpct(v):
        return f"{v:.0f}%" if v is not None else "N/A"

    print(f"{b:<12} {fmt(bl):>8} {fmt(v2):>8} {fmt(v2t):>8} {fmt(v3):>8} | "
          f"{delta(v2, bl):>8} {delta(v2t, bl):>8} {delta(v3, bl):>8} {delta(v3, v2t):>8} | "
          f"{cpct(v2c):>6} {cpct(v2tc):>6} {cpct(v3c):>6}")

# simTicks for GAPBS
print(f"\n{'Benchmark':<12} {'BL ticks':>12} {'V2 ticks':>12} {'V2t ticks':>12} {'V3 ticks':>12} | {'V2vsBL':>8} {'V2tvsBL':>8} {'V3vsBL':>8}")
print("-" * 120)
for b in gapbs:
    bl = get_ticks(gapbs_configs['baseline'](b))
    v2 = get_ticks(gapbs_configs['V2'](b))
    v2t = get_ticks(gapbs_configs['V2tuned'](b))
    v3 = get_ticks(gapbs_configs['V3'](b))
    print(f"{b:<12} {bl/1e9 if bl else 0:>11.2f}B {v2/1e9 if v2 else 0:>11.2f}B {v2t/1e9 if v2t else 0:>11.2f}B {v3/1e9 if v3 else 0:>11.2f}B | "
          f"{delta(v2, bl):>8} {delta(v2t, bl):>8} {delta(v3, bl):>8}")

# =====================================================================
# SUMMARY
# =====================================================================
print("\n\n" + "=" * 80)
print("  SUMMARY: V3 vs V2 across all workloads")
print("=" * 80)

all_v3_better = 0
all_v3_worse = 0
all_v3_neutral = 0

print(f"\n{'Workload':<28} {'V2 vs BL':>10} {'V3 vs BL':>10} {'Winner':>8}")
print("-" * 60)

for wl in micro_wl:
    bl = get_ipc(micro_configs['baseline'](wl))
    v2 = get_ipc(micro_configs['V2'](wl))
    v3 = get_ipc(micro_configs['V3'](wl))
    if bl and v2 and v3:
        v2d = (v2/bl-1)*100
        v3d = (v3/bl-1)*100
        if abs(v3d - v2d) < 0.5:
            winner = "tie"
            all_v3_neutral += 1
        elif v3d > v2d:
            winner = "V3"
            all_v3_better += 1
        else:
            winner = "V2"
            all_v3_worse += 1
        print(f"{wl:<28} {v2d:>+9.1f}% {v3d:>+9.1f}% {winner:>8}")

for b in gapbs:
    bl = get_ipc(gapbs_configs['baseline'](b))
    v2t = get_ipc(gapbs_configs['V2tuned'](b))
    v3 = get_ipc(gapbs_configs['V3'](b))
    if bl and v2t and v3:
        v2d = (v2t/bl-1)*100
        v3d = (v3/bl-1)*100
        if abs(v3d - v2d) < 0.5:
            winner = "tie"
            all_v3_neutral += 1
        elif v3d > v2d:
            winner = "V3"
            all_v3_better += 1
        else:
            winner = "V2t"
            all_v3_worse += 1
        print(f"GAPBS-{b:<22} {v2d:>+9.1f}% {v3d:>+9.1f}% {winner:>8}")

print(f"\nV3 better: {all_v3_better}, V2 better: {all_v3_worse}, tie: {all_v3_neutral}")
