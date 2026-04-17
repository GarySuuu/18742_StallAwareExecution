#!/usr/bin/env python3
"""Compare V3 compiled test results: baseline / v2_ref / v3_no_ema / v3_default."""
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
workloads = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
             'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']

configs = [
    ('baseline',    lambda wl: os.path.join(gem5, f'runs/baseline_v3/{wl}/latest/stats.txt')),
    ('v2_ref',      lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest/stats.txt')),
    ('v3_no_ema',   lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_no_ema/latest/stats.txt')),
    ('v3_default',  lambda wl: os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v3_default/latest/stats.txt')),
]

# IPC table
print("=" * 130)
print("  IPC: baseline / V2 / V3(no EMA) / V3(EMA)")
print("  V3 params: fw=6, cap=56, iqcap=26, lsqcap=28. EMA alpha=0.3")
print("=" * 130)
hdr = f"{'Workload':<28}"
for name, _ in configs:
    hdr += f" {name:>11}"
hdr += "  | V2 vs BL  V3noEMA   V3+EMA   EMA effect"
print(hdr)
print("-" * 130)

for wl in workloads:
    ipcs = {}
    for name, fn in configs:
        ipcs[name] = get_ipc(fn(wl))
    bl = ipcs.get('baseline')
    if not bl: continue

    row = f"{wl:<28}"
    for name, _ in configs:
        v = ipcs[name]
        row += f" {v:>11.4f}" if v else "        N/A"

    def delta(v):
        if v and bl: return f"{(v/bl-1)*100:>+7.1f}%"
        return "     N/A"

    v3ne = ipcs.get('v3_no_ema')
    v3e = ipcs.get('v3_default')
    ema_eff = ""
    if v3ne and v3e:
        ema_eff = f"{(v3e/v3ne-1)*100:>+7.1f}%"

    row += f"  | {delta(ipcs.get('v2_ref'))} {delta(v3ne)} {delta(v3e)}   {ema_eff}"
    print(row)

# Conservative % table
print()
print("=" * 100)
print("  Conservative Window %")
print("=" * 100)
hdr = f"{'Workload':<28}"
for name, fn in configs[1:]:
    hdr += f" {name:>12}"
print(hdr)
print("-" * 80)

for wl in workloads:
    row = f"{wl:<28}"
    for name, fn in configs[1:]:
        d = os.path.dirname(fn(wl))
        p = get_cons_pct(d)
        if p is not None:
            row += f" {p:>10.1f}%"
        else:
            row += "          N/A"
    print(row)

# simTicks table
print()
print("=" * 130)
print("  simTicks (billions, lower=faster)")
print("=" * 130)
hdr = f"{'Workload':<28}"
for name, _ in configs:
    hdr += f" {name:>11}"
hdr += "  | V2 vs BL  V3noEMA   V3+EMA"
print(hdr)
print("-" * 130)

for wl in workloads:
    ticks = {}
    for name, fn in configs:
        ticks[name] = get_ticks(fn(wl))
    bl = ticks.get('baseline')
    if not bl: continue

    row = f"{wl:<28}"
    for name, _ in configs:
        v = ticks[name]
        row += f" {v/1e9:>11.2f}" if v else "        N/A"

    def delta(v):
        if v and bl: return f"{(v/bl-1)*100:>+7.1f}%"
        return "     N/A"

    row += f"  | {delta(ticks.get('v2_ref'))} {delta(ticks.get('v3_no_ema'))} {delta(ticks.get('v3_default'))}"
    print(row)
