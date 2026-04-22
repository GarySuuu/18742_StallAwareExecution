#!/usr/bin/env python3
import re, os, csv


def get(p, pat):
    if not os.path.exists(p):
        return None
    with open(p) as f:
        for l in f:
            m = re.search(pat, l)
            if m:
                return float(m.group(1))
    return None


def mcpat_vals(p):
    if not os.path.exists(p):
        return None, None
    pw = en = None
    s = False
    with open(p) as f:
        for l in f:
            if "System:" in l and "Core" not in l:
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


def modes(d):
    log = os.path.join(d, "adaptive_window_log.csv")
    if not os.path.exists(log):
        return ""
    ms = {}
    rp = {}
    t = 0
    with open(log) as f:
        for r in csv.DictReader(f):
            t += 1
            m = r.get("applied_mode", "")
            ms[m] = ms.get(m, 0) + 1
            p = r.get("resource_profile_level", "na")
            if p != "na":
                rp[p] = rp.get(p, 0) + 1
    parts = [f"{k}:{v*100//max(t,1)}%" for k, v in sorted(ms.items())]
    for k, v in sorted(rp.items()):
        parts.append(f"{k}:{v}")
    return ", ".join(parts)


g = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = os.path.join(g, "runs", "v4_presentation", "showcase")

print("=" * 90)
print("  Showcase Workload Results")
print("=" * 90)

for wl, label in [
    ("adaptive_showcase_best", "BEST CASE (memory-dependent branchy)"),
    ("adaptive_showcase_neutral", "NEUTRAL CASE (pure integer compute)"),
]:
    bl_s = os.path.join(base, f"{wl}_baseline/latest/stats.txt")
    v4_s = os.path.join(base, f"{wl}_v4/latest/stats.txt")
    bl_m = os.path.join(base, f"{wl}_baseline/latest/mcpat.out")
    v4_m = os.path.join(base, f"{wl}_v4/latest/mcpat.out")

    bl_ipc = get(bl_s, r"system\.cpu\.ipc\s+([\d.]+)")
    v4_ipc = get(v4_s, r"system\.cpu\.ipc\s+([\d.]+)")
    bl_t = get(bl_s, r"simTicks\s+(\d+)")
    v4_t = get(v4_s, r"simTicks\s+(\d+)")
    bl_pw, bl_en = mcpat_vals(bl_m)
    v4_pw, v4_en = mcpat_vals(v4_m)

    bl_edp = bl_en * bl_t / 1e12 if bl_en and bl_t else None
    v4_edp = v4_en * v4_t / 1e12 if v4_en and v4_t else None

    dipc = (v4_ipc / bl_ipc - 1) * 100 if v4_ipc and bl_ipc else None
    dpwr = (v4_pw / bl_pw - 1) * 100 if v4_pw and bl_pw else None
    deng = (v4_en / bl_en - 1) * 100 if v4_en and bl_en else None
    dedp = (1 - v4_edp / bl_edp) * 100 if v4_edp and bl_edp else None

    mode_str = modes(os.path.join(base, f"{wl}_v4/latest"))

    f_pct = lambda v: f"{v:>+6.1f}%" if v is not None else "    N/A"

    print(f"\n  {label}")
    print(f"  {'':8} {'Baseline':>12} {'V4':>12} {'Change':>10}")
    print(
        f"  {'IPC':8} {bl_ipc or 0:>12.3f} {v4_ipc or 0:>12.3f} {f_pct(dipc):>10}"
    )
    print(
        f"  {'Power':8} {f'{bl_pw:.1f}W' if bl_pw else 'N/A':>12} {f'{v4_pw:.1f}W' if v4_pw else 'N/A':>12} {f_pct(dpwr):>10}"
    )
    print(
        f"  {'Energy':8} {f'{bl_en:.3f}J' if bl_en else 'N/A':>12} {f'{v4_en:.3f}J' if v4_en else 'N/A':>12} {f_pct(deng):>10}"
    )
    print(
        f"  {'EDP':8} {f'{bl_edp:.5f}' if bl_edp else 'N/A':>12} {f'{v4_edp:.5f}' if v4_edp else 'N/A':>12} {f_pct(dedp):>10}"
    )
    print(f"  Modes: {mode_str}")
