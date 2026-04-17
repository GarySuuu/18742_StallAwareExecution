#!/usr/bin/env python3
"""Compute WPE = (IPC_ratio)^0.8 * (Energy_bl/Energy_new)^0.2 for V2 and V3ml_t2."""

import math

# Baseline IPC and Energy (from v3_multilevel/baseline, same for both V2 and V3t2)
bl = {
    "balanced_pipeline_stress":  {"ipc": 2.907918, "energy": 3.31314},
    "phase_scan_mix":            {"ipc": 0.466612, "energy": 6.00512},
    "branch_entropy":            {"ipc": 0.909234, "energy": 6.08719},
    "serialized_pointer_chase":  {"ipc": 0.826551, "energy": 4.32275},
    "compute_queue_pressure":    {"ipc": 2.391738, "energy": 2.68588},
    "stream_cluster_reduce":     {"ipc": 0.513648, "energy": 3.45580},
    "gapbs_bfs":                 {"ipc": 1.409910, "energy": 4.18887},
    "gapbs_bc":                  {"ipc": 1.396511, "energy": 4.21920},
    "gapbs_pr":                  {"ipc": 1.406315, "energy": 4.20774},
    "gapbs_cc":                  {"ipc": 1.410674, "energy": 3.93623},
    "gapbs_sssp":                {"ipc": 1.391411, "energy": 4.00860},
    "gapbs_tc":                  {"ipc": 1.345860, "energy": 5.46094},
}

# V2 reference
v2 = {
    "balanced_pipeline_stress":  {"ipc": 2.907918, "energy": 3.31345},
    "phase_scan_mix":            {"ipc": 0.471603, "energy": 5.01882},
    "branch_entropy":            {"ipc": 0.911579, "energy": 5.41906},
    "serialized_pointer_chase":  {"ipc": 0.780264, "energy": 3.84717},
    "compute_queue_pressure":    {"ipc": 2.391738, "energy": 2.68625},
    "stream_cluster_reduce":     {"ipc": 0.513648, "energy": 3.45727},
    "gapbs_bfs":                 {"ipc": 1.371020, "energy": 3.72556},
    "gapbs_bc":                  {"ipc": 1.357523, "energy": 3.80988},
    "gapbs_pr":                  {"ipc": 1.371114, "energy": 3.82040},
    "gapbs_cc":                  {"ipc": 1.376824, "energy": 3.67538},
    "gapbs_sssp":                {"ipc": 1.363212, "energy": 3.66810},
    "gapbs_tc":                  {"ipc": 1.390750, "energy": 4.36246},
}

# V3ml_t2
t2 = {
    "balanced_pipeline_stress":  {"ipc": 2.891274, "energy": 3.33792},
    "phase_scan_mix":            {"ipc": 0.456138, "energy": 4.74143},
    "branch_entropy":            {"ipc": 0.987587, "energy": 4.47306},
    "serialized_pointer_chase":  {"ipc": 0.780264, "energy": 3.84717},
    "compute_queue_pressure":    {"ipc": 2.391738, "energy": 2.68625},
    "stream_cluster_reduce":     {"ipc": 0.513648, "energy": 3.45727},
    "gapbs_bfs":                 {"ipc": 1.290223, "energy": 3.81332},
    "gapbs_bc":                  {"ipc": 1.312522, "energy": 3.83482},
    "gapbs_pr":                  {"ipc": 1.296654, "energy": 3.82772},
    "gapbs_cc":                  {"ipc": 1.313090, "energy": 3.69178},
    "gapbs_sssp":                {"ipc": 1.368630, "energy": 3.82587},
    "gapbs_tc":                  {"ipc": 1.275521, "energy": 4.64384},
}

def wpe(bl_ipc, bl_energy, new_ipc, new_energy):
    """WPE = (IPC_new/IPC_bl)^0.8 * (Energy_bl/Energy_new)^0.2"""
    ipc_ratio = new_ipc / bl_ipc
    energy_ratio = bl_energy / new_energy
    return (ipc_ratio ** 0.8) * (energy_ratio ** 0.2)

def delta_pct(val):
    return (val - 1.0) * 100.0

workloads = list(bl.keys())

print("=" * 140)
print(f"{'Workload':<30} {'BL IPC':>8} {'V2 IPC':>8} {'T2 IPC':>8} | {'BL E(J)':>8} {'V2 E(J)':>8} {'T2 E(J)':>8} | {'V2 WPE':>8} {'T2 WPE':>8} | {'V2 dWPE%':>8} {'T2 dWPE%':>8} | Winner")
print("-" * 140)

v2_wpes = []
t2_wpes = []
v2_wins = 0
t2_wins = 0

for wl in workloads:
    bl_ipc = bl[wl]["ipc"]
    bl_e = bl[wl]["energy"]
    v2_ipc = v2[wl]["ipc"]
    v2_e = v2[wl]["energy"]
    t2_ipc = t2[wl]["ipc"]
    t2_e = t2[wl]["energy"]

    v2_wpe = wpe(bl_ipc, bl_e, v2_ipc, v2_e)
    t2_wpe = wpe(bl_ipc, bl_e, t2_ipc, t2_e)

    v2_wpes.append(v2_wpe)
    t2_wpes.append(t2_wpe)

    v2_d = delta_pct(v2_wpe)
    t2_d = delta_pct(t2_wpe)

    if t2_wpe > v2_wpe:
        winner = "V3t2"
        t2_wins += 1
    elif v2_wpe > t2_wpe:
        winner = "V2"
        v2_wins += 1
    else:
        winner = "TIE"

    print(f"{wl:<30} {bl_ipc:>8.4f} {v2_ipc:>8.4f} {t2_ipc:>8.4f} | {bl_e:>8.4f} {v2_e:>8.4f} {t2_e:>8.4f} | {v2_wpe:>8.4f} {t2_wpe:>8.4f} | {v2_d:>+8.2f}% {t2_d:>+8.2f}% | {winner}")

print("-" * 140)

avg_v2 = sum(v2_wpes) / len(v2_wpes)
avg_t2 = sum(t2_wpes) / len(t2_wpes)

print(f"{'AVERAGE':<30} {'':>8} {'':>8} {'':>8} | {'':>8} {'':>8} {'':>8} | {avg_v2:>8.4f} {avg_t2:>8.4f} | {delta_pct(avg_v2):>+8.2f}% {delta_pct(avg_t2):>+8.2f}% |")
print()
print(f"V2 wins: {v2_wins}, V3t2 wins: {t2_wins}")
print(f"Average V2 WPE: {delta_pct(avg_v2):+.2f}%")
print(f"Average V3t2 WPE: {delta_pct(avg_t2):+.2f}%")

# Micro vs GAPBS breakdown
micro_wl = [w for w in workloads if not w.startswith("gapbs")]
gapbs_wl = [w for w in workloads if w.startswith("gapbs")]

micro_v2 = [v2_wpes[i] for i, w in enumerate(workloads) if not w.startswith("gapbs")]
micro_t2 = [t2_wpes[i] for i, w in enumerate(workloads) if not w.startswith("gapbs")]
gapbs_v2 = [v2_wpes[i] for i, w in enumerate(workloads) if w.startswith("gapbs")]
gapbs_t2 = [t2_wpes[i] for i, w in enumerate(workloads) if w.startswith("gapbs")]

print()
print(f"Micro avg V2 WPE: {delta_pct(sum(micro_v2)/len(micro_v2)):+.2f}%")
print(f"Micro avg T2 WPE: {delta_pct(sum(micro_t2)/len(micro_t2)):+.2f}%")
print(f"GAPBS avg V2 WPE: {delta_pct(sum(gapbs_v2)/len(gapbs_v2)):+.2f}%")
print(f"GAPBS avg T2 WPE: {delta_pct(sum(gapbs_t2)/len(gapbs_t2)):+.2f}%")

# Check for any WPE < -3%
print()
print("=== Anomaly check: any WPE < -3%? ===")
for i, wl in enumerate(workloads):
    t2_d = delta_pct(t2_wpes[i])
    if t2_d < -3.0:
        print(f"  WARNING: {wl} T2 WPE = {t2_d:+.2f}% (below -3% threshold)")

# IPC ratio analysis
print()
print("=== IPC ratio analysis ===")
for wl in workloads:
    v2_ipc_ratio = v2[wl]["ipc"] / bl[wl]["ipc"]
    t2_ipc_ratio = t2[wl]["ipc"] / bl[wl]["ipc"]
    v2_e_ratio = bl[wl]["energy"] / v2[wl]["energy"]
    t2_e_ratio = bl[wl]["energy"] / t2[wl]["energy"]
    print(f"{wl:<30} V2: IPC_r={v2_ipc_ratio:.4f} E_r={v2_e_ratio:.4f} | T2: IPC_r={t2_ipc_ratio:.4f} E_r={t2_e_ratio:.4f}")
