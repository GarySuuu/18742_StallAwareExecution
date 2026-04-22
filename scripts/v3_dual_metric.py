#!/usr/bin/env python3
"""Dual metric report: WPE + EDP for v3t10 vs V2 vs baseline."""
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
    ipc = get_ipc(os.path.join(d, "stats.txt"))
    ticks = get_ticks(os.path.join(d, "stats.txt"))
    pw, en = get_mcpat(os.path.join(d, "mcpat.out"))
    return ipc, ticks, pw, en


def calc_wpe(ipc, en, bi, be):
    if None in (ipc, en, bi, be) or bi == 0 or be == 0:
        return None
    return ((ipc / bi) ** 0.8) * ((be / en) ** 0.2)


def calc_edp(en, ticks):
    if en is None or ticks is None:
        return None
    return en * (ticks / 1e12)  # Joule-seconds


def edp_imp(edp, bl_edp):
    if edp is None or bl_edp is None or bl_edp == 0:
        return None
    return (1 - edp / bl_edp) * 100


def wpe_imp(w):
    if w is None:
        return None
    return (w - 1) * 100


def f(v):
    return f"{v:>+6.1f}%" if v is not None else "    N/A"


def dp(n, b):
    return f"{(n/b-1)*100:>+6.1f}%" if n and b and b != 0 else "    N/A"


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

# Paths
t10 = lambda wl: os.path.join(g, f"runs/v3_multilevel/v3t10/{wl}/latest")
t10g = lambda b: os.path.join(g, f"runs/v3_multilevel/v3t10/gapbs_{b}/latest")
bl_m = lambda wl: os.path.join(g, f"runs/v3_multilevel/baseline/{wl}/latest")
bl_g = lambda b: os.path.join(
    g, f"runs/v3_multilevel/baseline/gapbs_{b}/latest"
)
v2_m = lambda wl: os.path.join(
    g, f"runs/adaptive/v3_compiled/{wl}_v2_ref/latest"
)
v2_g = lambda b: os.path.join(
    g, f"runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest"
)
v2bl_m = lambda wl: os.path.join(g, f"runs/baseline_v3/{wl}/latest")
v2bl_g = lambda b: os.path.join(
    g, f"runs/baseline/formal_gapbs_{b}_g20_baseline/latest"
)

print("=" * 140)
print("  V3t10 Final: WPE + EDP Dual Metric Report")
print(
    "  WPE = (IPC_ratio)^0.8 × (Energy_bl/Energy_new)^0.2  |  EDP = Energy × Time (lower=better)"
)
print("=" * 140)

print(
    f"\n{'Workload':<28} | {'dIPC':>6} {'dEng':>6} | {'V2 WPE':>7} {'V3 WPE':>7} | {'V2 EDP':>7} {'V3 EDP':>7} |"
)
print("-" * 95)

v2_wpe_all = []
v3_wpe_all = []
v2_edp_all = []
v3_edp_all = []

for section, workloads, bl_fn, v3_fn, v2_fn, v2bl_fn, prefix in [
    ("micro", micro, bl_m, t10, v2_m, v2bl_m, ""),
    ("gapbs", gapbs, bl_g, t10g, v2_g, v2bl_g, "GAPBS-"),
]:
    for wl in workloads:
        bl = get_all(bl_fn(wl))
        v3 = get_all(v3_fn(wl))
        v2 = get_all(v2_fn(wl))
        v2bl = get_all(v2bl_fn(wl))

        v2w = wpe_imp(calc_wpe(v2[0], v2[3], v2bl[0], v2bl[3]))
        v3w = wpe_imp(calc_wpe(v3[0], v3[3], bl[0], bl[3]))
        v2e = edp_imp(calc_edp(v2[3], v2[1]), calc_edp(v2bl[3], v2bl[1]))
        v3e = edp_imp(calc_edp(v3[3], v3[1]), calc_edp(bl[3], bl[1]))

        if v2w is not None:
            v2_wpe_all.append(v2w)
        if v3w is not None:
            v3_wpe_all.append(v3w)
        if v2e is not None:
            v2_edp_all.append(v2e)
        if v3e is not None:
            v3_edp_all.append(v3e)

        name = f"{prefix}{wl}"
        print(
            f"{name:<28} | {dp(v3[0],bl[0]):>6} {dp(v3[3],bl[3]):>6} | {f(v2w):>7} {f(v3w):>7} | {f(v2e):>7} {f(v3e):>7} |"
        )

    if section == "micro":
        print(
            f"{'  Micro avg':<28} | {'':>6} {'':>6} | {f(sum(v2_wpe_all)/len(v2_wpe_all)):>7} {f(sum(v3_wpe_all)/len(v3_wpe_all)):>7} | {f(sum(v2_edp_all)/len(v2_edp_all)):>7} {f(sum(v3_edp_all)/len(v3_edp_all)):>7} |"
        )
        micro_v2w = list(v2_wpe_all)
        micro_v3w = list(v3_wpe_all)
        micro_v2e = list(v2_edp_all)
        micro_v3e = list(v3_edp_all)
        print()

gapbs_v2w = v2_wpe_all[len(micro_v2w) :]
gapbs_v3w = v3_wpe_all[len(micro_v3w) :]
gapbs_v2e = v2_edp_all[len(micro_v2e) :]
gapbs_v3e = v3_edp_all[len(micro_v3e) :]

print(
    f"{'  GAPBS avg':<28} | {'':>6} {'':>6} | {f(sum(gapbs_v2w)/len(gapbs_v2w)):>7} {f(sum(gapbs_v3w)/len(gapbs_v3w)):>7} | {f(sum(gapbs_v2e)/len(gapbs_v2e)):>7} {f(sum(gapbs_v3e)/len(gapbs_v3e)):>7} |"
)

print(f"\n{'='*60}")
print(f"{'Metric':<20} {'V2':>10} {'V3t10':>10}")
print(f"{'-'*40}")
print(
    f"{'Overall WPE':<20} {sum(v2_wpe_all)/len(v2_wpe_all):>+9.2f}% {sum(v3_wpe_all)/len(v3_wpe_all):>+9.2f}%"
)
print(
    f"{'Micro WPE':<20} {sum(micro_v2w)/len(micro_v2w):>+9.2f}% {sum(micro_v3w)/len(micro_v3w):>+9.2f}%"
)
print(
    f"{'GAPBS WPE':<20} {sum(gapbs_v2w)/len(gapbs_v2w):>+9.2f}% {sum(gapbs_v3w)/len(gapbs_v3w):>+9.2f}%"
)
print(
    f"{'Overall EDP':<20} {sum(v2_edp_all)/len(v2_edp_all):>+9.2f}% {sum(v3_edp_all)/len(v3_edp_all):>+9.2f}%"
)
print(
    f"{'Micro EDP':<20} {sum(micro_v2e)/len(micro_v2e):>+9.2f}% {sum(micro_v3e)/len(micro_v3e):>+9.2f}%"
)
print(
    f"{'GAPBS EDP':<20} {sum(gapbs_v2e)/len(gapbs_v2e):>+9.2f}% {sum(gapbs_v3e)/len(gapbs_v3e):>+9.2f}%"
)
