#!/usr/bin/env python3
"""Analyze v3t10 (Resource congestion sub-level) results."""
import os, re, csv


def get_ipc(p):
    if not os.path.exists(p):
        return None
    with open(p) as f:
        for l in f:
            m = re.search(r"system\.cpu\.ipc\s+([\d.]+)", l)
            if m:
                return float(m.group(1))
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
    return get_ipc(os.path.join(d, "stats.txt")), *get_mcpat(
        os.path.join(d, "mcpat.out")
    )


def wpe(ipc, en, bi, be):
    if None in (ipc, en, bi, be) or bi == 0 or be == 0:
        return None
    return ((ipc / bi) ** 0.8) * ((be / en) ** 0.2)


def modes(d):
    log = os.path.join(d, "adaptive_window_log.csv")
    if not os.path.exists(log):
        return "", ""
    ms = {}
    rp = {}
    t = 0
    with open(log) as f:
        for r in csv.DictReader(f):
            t += 1
            m = r.get("applied_mode", "")
            ms[m] = ms.get(m, 0) + 1
            p = r.get("resource_profile_level", "na")
            rp[p] = rp.get(p, 0) + 1
    mode_str = " ".join(
        f"{k}:{v*100//max(t,1)}%" for k, v in sorted(ms.items())
    )
    rp_str = " ".join(f"{k}:{v}" for k, v in sorted(rp.items()) if k != "na")
    return mode_str, rp_str


def dp(n, b):
    return f"{(n/b-1)*100:>+6.1f}%" if n and b and b != 0 else "    N/A"


def fw(v):
    return f"{(v-1)*100:>+6.1f}%" if v else "    N/A"


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

print("=" * 130)
print("  v3t10: Resource Congestion Sub-Level Results")
print("=" * 130)

print(
    f"\n{'Workload':<28} {'BL IPC':>7} {'t10 IPC':>8} {'dIPC':>7} {'dEng':>7} {'WPE':>7} | modes / sub-level"
)
print("-" * 110)

v2_micro_bl = lambda wl: os.path.join(g, f"runs/baseline_v3/{wl}/latest")
v2_gapbs_bl = lambda b: os.path.join(
    g, f"runs/baseline/formal_gapbs_{b}_g20_baseline/latest"
)

all_wpe = []
micro_wpe = []
gapbs_wpe = []

for wl in micro:
    bl = get_all(os.path.join(g, f"runs/v3_multilevel/baseline/{wl}/latest"))
    t10 = get_all(os.path.join(g, f"runs/v3_multilevel/v3t10/{wl}/latest"))
    w = wpe(t10[0], t10[2], bl[0], bl[2])
    wi = (w - 1) * 100 if w else None
    if wi is not None:
        all_wpe.append(wi)
        micro_wpe.append(wi)
    m, rp = modes(os.path.join(g, f"runs/v3_multilevel/v3t10/{wl}/latest"))
    rp_show = f" sub:{rp}" if rp else ""
    print(
        f"{wl:<28} {bl[0] or 0:>7.3f} {t10[0] or 0:>8.3f} {dp(t10[0],bl[0]):>7} {dp(t10[2],bl[2]):>7} {fw(w):>7} | {m}{rp_show}"
    )

print()
for b in gapbs:
    bl = get_all(
        os.path.join(g, f"runs/v3_multilevel/baseline/gapbs_{b}/latest")
    )
    t10 = get_all(
        os.path.join(g, f"runs/v3_multilevel/v3t10/gapbs_{b}/latest")
    )
    w = wpe(t10[0], t10[2], bl[0], bl[2])
    wi = (w - 1) * 100 if w else None
    if wi is not None:
        all_wpe.append(wi)
        gapbs_wpe.append(wi)
    m, rp = modes(
        os.path.join(g, f"runs/v3_multilevel/v3t10/gapbs_{b}/latest")
    )
    rp_show = f" sub:{rp}" if rp else ""
    print(
        f"GAPBS-{b:<22} {bl[0] or 0:>7.3f} {t10[0] or 0:>8.3f} {dp(t10[0],bl[0]):>7} {dp(t10[2],bl[2]):>7} {fw(w):>7} | {m}{rp_show}"
    )

# Compare with v3t9a
print(f"\n{'='*80}")
print("  v3t9a vs v3t10 comparison")
print(f"{'='*80}")

v9a_micro_wpe = []
v9a_gapbs_wpe = []
print(f"\n{'Workload':<28} {'v3t9a WPE':>10} {'v3t10 WPE':>10} {'Delta':>8}")
print("-" * 60)

for wl in micro:
    bl9 = get_all(os.path.join(g, f"runs/v3_multilevel/baseline/{wl}/latest"))
    t9 = get_all(os.path.join(g, f"runs/v3_multilevel/v3t9a/{wl}/latest"))
    if not t9[0]:
        t9 = get_all(os.path.join(g, f"runs/v3_multilevel/v3t8/{wl}/latest"))
    t10 = get_all(os.path.join(g, f"runs/v3_multilevel/v3t10/{wl}/latest"))
    w9 = wpe(t9[0], t9[2], bl9[0], bl9[2])
    w10 = wpe(t10[0], t10[2], bl9[0], bl9[2])
    w9i = (w9 - 1) * 100 if w9 else None
    w10i = (w10 - 1) * 100 if w10 else None
    if w9i is not None:
        v9a_micro_wpe.append(w9i)
    delta = (
        f"{w10i-w9i:>+7.2f}pp"
        if w9i is not None and w10i is not None
        else "     N/A"
    )
    print(f"{wl:<28} {fw(w9):>10} {fw(w10):>10} {delta}")

for b in gapbs:
    bl9 = get_all(
        os.path.join(g, f"runs/v3_multilevel/baseline/gapbs_{b}/latest")
    )
    t9 = get_all(os.path.join(g, f"runs/v3_multilevel/v3t9a/gapbs_{b}/latest"))
    t10 = get_all(
        os.path.join(g, f"runs/v3_multilevel/v3t10/gapbs_{b}/latest")
    )
    w9 = wpe(t9[0], t9[2], bl9[0], bl9[2])
    w10 = wpe(t10[0], t10[2], bl9[0], bl9[2])
    w9i = (w9 - 1) * 100 if w9 else None
    w10i = (w10 - 1) * 100 if w10 else None
    if w9i is not None:
        v9a_gapbs_wpe.append(w9i)
    delta = (
        f"{w10i-w9i:>+7.2f}pp"
        if w9i is not None and w10i is not None
        else "     N/A"
    )
    print(f"GAPBS-{b:<22} {fw(w9):>10} {fw(w10):>10} {delta}")

print(f"\n{'Metric':<28} {'v3t9a':>10} {'v3t10':>10}")
print("-" * 50)
if micro_wpe:
    print(
        f"{'Micro avg WPE':<28} {sum(v9a_micro_wpe)/len(v9a_micro_wpe):>+9.2f}% {sum(micro_wpe)/len(micro_wpe):>+9.2f}%"
    )
if gapbs_wpe:
    print(
        f"{'GAPBS avg WPE':<28} {sum(v9a_gapbs_wpe)/len(v9a_gapbs_wpe):>+9.2f}% {sum(gapbs_wpe)/len(gapbs_wpe):>+9.2f}%"
    )
if all_wpe:
    print(
        f"{'Overall avg WPE':<28} {(sum(v9a_micro_wpe)+sum(v9a_gapbs_wpe))/(len(v9a_micro_wpe)+len(v9a_gapbs_wpe)):>+9.2f}% {sum(all_wpe)/len(all_wpe):>+9.2f}%"
    )
