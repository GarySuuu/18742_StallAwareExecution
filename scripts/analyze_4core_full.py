#!/usr/bin/env python3
import re, os


def get(p, pat):
    if not os.path.exists(p):
        return None
    with open(p) as f:
        for l in f:
            m = re.search(pat, l)
            if m:
                return float(m.group(1))
    return None


def mcpat_energy(p):
    if not os.path.exists(p):
        return None
    s = False
    with open(p) as f:
        for l in f:
            if "System:" in l and "Core" not in l:
                s = True
                continue
            if s:
                m = re.search(r"Total Runtime Energy\s*=\s*([\d.]+)\s*J", l)
                if m:
                    return float(m.group(1))
    return None


g = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = os.path.join(g, "runs", "v4_multicore")

micro = [
    "balanced_pipeline_stress",
    "phase_scan_mix",
    "branch_entropy",
    "serialized_pointer_chase",
    "compute_queue_pressure",
    "stream_cluster_reduce",
]
gapbs = [
    "gapbs_bfs",
    "gapbs_bc",
    "gapbs_pr",
    "gapbs_cc",
    "gapbs_sssp",
    "gapbs_tc",
]

all_wl = micro + gapbs

print("=" * 110)
print("  4-Core Same-Workload: Baseline vs V4")
print("  Energy = per-core McPAT x4 (same workload on all cores)")
print("=" * 110)

f_pct = lambda v: f"{v:>+6.1f}%" if v is not None else "    N/A"

print(
    f"\n{'Workload':<28} | {'BL avgIPC':>9} {'V4 avgIPC':>9} {'dIPC':>7} | {'BL Eng':>8} {'V4 Eng':>8} {'dEng':>7} | {'EDP imp':>8} |"
)
print("-" * 105)

edp_all = []

for wl in all_wl:
    bl_d = os.path.join(base, f"{wl}_baseline/latest")
    v4_d = os.path.join(base, f"{wl}_v4/latest")

    bl_stats = os.path.join(bl_d, "stats.txt")
    v4_stats = os.path.join(v4_d, "stats.txt")

    if not os.path.exists(bl_stats) or not os.path.exists(v4_stats):
        print(f"{wl:<28} | {'--- missing ---':^50} |")
        continue

    # Check if simulation actually completed (has simInsts)
    bl_insts = get(bl_stats, r"simInsts\s+(\d+)")
    v4_insts = get(v4_stats, r"simInsts\s+(\d+)")
    if bl_insts is None or bl_insts < 1000:
        print(f"{wl:<28} | {'--- sim failed ---':^50} |")
        continue

    bl_ticks = get(bl_stats, r"simTicks\s+(\d+)")
    v4_ticks = get(v4_stats, r"simTicks\s+(\d+)")

    # Average IPC across 4 cores
    bl_ipcs = [
        get(bl_stats, rf"system\.cpu{i}\.ipc\s+([\d.]+)") or 0
        for i in range(4)
    ]
    v4_ipcs = [
        get(v4_stats, rf"system\.cpu{i}\.ipc\s+([\d.]+)") or 0
        for i in range(4)
    ]
    bl_avg = sum(bl_ipcs) / 4
    v4_avg = sum(v4_ipcs) / 4

    bl_en_core = mcpat_energy(os.path.join(bl_d, "mcpat.out"))
    v4_en_core = mcpat_energy(os.path.join(v4_d, "mcpat.out"))

    if bl_en_core and v4_en_core and bl_ticks and v4_ticks:
        bl_en = bl_en_core * 4
        v4_en = v4_en_core * 4
        bl_edp = bl_en * bl_ticks / 1e12
        v4_edp = v4_en * v4_ticks / 1e12
        dedp = (1 - v4_edp / bl_edp) * 100
        dipc = (v4_avg / bl_avg - 1) * 100 if bl_avg > 0 else None
        deng = (v4_en / bl_en - 1) * 100
        edp_all.append(dedp)
        print(
            f"{wl:<28} | {bl_avg:>9.3f} {v4_avg:>9.3f} {f_pct(dipc):>7} | {bl_en:>7.2f}J {v4_en:>7.2f}J {f_pct(deng):>7} | {f_pct(dedp):>8} |"
        )
    else:
        print(
            f"{wl:<28} | {bl_avg:>9.3f} {v4_avg:>9.3f} {'':>7} | {'N/A':>8} {'N/A':>8} {'':>7} | {'N/A':>8} |"
        )

if edp_all:
    print(
        f"\n  Average EDP improvement (successful workloads): {sum(edp_all)/len(edp_all):+.1f}% ({len(edp_all)} workloads)"
    )
