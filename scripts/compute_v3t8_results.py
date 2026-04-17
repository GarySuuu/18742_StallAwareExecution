#!/usr/bin/env python3
"""Compute v3t8 results: IPC, Energy, WPE for all 12 workloads."""

import re, os, csv

def get_ipc(stats_path):
    with open(stats_path) as f:
        for line in f:
            if 'system.cpu.ipc ' in line:
                return float(line.split()[1])
    return None

def get_energy(mcpat_path):
    with open(mcpat_path) as f:
        for line in f:
            if 'Total Runtime Energy' in line and 'J' in line:
                m = re.search(r'([\d.]+)\s*J', line)
                if m:
                    return float(m.group(1))
    return None

def wpe(bl_ipc, bl_energy, new_ipc, new_energy):
    ipc_ratio = new_ipc / bl_ipc
    energy_ratio = bl_energy / new_energy
    return (ipc_ratio ** 0.8) * (energy_ratio ** 0.2)

base_v3t8 = '/mnt/c/Users/garsy/Documents/18742project/gem5/runs/v3_multilevel/v3t8'
base_v3t4 = '/mnt/c/Users/garsy/Documents/18742project/gem5/runs/v3_multilevel/v3t4_cand2'
base_v3t7 = '/mnt/c/Users/garsy/Documents/18742project/gem5/runs/v3_multilevel/v3t7'
base_bl = '/mnt/c/Users/garsy/Documents/18742project/gem5/runs/v3_multilevel/baseline'

workloads = [
    'gapbs_bfs', 'gapbs_bc', 'gapbs_cc', 'gapbs_pr', 'gapbs_sssp', 'gapbs_tc',
    'balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
    'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce'
]

# ---- Full v3t8 results table ----
print("=" * 120)
print(f"{'Workload':<30s} {'BL IPC':>8s} {'v3t8 IPC':>9s} {'dIPC%':>8s} {'BL E(J)':>8s} {'v3t8 E(J)':>9s} {'dE%':>8s} {'WPE%':>8s}")
print("-" * 120)

gapbs_wpes = []
micro_wpes = []
all_wpes = []
results = {}

for wl in workloads:
    bl_ipc = get_ipc(base_bl + '/' + wl + '/latest/stats.txt')
    bl_energy = get_energy(base_bl + '/' + wl + '/latest/mcpat.out')
    new_ipc = get_ipc(base_v3t8 + '/' + wl + '/latest/stats.txt')
    new_energy = get_energy(base_v3t8 + '/' + wl + '/latest/mcpat.out')

    if bl_ipc and bl_energy and new_ipc and new_energy:
        dipc = (new_ipc/bl_ipc - 1)*100
        de = (new_energy/bl_energy - 1)*100
        w = wpe(bl_ipc, bl_energy, new_ipc, new_energy)
        dw = (w-1)*100
        print(f"{wl:<30s} {bl_ipc:>8.6f} {new_ipc:>9.6f} {dipc:>+8.2f}% {bl_energy:>8.5f} {new_energy:>9.5f} {de:>+8.2f}% {dw:>+8.2f}%")
        all_wpes.append(dw)
        results[wl] = {'ipc': new_ipc, 'energy': new_energy, 'dipc': dipc, 'de': de, 'dwpe': dw}
        if wl.startswith('gapbs_'):
            gapbs_wpes.append(dw)
        else:
            micro_wpes.append(dw)
    else:
        print(f"{wl:<30s} MISSING DATA (bl_ipc={bl_ipc}, bl_energy={bl_energy}, new_ipc={new_ipc}, new_energy={new_energy})")

print()
if gapbs_wpes:
    print(f"GAPBS avg WPE: {sum(gapbs_wpes)/len(gapbs_wpes):+.2f}%")
if micro_wpes:
    print(f"Micro avg WPE: {sum(micro_wpes)/len(micro_wpes):+.2f}%")
if all_wpes:
    print(f"Overall avg WPE: {sum(all_wpes)/len(all_wpes):+.2f}%")

# ---- Comparison table: v3t4, v3t7, v3t8 for GAPBS ----
print()
print("=" * 100)
print("GAPBS Comparison: v3t4 vs v3t7 vs v3t8")
print("-" * 100)
print(f"{'Bench':<12s} {'v3t4 dIPC%':>10s} {'v3t7 dIPC%':>10s} {'v3t8 dIPC%':>10s} {'v3t4 WPE%':>10s} {'v3t7 WPE%':>10s} {'v3t8 WPE%':>10s}")
print("-" * 100)

v3t4_wpes = []
v3t7_wpes = []
v3t8_wpes = []

for bench in ['bfs', 'bc', 'cc', 'pr', 'sssp', 'tc']:
    wl = 'gapbs_' + bench
    bl_ipc = get_ipc(base_bl + '/' + wl + '/latest/stats.txt')
    bl_energy = get_energy(base_bl + '/' + wl + '/latest/mcpat.out')

    t4_ipc = get_ipc(base_v3t4 + '/' + wl + '/latest/stats.txt')
    t4_energy = get_energy(base_v3t4 + '/' + wl + '/latest/mcpat.out')
    t7_ipc = get_ipc(base_v3t7 + '/' + wl + '/latest/stats.txt')
    t7_energy = get_energy(base_v3t7 + '/' + wl + '/latest/mcpat.out')
    t8_ipc = get_ipc(base_v3t8 + '/' + wl + '/latest/stats.txt')
    t8_energy = get_energy(base_v3t8 + '/' + wl + '/latest/mcpat.out')

    t4_dipc = (t4_ipc/bl_ipc - 1)*100
    t7_dipc = (t7_ipc/bl_ipc - 1)*100
    t8_dipc = (t8_ipc/bl_ipc - 1)*100

    t4_w = (wpe(bl_ipc, bl_energy, t4_ipc, t4_energy) - 1) * 100
    t7_w = (wpe(bl_ipc, bl_energy, t7_ipc, t7_energy) - 1) * 100
    t8_w = (wpe(bl_ipc, bl_energy, t8_ipc, t8_energy) - 1) * 100

    v3t4_wpes.append(t4_w)
    v3t7_wpes.append(t7_w)
    v3t8_wpes.append(t8_w)

    print(f"{wl:<12s} {t4_dipc:>+10.2f}% {t7_dipc:>+10.2f}% {t8_dipc:>+10.2f}% {t4_w:>+10.2f}% {t7_w:>+10.2f}% {t8_w:>+10.2f}%")

print("-" * 100)
print(f"{'AVG':<12s} {'':>10s} {'':>10s} {'':>10s} {sum(v3t4_wpes)/len(v3t4_wpes):>+10.2f}% {sum(v3t7_wpes)/len(v3t7_wpes):>+10.2f}% {sum(v3t8_wpes)/len(v3t8_wpes):>+10.2f}%")

# ---- Serialized-tight window distribution ----
print()
print("=" * 80)
print("Serialized-Tight Window Distribution (v3t8)")
print("-" * 80)
print(f"{'Bench':<12s} {'Total':>8s} {'Ser-Tight':>10s} {'%Tight':>8s} {'Normal':>10s} {'%Normal':>8s}")
print("-" * 80)

for bench in ['bfs', 'bc', 'cc', 'pr', 'sssp', 'tc']:
    wl = 'gapbs_' + bench
    f = base_v3t8 + '/' + wl + '/latest/adaptive_window_log.csv'
    with open(f) as fh:
        reader = csv.DictReader(fh)
        total = 0
        tight = 0
        for row in reader:
            total += 1
            if row['resource_profile_level'] == 'ser-tight':
                tight += 1
    normal = total - tight
    print(f"{wl:<12s} {total:>8d} {tight:>10d} {tight/total*100:>7.1f}% {normal:>10d} {normal/total*100:>7.1f}%")
