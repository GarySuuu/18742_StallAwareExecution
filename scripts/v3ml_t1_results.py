#!/usr/bin/env python3
import os, re, csv

def get_ipc(p):
    if not os.path.exists(p): return None
    with open(p) as f:
        for l in f:
            m = re.search(r'system\.cpu\.ipc\s+([\d.]+)', l)
            if m: return float(m.group(1))
    return None

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
                if pw and en: break
    return pw, en

def get_all(d):
    return get_ipc(os.path.join(d,'stats.txt')), *get_mcpat(os.path.join(d,'mcpat.out'))

def modes(d):
    log = os.path.join(d,'adaptive_window_log.csv')
    if not os.path.exists(log): return ''
    ms = {}; t = 0
    with open(log) as f:
        for r in csv.DictReader(f):
            t += 1; m = r.get('applied_mode',''); ms[m] = ms.get(m,0)+1
    return ' '.join(f'{k}:{v*100//t}%' for k,v in sorted(ms.items())) if t else ''

def wpe(ipc,en,bi,be):
    if None in (ipc,en,bi,be) or bi==0 or be==0: return None
    return ((ipc/bi)**0.8)*((be/en)**0.2)

def f(v): return f'{(v-1)*100:>+6.1f}%' if v else '    N/A'
def dp(n,b): return f'{(n/b-1)*100:>+6.1f}%' if n and b and b!=0 else '    N/A'

g = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ml = os.path.join(g, 'runs', 'v3_multilevel')

micro = ['balanced_pipeline_stress','phase_scan_mix','branch_entropy',
         'serialized_pointer_chase','compute_queue_pressure','stream_cluster_reduce']
gapbs_list = ['bfs','bc','pr','cc','sssp','tc']

header = "=" * 120
print(header)
print("  V3ml_t1 (multi-level + mem_block=0.12 + signal decoupling)")
print(header)

print("\nMICRO:")
print(f"{'WL':<28} {'BL':>7} {'V3t1':>7} {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'WPE':>7} | modes")
print("-" * 115)
for wl in micro:
    bl = get_all(os.path.join(ml, f'baseline/{wl}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml_t1/{wl}/latest'))
    w = wpe(v3[0], v3[2], bl[0], bl[2])
    m = modes(os.path.join(ml, f'v3ml_t1/{wl}/latest'))
    print(f"{wl:<28} {bl[0] or 0:>7.3f} {v3[0] or 0:>7.3f} {dp(v3[0],bl[0]):>7} {dp(v3[1],bl[1]):>7} {dp(v3[2],bl[2]):>7} {f(w):>7} | {m}")

print("\nGAPBS:")
print(f"{'Bench':<28} {'BL':>7} {'V3t1':>7} {'dIPC':>7} {'dPwr':>7} {'dEng':>7} {'WPE':>7} | modes")
print("-" * 115)
for b in gapbs_list:
    bl = get_all(os.path.join(ml, f'baseline/gapbs_{b}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml_t1/gapbs_{b}/latest'))
    w = wpe(v3[0], v3[2], bl[0], bl[2])
    m = modes(os.path.join(ml, f'v3ml_t1/gapbs_{b}/latest'))
    print(f"GAPBS-{b:<22} {bl[0] or 0:>7.3f} {v3[0] or 0:>7.3f} {dp(v3[0],bl[0]):>7} {dp(v3[1],bl[1]):>7} {dp(v3[2],bl[2]):>7} {f(w):>7} | {m}")

# WPE comparison
print(f"\n{'='*70}")
print("WPE: V2 vs V3ml_t1")
print(f"{'='*70}")
print(f"{'WL':<28} {'V2':>7} {'V3t1':>7} {'Win':>6}")
print("-" * 52)
v2w = v3w = 0; v2a = []; v3a = []
for wl in micro:
    bl = get_all(os.path.join(ml, f'baseline/{wl}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml_t1/{wl}/latest'))
    blo = get_all(os.path.join(g, f'runs/baseline_v3/{wl}/latest'))
    v2d = get_all(os.path.join(g, f'runs/adaptive/v3_compiled/{wl}_v2_ref/latest'))
    w2 = wpe(v2d[0],v2d[2],blo[0],blo[2])
    w3 = wpe(v3[0],v3[2],bl[0],bl[2])
    i2 = (w2-1)*100 if w2 else None
    i3 = (w3-1)*100 if w3 else None
    if i2 is not None: v2a.append(i2)
    if i3 is not None: v3a.append(i3)
    win = 'V3t1' if (i3 or -999) > (i2 or -999) else 'V2'
    if win == 'V3t1': v3w += 1
    else: v2w += 1
    print(f"{wl:<28} {f(w2):>7} {f(w3):>7} {win:>6}")

for b in gapbs_list:
    bl = get_all(os.path.join(ml, f'baseline/gapbs_{b}/latest'))
    v3 = get_all(os.path.join(ml, f'v3ml_t1/gapbs_{b}/latest'))
    blo = get_all(os.path.join(g, f'runs/baseline/formal_gapbs_{b}_g20_baseline/latest'))
    v2d = get_all(os.path.join(g, f'runs/adaptive/v3_compiled/gapbs_{b}_g20_v2_tuned/latest'))
    w2 = wpe(v2d[0],v2d[2],blo[0],blo[2])
    w3 = wpe(v3[0],v3[2],bl[0],bl[2])
    i2 = (w2-1)*100 if w2 else None
    i3 = (w3-1)*100 if w3 else None
    if i2 is not None: v2a.append(i2)
    if i3 is not None: v3a.append(i3)
    win = 'V3t1' if (i3 or -999) > (i2 or -999) else 'V2'
    if win == 'V3t1': v3w += 1
    else: v2w += 1
    print(f"GAPBS-{b:<22} {f(w2):>7} {f(w3):>7} {win:>6}")

print(f"\nV2 wins: {v2w}, V3t1 wins: {v3w}")
if v2a: print(f"V2 avg WPE: {sum(v2a)/len(v2a):+.1f}%")
if v3a: print(f"V3t1 avg WPE: {sum(v3a)/len(v3a):+.1f}%")
