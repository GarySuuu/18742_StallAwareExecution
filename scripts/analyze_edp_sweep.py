#!/usr/bin/env python3
"""Analyze 4 EDP config sweep results."""
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
all_wl = [(w, False) for w in micro] + [(b, True) for b in gapbs]

configs = ["A", "B", "C", "D"]
bl_fn = lambda wl, is_g: os.path.join(
    g, f'runs/v3_multilevel/baseline/{"gapbs_"+wl if is_g else wl}/latest'
)
cfg_fn = lambda tag, wl, is_g: os.path.join(
    g, f'runs/v3_final/edp_{tag}/{"gapbs_"+wl if is_g else wl}/latest'
)

# Also compare with previous EDP-opt (no squash-proportional)
prev_fn = lambda wl, is_g: os.path.join(
    g, f'runs/v3_final/edp_opt/{"gapbs_"+wl if is_g else wl}/latest'
)

print("=" * 130)
print("  EDP Config Sweep: A(base) / B(mem_blk=0.10) / C(agg fw=7) / D(B+C)")
print("  All with squash-proportional + adaptive window")
print("=" * 130)

results = {
    c: {"wpe": [], "edp": [], "mwpe": [], "medp": [], "gwpe": [], "gedp": []}
    for c in configs + ["prev"]
}

print(
    f"\n{'Workload':<28} | {'--- A ---':^14} | {'--- B ---':^14} | {'--- C ---':^14} | {'--- D ---':^14} | {'-- prev --':^14} |"
)
print(
    f"{'':28} | {'WPE':>6} {'EDP':>6} | {'WPE':>6} {'EDP':>6} | {'WPE':>6} {'EDP':>6} | {'WPE':>6} {'EDP':>6} | {'WPE':>6} {'EDP':>6} |"
)
print("-" * 125)

for wl, is_g in all_wl:
    bl = get_all(bl_fn(wl, is_g))
    bl_edp_v = edp(bl[3], bl[1])
    name = f"GAPBS-{wl}" if is_g else wl
    row = f"{name:<28} |"

    for tag in configs:
        d = get_all(cfg_fn(tag, wl, is_g))
        w = wpe(d[0], d[3], bl[0], bl[3])
        wi = (w - 1) * 100 if w else None
        e = edp(d[3], d[1])
        ei = (1 - e / bl_edp_v) * 100 if e and bl_edp_v else None
        if wi is not None:
            results[tag]["wpe"].append(wi)
            if is_g:
                results[tag]["gwpe"].append(wi)
            else:
                results[tag]["mwpe"].append(wi)
        if ei is not None:
            results[tag]["edp"].append(ei)
            if is_g:
                results[tag]["gedp"].append(ei)
            else:
                results[tag]["medp"].append(ei)
        row += f" {f(wi):>6} {f(ei):>6} |"

    # Previous EDP-opt
    pd = get_all(prev_fn(wl, is_g))
    pw = wpe(pd[0], pd[3], bl[0], bl[3])
    pwi = (pw - 1) * 100 if pw else None
    pe = edp(pd[3], pd[1])
    pei = (1 - pe / bl_edp_v) * 100 if pe and bl_edp_v else None
    if pwi is not None:
        results["prev"]["wpe"].append(pwi)
        if is_g:
            results["prev"]["gwpe"].append(pwi)
        else:
            results["prev"]["mwpe"].append(pwi)
    if pei is not None:
        results["prev"]["edp"].append(pei)
        if is_g:
            results["prev"]["gedp"].append(pei)
        else:
            results["prev"]["medp"].append(pei)
    row += f" {f(pwi):>6} {f(pei):>6} |"

    print(row)

print(f"\n{'='*80}")
print(f"  SUMMARY")
print(f"{'='*80}")
print(f"\n{'Metric':<20} {'A':>8} {'B':>8} {'C':>8} {'D':>8} {'prev':>8}")
print("-" * 60)
for label, key in [
    ("Overall WPE", "wpe"),
    ("Micro WPE", "mwpe"),
    ("GAPBS WPE", "gwpe"),
    ("Overall EDP", "edp"),
    ("Micro EDP", "medp"),
    ("GAPBS EDP", "gedp"),
]:
    vals = []
    for tag in configs + ["prev"]:
        d = results[tag][key]
        vals.append(f"{sum(d)/len(d):>+7.2f}%" if d else "     N/A")
    print(f"{label:<20} {vals[0]} {vals[1]} {vals[2]} {vals[3]} {vals[4]}")
