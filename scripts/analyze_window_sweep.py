#!/usr/bin/env python3
"""Analyze window size sweep results."""
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


g = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sweep = os.path.join(g, "runs", "v3_multilevel", "win_sweep")

workloads = [
    "phase_scan_mix",
    "branch_entropy",
    "balanced_pipeline_stress",
    "gapbs_tc",
    "gapbs_bfs",
    "gapbs_sssp",
]
windows = [1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000]

print("=" * 130)
print("  Window Size Sweep Results")
print("=" * 130)

for wl in workloads:
    bl_path = os.path.join(g, f"runs/v3_multilevel/baseline/{wl}/latest")
    if not os.path.exists(bl_path):
        # try without gapbs_ prefix
        bl_path2 = os.path.join(
            g, f'runs/v3_multilevel/baseline/{wl.replace("gapbs_","")}/latest'
        )
        if os.path.exists(bl_path2):
            bl_path = bl_path2
    bl = get_all(bl_path)
    if bl[0] is None:
        print(f"\n{wl}: BASELINE NOT FOUND")
        continue

    bl_edp = edp(bl[3], bl[1])

    print(f"\n  {wl} (baseline IPC={bl[0]:.3f})")
    print(
        f"  {'Window':>8} {'IPC':>7} {'dIPC':>7} {'Energy':>7} {'dEng':>7} {'WPE':>7} {'EDP':>7}"
    )
    print(f"  {'-'*55}")

    best_wpe_win = None
    best_wpe = -999
    best_edp_win = None
    best_edp = -999

    for win in windows:
        d = os.path.join(sweep, f"{wl}_win{win}", "latest")
        data = get_all(d)
        if data[0] is None:
            print(f"  {win:>8}   N/A")
            continue

        w = wpe(data[0], data[3], bl[0], bl[3])
        wi = (w - 1) * 100 if w else None
        e = edp(data[3], data[1])
        ei = (1 - e / bl_edp) * 100 if e and bl_edp else None
        dipc = (data[0] / bl[0] - 1) * 100 if data[0] and bl[0] else None
        deng = (data[3] / bl[3] - 1) * 100 if data[3] and bl[3] else None

        if wi is not None and wi > best_wpe:
            best_wpe = wi
            best_wpe_win = win
        if ei is not None and ei > best_edp:
            best_edp = ei
            best_edp_win = win

        marker = ""
        if win == best_wpe_win:
            marker += " *WPE"
        if win == best_edp_win:
            marker += " *EDP"

        print(
            f"  {win:>8} {data[0]:>7.3f} {f'{dipc:>+6.1f}%' if dipc else '    N/A':>7} "
            f"{f'{data[3]:.3f}' if data[3] else 'N/A':>7} {f'{deng:>+6.1f}%' if deng else '    N/A':>7} "
            f"{f(wi):>7} {f(ei):>7}{marker}"
        )

    print(f"  Best WPE: window={best_wpe_win} ({best_wpe:+.1f}%)")
    print(f"  Best EDP: window={best_edp_win} ({best_edp:+.1f}%)")
