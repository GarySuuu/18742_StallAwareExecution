#!/usr/bin/env python3
"""Final comparison: Baseline vs V3 vs V4(WPE) vs V4(EDP)."""
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

# Paths
# Baseline
bl_m = lambda wl: os.path.join(g, f"runs/v3_multilevel/baseline/{wl}/latest")
bl_g = lambda b: os.path.join(
    g, f"runs/v3_multilevel/baseline/gapbs_{b}/latest"
)

# V3 = v3t9a (Round 7)
v3_m = lambda wl: os.path.join(g, f"runs/v3_multilevel/v3t9a/{wl}/latest")
v3_m_alt = lambda wl: os.path.join(
    g, f"runs/v3_multilevel/v3t8/{wl}/latest"
)  # micro same as v3t8
v3_g = lambda wl: os.path.join(
    g, f"runs/v3_multilevel/v3t9a/gapbs_{wl}/latest"
)

# V4 WPE-optimal = v3t10
v4w_m = lambda wl: os.path.join(g, f"runs/v3_multilevel/v3t10/{wl}/latest")
v4w_g = lambda b: os.path.join(g, f"runs/v3_multilevel/v3t10/gapbs_{b}/latest")

# V4 EDP-optimal = edp_opt
v4e_m = lambda wl: os.path.join(g, f"runs/v3_final/edp_opt/{wl}/latest")
v4e_g = lambda b: os.path.join(g, f"runs/v3_final/edp_opt/gapbs_{b}/latest")


def resolve(fn, alt_fn, wl):
    d = get_all(fn(wl))
    if d[0] is None and alt_fn:
        d = get_all(alt_fn(wl))
    return d


print("=" * 160)
print("  FINAL COMPARISON: Baseline vs V3 vs V4-WPE vs V4-EDP")
print(
    "  V3 = v3t9a (Round 7)  |  V4-WPE = v3t10 (Resource congestion)  |  V4-EDP = edp_opt (aggressive throttle)"
)
print("=" * 160)

# Collect all metrics
all_metrics = {
    "v3": {
        "wpe": [],
        "edp": [],
        "mwpe": [],
        "medp": [],
        "gwpe": [],
        "gedp": [],
    },
    "v4w": {
        "wpe": [],
        "edp": [],
        "mwpe": [],
        "medp": [],
        "gwpe": [],
        "gedp": [],
    },
    "v4e": {
        "wpe": [],
        "edp": [],
        "mwpe": [],
        "medp": [],
        "gwpe": [],
        "gedp": [],
    },
}

print(
    f"\n{'':28} | {'--- Baseline ---':^18} | {'--- V3 vs BL ---':^24} | {'--- V4-WPE vs BL ---':^24} | {'--- V4-EDP vs BL ---':^24} |"
)
print(
    f"{'Workload':<28} | {'IPC':>6} {'Eng(J)':>7} | {'dIPC':>6} {'dEng':>6} {'WPE':>6} {'EDP':>6} | {'dIPC':>6} {'dEng':>6} {'WPE':>6} {'EDP':>6} | {'dIPC':>6} {'dEng':>6} {'WPE':>6} {'EDP':>6} |"
)
print("-" * 155)

for section, workloads, bl_fn, v3_fn, v3_alt, v4w_fn, v4e_fn, prefix in [
    ("micro", micro, bl_m, v3_m, v3_m_alt, v4w_m, v4e_m, ""),
    ("gapbs", gapbs, bl_g, v3_g, None, v4w_g, v4e_g, "GAPBS-"),
]:
    for wl in workloads:
        bl = get_all(bl_fn(wl))
        v3 = resolve(v3_fn, v3_alt, wl)
        v4w = get_all(v4w_fn(wl))
        v4e = get_all(v4e_fn(wl))

        bl_edp = calc_edp(bl[3], bl[1])
        name = f"{prefix}{wl}"

        row = f"{name:<28} | {bl[0] or 0:>6.3f} {bl[3] or 0:>7.3f} |"

        for tag, d in [("v3", v3), ("v4w", v4w), ("v4e", v4e)]:
            dipc = dp(d[0], bl[0])
            deng = dp(d[3], bl[3])
            w = calc_wpe(d[0], d[3], bl[0], bl[3])
            wi = (w - 1) * 100 if w else None
            e = calc_edp(d[3], d[1])
            ei = (1 - e / bl_edp) * 100 if e and bl_edp else None

            if wi is not None:
                all_metrics[tag]["wpe"].append(wi)
                if section == "micro":
                    all_metrics[tag]["mwpe"].append(wi)
                else:
                    all_metrics[tag]["gwpe"].append(wi)
            if ei is not None:
                all_metrics[tag]["edp"].append(ei)
                if section == "micro":
                    all_metrics[tag]["medp"].append(ei)
                else:
                    all_metrics[tag]["gedp"].append(ei)

            row += f" {f(dipc):>6} {f(deng):>6} {f(wi):>6} {f(ei):>6} |"

        print(row)

    if section == "micro":
        print()

# Summary
print(f"\n{'='*90}")
print(f"  SUMMARY")
print(f"{'='*90}")
print(f"\n{'Metric':<20} {'V3':>10} {'V4-WPE':>10} {'V4-EDP':>10}")
print("-" * 55)
for label, key in [
    ("Overall WPE", "wpe"),
    ("Micro WPE", "mwpe"),
    ("GAPBS WPE", "gwpe"),
    ("Overall EDP", "edp"),
    ("Micro EDP", "medp"),
    ("GAPBS EDP", "gedp"),
]:
    vals = []
    for tag in ["v3", "v4w", "v4e"]:
        d = all_metrics[tag][key]
        vals.append(f"{sum(d)/len(d):>+9.2f}%" if d else "      N/A")
    print(f"{label:<20} {vals[0]} {vals[1]} {vals[2]}")
