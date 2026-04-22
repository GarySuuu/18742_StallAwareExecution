#!/usr/bin/env python3
"""Analyze V4 unified config — EDP only."""
import os, re


def get_ipc(p):
    if not os.path.exists(p):
        return None
    with open(p) as f:
        for l in f:
            m = re.search(r"system\.cpu\.ipc\s+([\d.]+)", l)
            if m:
                return float(m.group(1))
    return None


def get_ticks(p):
    if not os.path.exists(p):
        return None
    with open(p) as f:
        for l in f:
            m = re.search(r"simTicks\s+(\d+)", l)
            if m:
                return int(m.group(1))
    return None


def get_mcpat(p):
    if not os.path.exists(p):
        return None, None
    pw = en = None
    s = False
    with open(p) as f:
        for l in f:
            if "System:" in l:
                s = True
                continue
            if s:
                m = re.search(r"Runtime Dynamic Power\s*=\s*([\d.]+)\s*W", l)
                if m and pw is None:
                    pw = float(m.group(1))
                m2 = re.search(r"Total Runtime Energy\s*=\s*([\d.]+)\s*J", l)
                if m2 and en is None:
                    en = float(m2.group(1))
                if pw and en:
                    break
    return pw, en


def get_all(d):
    return (
        get_ipc(os.path.join(d, "stats.txt")),
        get_ticks(os.path.join(d, "stats.txt")),
        *get_mcpat(os.path.join(d, "mcpat.out")),
    )


def edp(en, ticks):
    if en is None or ticks is None:
        return None
    return en * (ticks / 1e12)


def f(v):
    return f"{v:>+6.1f}%" if v is not None else "    N/A"


def dp(n, b):
    return (n / b - 1) * 100 if n and b and b != 0 else None


g = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
micro = [
    "balanced_pipeline_stress",
    "phase_scan_mix",
    "branch_entropy",
    "serialized_pointer_chase",
    "compute_queue_pressure",
    "stream_cluster_reduce",
]
gapbs = ["bfs", "bc", "pr", "cc", "sssp", "tc"]

bl_fn = lambda wl, is_g: os.path.join(
    g, f'runs/v3_multilevel/baseline/{"gapbs_"+wl if is_g else wl}/latest'
)
uni_fn = lambda wl, is_g: os.path.join(
    g, f'runs/v4_unified/{"gapbs_"+wl if is_g else wl}/latest'
)
prev_fn = lambda wl, is_g: os.path.join(
    g, f'runs/v3_final/edp_opt/{"gapbs_"+wl if is_g else wl}/latest'
)

print("=" * 120)
print("  V4 Unified Config: EDP Results")
print(
    "  Config: fw=5, cap=48, iq=24, lsq=24, deep fw=3@sq>=0.25, adaptive window — SAME for all workloads"
)
print("=" * 120)

print(
    f"\n{'Workload':<28} | {'BL IPC':>7} {'Uni IPC':>8} {'dIPC':>7} | {'BL Eng':>7} {'Uni Eng':>8} {'dEng':>7} | {'Uni EDP':>8} {'Prev EDP':>9} |"
)
print("-" * 110)

uni_edp_all = []
prev_edp_all = []
uni_medp = []
prev_medp = []
uni_gedp = []
prev_gedp = []

for section, workloads, is_g, prefix in [
    ("micro", micro, False, ""),
    ("gapbs", gapbs, True, "GAPBS-"),
]:
    for wl in workloads:
        bl = get_all(bl_fn(wl, is_g))
        uni = get_all(uni_fn(wl, is_g))
        prev = get_all(prev_fn(wl, is_g))

        bl_edp_v = edp(bl[3], bl[1])
        uni_edp_v = edp(uni[3], uni[1])
        prev_edp_v = edp(prev[3], prev[1])

        uni_ei = (
            (1 - uni_edp_v / bl_edp_v) * 100
            if uni_edp_v and bl_edp_v
            else None
        )
        prev_ei = (
            (1 - prev_edp_v / bl_edp_v) * 100
            if prev_edp_v and bl_edp_v
            else None
        )

        if uni_ei is not None:
            uni_edp_all.append(uni_ei)
            if not is_g:
                uni_medp.append(uni_ei)
            else:
                uni_gedp.append(uni_ei)
        if prev_ei is not None:
            prev_edp_all.append(prev_ei)
            if not is_g:
                prev_medp.append(prev_ei)
            else:
                prev_gedp.append(prev_ei)

        dipc = dp(uni[0], bl[0])
        deng = dp(uni[3], bl[3])
        name = f"{prefix}{wl}"

        print(
            f"{name:<28} | {bl[0] or 0:>7.3f} {uni[0] or 0:>8.3f} {f(dipc):>7} | {bl[3] or 0:>7.3f} {uni[3] or 0:>8.3f} {f(deng):>7} | {f(uni_ei):>8} {f(prev_ei):>9} |"
        )

    if section == "micro":
        print()

print(f"\n{'='*70}")
print(f"  SUMMARY (EDP improvement %)")
print(f"{'='*70}")
print(f"\n{'Metric':<20} {'V4-Unified':>12} {'V4-EDP-prev':>12} {'V2':>12}")
print("-" * 60)
print(
    f"{'Overall EDP':<20} {sum(uni_edp_all)/len(uni_edp_all):>+11.2f}% {sum(prev_edp_all)/len(prev_edp_all):>+11.2f}% {'~+7.5%':>12}"
)
print(
    f"{'Micro EDP':<20} {sum(uni_medp)/len(uni_medp):>+11.2f}% {sum(prev_medp)/len(prev_medp):>+11.2f}%"
)
print(
    f"{'GAPBS EDP':<20} {sum(uni_gedp)/len(uni_gedp):>+11.2f}% {sum(prev_gedp)/len(prev_gedp):>+11.2f}%"
)
