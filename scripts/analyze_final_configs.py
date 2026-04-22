#!/usr/bin/env python3
"""Analyze WPE-optimal and EDP-optimal final configs."""
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


def wpe(ipc, en, bi, be):
    if None in (ipc, en, bi, be) or bi == 0 or be == 0:
        return None
    return ((ipc / bi) ** 0.8) * ((be / en) ** 0.2)


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

bl_m = lambda wl: os.path.join(g, f"runs/v3_multilevel/baseline/{wl}/latest")
bl_g = lambda b: os.path.join(
    g, f"runs/v3_multilevel/baseline/gapbs_{b}/latest"
)
wpe_m = lambda wl: os.path.join(g, f"runs/v3_final/wpe_opt/{wl}/latest")
wpe_g = lambda b: os.path.join(g, f"runs/v3_final/wpe_opt/gapbs_{b}/latest")
edp_m = lambda wl: os.path.join(g, f"runs/v3_final/edp_opt/{wl}/latest")
edp_g = lambda b: os.path.join(g, f"runs/v3_final/edp_opt/gapbs_{b}/latest")
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

print("=" * 150)
print(
    "  Final Configs: V2 vs WPE-optimal vs EDP-optimal (both with adaptive window)"
)
print("=" * 150)

hdr = f"{'Workload':<28} | {'dIPC':>6} {'dEng':>6} {'WPE':>6} {'EDP':>6} | {'dIPC':>6} {'dEng':>6} {'WPE':>6} {'EDP':>6} | {'dIPC':>6} {'dEng':>6} {'WPE':>6} {'EDP':>6} |"
print(
    f"\n{'':28} | {'--- V2 ---':^26} | {'--- WPE-opt ---':^26} | {'--- EDP-opt ---':^26} |"
)
print(hdr.replace("dIPC", "dIPC").replace("dEng", "dEng"))
print("-" * 120)

configs_data = {
    "v2": {
        "wpe": [],
        "edp": [],
        "mwpe": [],
        "medp": [],
        "gwpe": [],
        "gedp": [],
    },
    "wpe_opt": {
        "wpe": [],
        "edp": [],
        "mwpe": [],
        "medp": [],
        "gwpe": [],
        "gedp": [],
    },
    "edp_opt": {
        "wpe": [],
        "edp": [],
        "mwpe": [],
        "medp": [],
        "gwpe": [],
        "gedp": [],
    },
}

for section, workloads, bl_fn, wpe_fn, edp_fn, v2_fn, v2bl_fn, prefix in [
    ("micro", micro, bl_m, wpe_m, edp_m, v2_m, v2bl_m, ""),
    ("gapbs", gapbs, bl_g, wpe_g, edp_g, v2_g, v2bl_g, "GAPBS-"),
]:
    for wl in workloads:
        bl = get_all(bl_fn(wl))
        wp = get_all(wpe_fn(wl))
        ep = get_all(edp_fn(wl))
        v2 = get_all(v2_fn(wl))
        v2b = get_all(v2bl_fn(wl))

        # V2 metrics
        v2_wpe_v = (
            (wpe(v2[0], v2[3], v2b[0], v2b[3]) - 1) * 100
            if wpe(v2[0], v2[3], v2b[0], v2b[3])
            else None
        )
        v2_edp_v = (
            (1 - edp(v2[3], v2[1]) / edp(v2b[3], v2b[1])) * 100
            if edp(v2[3], v2[1]) and edp(v2b[3], v2b[1])
            else None
        )
        v2_dipc = dp(v2[0], v2b[0])
        v2_deng = dp(v2[3], v2b[3])

        # WPE-opt metrics
        wp_wpe_v = (
            (wpe(wp[0], wp[3], bl[0], bl[3]) - 1) * 100
            if wpe(wp[0], wp[3], bl[0], bl[3])
            else None
        )
        wp_edp_v = (
            (1 - edp(wp[3], wp[1]) / edp(bl[3], bl[1])) * 100
            if edp(wp[3], wp[1]) and edp(bl[3], bl[1])
            else None
        )
        wp_dipc = dp(wp[0], bl[0])
        wp_deng = dp(wp[3], bl[3])

        # EDP-opt metrics
        ep_wpe_v = (
            (wpe(ep[0], ep[3], bl[0], bl[3]) - 1) * 100
            if wpe(ep[0], ep[3], bl[0], bl[3])
            else None
        )
        ep_edp_v = (
            (1 - edp(ep[3], ep[1]) / edp(bl[3], bl[1])) * 100
            if edp(ep[3], ep[1]) and edp(bl[3], bl[1])
            else None
        )
        ep_dipc = dp(ep[0], bl[0])
        ep_deng = dp(ep[3], bl[3])

        name = f"{prefix}{wl}"
        print(
            f"{name:<28} | {f(v2_dipc):>6} {f(v2_deng):>6} {f(v2_wpe_v):>6} {f(v2_edp_v):>6} "
            f"| {f(wp_dipc):>6} {f(wp_deng):>6} {f(wp_wpe_v):>6} {f(wp_edp_v):>6} "
            f"| {f(ep_dipc):>6} {f(ep_deng):>6} {f(ep_wpe_v):>6} {f(ep_edp_v):>6} |"
        )

        for key, vals in [
            ("v2", [v2_wpe_v, v2_edp_v]),
            ("wpe_opt", [wp_wpe_v, wp_edp_v]),
            ("edp_opt", [ep_wpe_v, ep_edp_v]),
        ]:
            if vals[0] is not None:
                configs_data[key]["wpe"].append(vals[0])
                if section == "micro":
                    configs_data[key]["mwpe"].append(vals[0])
                else:
                    configs_data[key]["gwpe"].append(vals[0])
            if vals[1] is not None:
                configs_data[key]["edp"].append(vals[1])
                if section == "micro":
                    configs_data[key]["medp"].append(vals[1])
                else:
                    configs_data[key]["gedp"].append(vals[1])

    if section == "micro":
        print()

print(f"\n{'='*80}")
print(f"  SUMMARY")
print(f"{'='*80}")
print(f"\n{'Metric':<20} {'V2':>10} {'WPE-opt':>10} {'EDP-opt':>10}")
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
    for cfg in ["v2", "wpe_opt", "edp_opt"]:
        d = configs_data[cfg][key]
        vals.append(f"{sum(d)/len(d):>+9.2f}%" if d else "      N/A")
    print(f"{label:<20} {vals[0]} {vals[1]} {vals[2]}")
