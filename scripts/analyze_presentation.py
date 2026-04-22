#!/usr/bin/env python3
"""Analyze presentation results: showcase workloads + 4-core."""
import os, re


def get_stat(path, pattern):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        for l in f:
            m = re.search(pattern, l)
            if m:
                return float(m.group(1))
    return None


def get_ipc(p):
    return get_stat(p, r"system\.cpu\.ipc\s+([\d.]+)")


def get_ticks(p):
    return get_stat(p, r"simTicks\s+(\d+)")


# For multicore, per-cpu IPC
def get_cpu_ipc(p, idx):
    return (
        get_stat(p, rf"system\.cpu{idx}\.ipc\s+([\d.]+)")
        if idx > 0
        else get_stat(p, r"system\.cpu\.ipc\s+([\d.]+)")
    )


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


def edp(en, ticks):
    if en is None or ticks is None:
        return None
    return en * (ticks / 1e12)


def f(v):
    return f"{v:>+6.1f}%" if v is not None else "    N/A"


g = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = os.path.join(g, "runs", "v4_presentation")

print("=" * 100)
print("  PRESENTATION RESULTS")
print("=" * 100)

# Part 1: Showcase workloads
print("\n  Part 1: Showcase Workloads (single core, 50M instructions)")
print("-" * 90)

for wl, label in [
    ("adaptive_showcase_best", "Best Case (phase-changing)"),
    ("adaptive_showcase_neutral", "Neutral Case (pure compute)"),
]:
    bl_stats = os.path.join(base, f"showcase/{wl}_baseline/latest/stats.txt")
    v4_stats = os.path.join(base, f"showcase/{wl}_v4/latest/stats.txt")
    bl_mcpat = os.path.join(base, f"showcase/{wl}_baseline/latest/mcpat.out")
    v4_mcpat = os.path.join(base, f"showcase/{wl}_v4/latest/mcpat.out")

    bl_ipc = get_ipc(bl_stats)
    v4_ipc = get_ipc(v4_stats)
    bl_ticks = get_ticks(bl_stats)
    v4_ticks = get_ticks(v4_stats)
    bl_pw, bl_en = get_mcpat(bl_mcpat)
    v4_pw, v4_en = get_mcpat(v4_mcpat)

    bl_edp = edp(bl_en, bl_ticks)
    v4_edp = edp(v4_en, v4_ticks)
    edp_imp = (1 - v4_edp / bl_edp) * 100 if v4_edp and bl_edp else None

    dipc = (v4_ipc / bl_ipc - 1) * 100 if v4_ipc and bl_ipc else None
    dpwr = (v4_pw / bl_pw - 1) * 100 if v4_pw and bl_pw else None
    deng = (v4_en / bl_en - 1) * 100 if v4_en and bl_en else None

    print(f"\n  {label}: {wl}")
    print(f"  {'':4} {'Baseline':>10} {'V4':>10} {'Change':>10}")
    print(
        f"  {'IPC':4} {bl_ipc or 0:>10.3f} {v4_ipc or 0:>10.3f} {f(dipc):>10}"
    )
    print(
        f"  {'Power':4} {bl_pw or 0:>9.1f}W {v4_pw or 0:>9.1f}W {f(dpwr):>10}"
    )
    print(
        f"  {'Energy':4} {bl_en or 0:>9.3f}J {v4_en or 0:>9.3f}J {f(deng):>10}"
    )
    print(
        f"  {'EDP':4} {bl_edp or 0:>10.4f} {v4_edp or 0:>10.4f} {f(edp_imp):>10}"
    )

# Part 2: 4-core multicore
print("\n\n  Part 2: 4-Core Multicore Experiment")
print("-" * 90)

bl_dir = os.path.join(base, "multicore/baseline_4core/latest")
v4_dir = os.path.join(base, "multicore/v4_4core/latest")

bl_ticks = get_ticks(os.path.join(bl_dir, "stats.txt"))
v4_ticks = get_ticks(os.path.join(v4_dir, "stats.txt"))
bl_pw, bl_en = get_mcpat(os.path.join(bl_dir, "mcpat.out"))
v4_pw, v4_en = get_mcpat(os.path.join(v4_dir, "mcpat.out"))

bl_edp = edp(bl_en, bl_ticks)
v4_edp = edp(v4_en, v4_ticks)
edp_imp = (1 - v4_edp / bl_edp) * 100 if v4_edp and bl_edp else None
dpwr = (v4_pw / bl_pw - 1) * 100 if v4_pw and bl_pw else None
deng = (v4_en / bl_en - 1) * 100 if v4_en and bl_en else None
dticks = (v4_ticks / bl_ticks - 1) * 100 if v4_ticks and bl_ticks else None

wl_names = [
    "serialized_pointer_chase",
    "branch_entropy",
    "phase_scan_mix",
    "compute_queue_pressure",
]

print(f"\n  System-level:")
print(f"  {'':8} {'Baseline':>12} {'V4':>12} {'Change':>10}")
print(
    f"  {'simTicks':8} {bl_ticks or 0:>12} {v4_ticks or 0:>12} {f(dticks):>10}"
)
print(f"  {'Power':8} {bl_pw or 0:>11.1f}W {v4_pw or 0:>11.1f}W {f(dpwr):>10}")
print(
    f"  {'Energy':8} {bl_en or 0:>11.3f}J {v4_en or 0:>11.3f}J {f(deng):>10}"
)
print(
    f"  {'EDP':8} {bl_edp or 0:>12.4f} {v4_edp or 0:>12.4f} {f(edp_imp):>10}"
)

print(f"\n  Per-CPU IPC:")
bl_stats = os.path.join(bl_dir, "stats.txt")
v4_stats = os.path.join(v4_dir, "stats.txt")

for i, wl in enumerate(wl_names):
    bi = get_cpu_ipc(bl_stats, i)
    vi = get_cpu_ipc(v4_stats, i)
    dipc = (vi / bi - 1) * 100 if vi and bi else None
    print(
        f"  CPU{i} ({wl[:20]:20}) BL={bi or 0:.3f} V4={vi or 0:.3f} {f(dipc)}"
    )
