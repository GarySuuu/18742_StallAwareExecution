#!/usr/bin/env python3
"""Final V3 report: Baseline / V2 / V3-final with IPC, Power, Energy, WPE."""
import os, re

def get_stat(path, pattern):
    if not os.path.exists(path): return None
    with open(path) as f:
        for line in f:
            m = re.search(pattern, line)
            if m: return float(m.group(1))
    return None

def get_ipc(p): return get_stat(p, r'system\.cpu\.ipc\s+([\d.]+)')

def get_mcpat(p):
    if not os.path.exists(p): return None, None
    pw = en = None; s = False
    with open(p) as f:
        for l in f:
            if 'System:' in l: s = True; continue
            if s:
                m = re.search(r'Runtime Dynamic Power\s*=\s*([\d.]+)\s*W', l)
                if m and pw is None: pw = float(m.group(1))
                m2 = re.search(r'Total Runtime Energy\s*=\s*([\d.]+)\s*J', l)
                if m2 and en is None: en = float(m2.group(1))
                if pw is not None and en is not None: break
    return pw, en

def get_all(d):
    ipc = get_ipc(os.path.join(d, 'stats.txt'))
    pw, en = get_mcpat(os.path.join(d, 'mcpat.out'))
    return ipc, pw, en

def wpe(ipc, en, bi, be):
    if None in (ipc, en, bi, be) or bi == 0 or be == 0: return None
    return ((ipc/bi)**0.8) * ((be/en)**0.2)

def dp(n, b):
    if n is None or b is None or b == 0: return None
    return (n/b - 1) * 100

def fmt_pct(v):
    if v is not None: return f"{v:>+6.1f}%"
    return "    N/A"

def fmt_val(v, d=3):
    if v is not None: return f"{v:.{d}f}"
    return "N/A"

gem5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ml = os.path.join(gem5, 'runs', 'v3_multilevel')

# Paths
micro_wl = ['balanced_pipeline_stress', 'phase_scan_mix', 'branch_entropy',
            'serialized_pointer_chase', 'compute_queue_pressure', 'stream_cluster_reduce']
gapbs_list = ['bfs', 'bc', 'pr', 'cc', 'sssp', 'tc']

# V3-final: micro=v3t3, GAPBS=v3t4
def v3_micro(wl): return os.path.join(ml, f'v3ml_t3/{wl}/latest')
def v3_gapbs(b): return os.path.join(ml, f'v3t4_cand2/gapbs_{b}/latest')
def bl_micro(wl): return os.path.join(ml, f'baseline/{wl}/latest')
def bl_gapbs(b): return os.path.join(ml, f'baseline/gapbs_{b}/latest')
def v2_micro(wl): return os.path.join(gem5, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest')
def v2_gapbs(b): return os.path.join(gem5, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest')
def bl_v2_micro(wl): return os.path.join(gem5, f'runs/baseline_v3/{wl}/latest')
def bl_v2_gapbs(b): return os.path.join(gem5, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest')

sep = "=" * 160

print(sep)
print("  FINAL V3 RESULTS: Baseline / V2 / V3-final")
print("  V3-final = v3t3 micro (fw=6,cap=56,iq=26,lsq=28,win=5000) + v3t4 GAPBS (fw=4,cap=128,iq=0,lsq=0,win=2500)")
print("  WPE = (IPC_ratio)^0.8 × (Energy_bl/Energy_new)^0.2")
print(sep)

all_data = []

for section, workloads, bl_fn, v2_fn, v3_fn, bl_v2_fn, prefix in [
    ("MICROBENCHMARKS (50M instructions)", micro_wl, bl_micro, v2_micro, v3_micro, bl_v2_micro, ""),
    ("GAPBS FORMAL BENCHMARKS (g20, 50M instructions)", gapbs_list, bl_gapbs, v2_gapbs, v3_gapbs, bl_v2_gapbs, "GAPBS-"),
]:
    print(f"\n  {section}")
    print(f"{'Workload':<28} | {'--- Baseline ---':^22} | {'--- V2 vs BL ---':^40} | {'--- V3-final vs BL ---':^40} |")
    print(f"{'':28} | {'IPC':>7} {'Pwr(W)':>7} {'Eng(J)':>7} | {'IPC':>7} {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'WPE':>7} | {'IPC':>7} {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'WPE':>7} |")
    print("-" * 155)

    for wl in workloads:
        bl = get_all(bl_fn(wl))
        v2 = get_all(v2_fn(wl))
        v3 = get_all(v3_fn(wl))
        bl_v2 = get_all(bl_v2_fn(wl))

        v2_wpe = wpe(v2[0], v2[2], bl_v2[0], bl_v2[2])
        v3_wpe = wpe(v3[0], v3[2], bl[0], bl[2])

        name = f"{prefix}{wl}"

        print(f"{name:<28} | {fmt_val(bl[0]):>7} {fmt_val(bl[1],1):>7} {fmt_val(bl[2]):>7} "
              f"| {fmt_val(v2[0]):>7} {fmt_pct(dp(v2[0],bl_v2[0])):>7} {fmt_pct(dp(v2[1],bl_v2[1])):>7} {fmt_pct(dp(v2[2],bl_v2[2])):>7} {fmt_pct((v2_wpe-1)*100 if v2_wpe else None):>7} "
              f"| {fmt_val(v3[0]):>7} {fmt_pct(dp(v3[0],bl[0])):>7} {fmt_pct(dp(v3[1],bl[1])):>7} {fmt_pct(dp(v3[2],bl[2])):>7} {fmt_pct((v3_wpe-1)*100 if v3_wpe else None):>7} |")

        all_data.append({
            'name': name,
            'section': 'micro' if not prefix else 'gapbs',
            'v2_wpe': (v2_wpe-1)*100 if v2_wpe else None,
            'v3_wpe': (v3_wpe-1)*100 if v3_wpe else None,
            'bl_ipc': bl[0], 'v2_ipc': v2[0], 'v3_ipc': v3[0],
            'bl_pwr': bl[1], 'v2_pwr': v2[1], 'v3_pwr': v3[1],
            'bl_eng': bl[2], 'v2_eng': v2[2], 'v3_eng': v3[2],
        })

# Summary
print(f"\n{sep}")
print("  WPE SUMMARY")
print(sep)
print(f"\n{'Workload':<28} {'V2 WPE':>8} {'V3 WPE':>8} {'Winner':>8} {'Margin':>8}")
print("-" * 58)

v2_wins = v3_wins = ties = 0
v2_all = []; v3_all = []
v2_micro = []; v3_micro_l = []
v2_gapbs_l = []; v3_gapbs_l = []

for d in all_data:
    v2w = d['v2_wpe']; v3w = d['v3_wpe']
    if v2w is not None: v2_all.append(v2w)
    if v3w is not None: v3_all.append(v3w)
    if d['section'] == 'micro':
        if v2w is not None: v2_micro.append(v2w)
        if v3w is not None: v3_micro_l.append(v3w)
    else:
        if v2w is not None: v2_gapbs_l.append(v2w)
        if v3w is not None: v3_gapbs_l.append(v3w)

    if v2w is None or v3w is None:
        w = "N/A"; margin = ""
    elif abs(v3w - v2w) < 0.05:
        w = "TIE"; ties += 1; margin = ""
    elif v3w > v2w:
        w = "V3"; v3_wins += 1; margin = f"+{v3w-v2w:.1f}pp"
    else:
        w = "V2"; v2_wins += 1; margin = f"+{v2w-v3w:.1f}pp"

    print(f"{d['name']:<28} {fmt_pct(v2w):>8} {fmt_pct(v3w):>8} {w:>8} {margin:>8}")

print(f"\n{'':28} {'V2':>12} {'V3-final':>12}")
print(f"{'Wins':28} {v2_wins:>12} {v3_wins:>12}")
print(f"{'Ties':28} {ties:>12} {ties:>12}")
if v2_all: print(f"{'Overall avg WPE':28} {sum(v2_all)/len(v2_all):>+11.2f}% {sum(v3_all)/len(v3_all):>+11.2f}%")
if v2_micro: print(f"{'Micro avg WPE':28} {sum(v2_micro)/len(v2_micro):>+11.2f}% {sum(v3_micro_l)/len(v3_micro_l):>+11.2f}%")
if v2_gapbs_l: print(f"{'GAPBS avg WPE':28} {sum(v2_gapbs_l)/len(v2_gapbs_l):>+11.2f}% {sum(v3_gapbs_l)/len(v3_gapbs_l):>+11.2f}%")
