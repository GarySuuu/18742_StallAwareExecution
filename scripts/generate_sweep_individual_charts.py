#!/usr/bin/env python3
"""
Generate individual charts: one PNG per (parameter_group x signal).
Output structure: results/charts/sweep/{param_group}/{signal_name}.png
"""

import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

C_BLUE = '#2196F3'
C_RED = '#F44336'
C_GREEN = '#4CAF50'
C_ORANGE = '#FF9800'
C_PURPLE = '#9C27B0'
C_TEAL = '#009688'
C_PINK = '#E91E63'
C_INDIGO = '#3F51B5'

def load_data(csv_path):
    with open(csv_path) as f:
        return list(csv.DictReader(f))

def get(rows, tag):
    for r in rows:
        if r['experiment'] == f'sweep_{tag}':
            return r
    return None

def baseline(rows):
    for r in rows:
        if r['experiment'] == 'baseline':
            return r
    return None

def safe_float(r, key):
    v = r.get(key, '') or '0'
    try: return float(v)
    except: return 0.0

def safe_int(r, key):
    v = r.get(key, '') or '0'
    try: return int(v)
    except: return 0

def pct_of(num_key, denom_keys, r):
    num = safe_int(r, num_key)
    denom = sum(safe_int(r, k) for k in denom_keys)
    return num / denom * 100.0 if denom else 0.0

def define_signals():
    return [
        ('IPC', 'ipc', lambda r: safe_float(r, 'ipc'), '', C_BLUE),
        ('Fetch Mean (insns per cycle)', 'fetch_mean', lambda r: safe_float(r, 'fetch_nisnDist_mean'), 'insns/cyc', C_INDIGO),
        ('Fetch Idle Pct (nisnDist 0)', 'fetch_idle_pct', lambda r: safe_int(r, 'fetch_nisnDist_0') / max(safe_int(r, 'fetch_nisnDist_samples'), 1) * 100, '%', C_TEAL),
        ('Fetch Full-Width Pct (nisnDist 8)', 'fetch_full_pct', lambda r: safe_int(r, 'fetch_nisnDist_8') / max(safe_int(r, 'fetch_nisnDist_samples'), 1) * 100, '%', C_GREEN),
        ('Issue Rate Mean', 'issue_rate_mean', lambda r: safe_float(r, 'numIssuedDist_mean'), 'insns/cyc', C_ORANGE),
        ('Commit Rate Mean', 'commit_rate_mean', lambda r: safe_float(r, 'commit_numCommittedDist_mean'), 'insns/cyc', C_RED),
        ('Decode Blocked Pct', 'decode_blocked_pct', lambda r: pct_of('decode_blockedCycles', ['decode_idleCycles','decode_blockedCycles','decode_runCycles'], r), '%', C_PURPLE),
        ('Rename Blocked Pct', 'rename_blocked_pct', lambda r: pct_of('rename_blockCycles', ['rename_idleCycles','rename_blockCycles','rename_runCycles'], r), '%', C_PINK),
        ('IQ Full Events (millions)', 'iq_full_events', lambda r: safe_int(r, 'rename_IQFullEvents') / 1e6, 'millions', C_RED),
        ('LQ Full Events (millions)', 'lq_full_events', lambda r: safe_int(r, 'rename_LQFullEvents') / 1e6, 'millions', C_TEAL),
        ('SQ Full Events (millions)', 'sq_full_events', lambda r: safe_int(r, 'rename_SQFullEvents') / 1e6, 'millions', C_GREEN),
        ('Store-to-Load Forwarding (millions)', 'forwLoads', lambda r: safe_int(r, 'lsq_forwLoads') / 1e6, 'millions', C_BLUE),
        ('Mem Order Violations (thousands)', 'mem_order_viol', lambda r: safe_int(r, 'lsq_memOrderViolation') / 1e3, 'thousands', C_RED),
        ('ROB Writes (millions)', 'rob_writes', lambda r: safe_int(r, 'rob_writes') / 1e6, 'millions', C_ORANGE),
        ('Fetch Squash Cycles (millions)', 'fetch_squash_cycles', lambda r: safe_int(r, 'fetch_squashCycles') / 1e6, 'millions', C_PURPLE),
        ('Branch Mispredicts (thousands)', 'branch_mispredicts', lambda r: safe_int(r, 'commit_branchMispredicts') / 1e3, 'thousands', C_PINK),
    ]


def make_single_chart(rows, bl, param_name, tags, x_labels, x_label_axis,
                      sig_display, sig_slug, sig_fn, sig_unit, sig_color, out_dir):
    available = []
    for tag, xl in zip(tags, x_labels):
        r = get(rows, tag)
        if r:
            available.append((xl, sig_fn(r)))
    if not available:
        return None

    bl_val = sig_fn(bl)
    xs = [a[0] for a in available]
    ys = [a[1] for a in available]

    fig, ax = plt.subplots(figsize=(max(8, len(xs) * 0.7), 5))
    x_pos = np.arange(len(xs))
    bars = ax.bar(x_pos, ys, color=sig_color, alpha=0.8, edgecolor='white', linewidth=0.5)
    ax.axhline(y=bl_val, color='black', linestyle='--', linewidth=1.2, alpha=0.7,
               label=f'baseline = {bl_val:.3f}')

    if any(k in sig_slug for k in ['blocked', 'full', 'squash', 'viol']):
        best_idx = ys.index(min(ys))
    else:
        best_idx = ys.index(max(ys))
    bars[best_idx].set_edgecolor(C_GREEN)
    bars[best_idx].set_linewidth(2.5)

    for i, (bar, y) in enumerate(zip(bars, ys)):
        if y == 0 and bl_val == 0:
            continue
        if sig_unit == '%':
            txt = f'{y:.1f}%'
        elif 'million' in sig_unit:
            txt = f'{y:.2f}M'
        elif 'thousand' in sig_unit:
            txt = f'{y:.1f}K'
        else:
            txt = f'{y:.3f}'
        fontsize = 7 if len(xs) > 10 else 8
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                txt, ha='center', va='bottom', fontsize=fontsize,
                rotation=45 if len(xs) > 10 else 0)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(xs, fontsize=8, rotation=45 if len(xs) > 10 else 0)
    ax.set_xlabel(x_label_axis, fontsize=11)
    ax.set_ylabel(sig_unit if sig_unit else 'value', fontsize=11)
    ax.set_title(f'{param_name} Sweep: {sig_display}', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9)

    if ys[best_idx] != bl_val and bl_val != 0:
        ax.annotate(f'best: {xs[best_idx]}',
                    xy=(best_idx, ys[best_idx]),
                    xytext=(best_idx + min(1.5, len(xs)*0.1), max(ys) * 1.02),
                    fontsize=9, fontweight='bold', color=C_GREEN,
                    arrowprops=dict(arrowstyle='->', color=C_GREEN, lw=1.5))

    plt.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    fpath = os.path.join(out_dir, f'{sig_slug}.png')
    plt.savefig(fpath, dpi=140, bbox_inches='tight')
    plt.close()
    return fpath


def main():
    gem5_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(gem5_root, 'results', 'sweep_signals.csv')
    chart_base = os.path.join(gem5_root, 'results', 'charts', 'sweep')

    rows = load_data(csv_path)
    bl = baseline(rows)
    signals = define_signals()

    param_groups = [
        ('Fetch Width', 'fetch_width',
         [f'fw{i}' for i in range(1, 9)], [str(i) for i in range(1, 9)], 'Fetch Width'),
        ('IQ Cap', 'iq_cap',
         [f'iqcap{v}' for v in [8,12,16,20,22,24,26,28,30,32,40,48,0]],
         [str(v) for v in [8,12,16,20,22,24,26,28,30,32,40,48]] + ['off'], 'IQ Cap'),
        ('LSQ Cap', 'lsq_cap',
         [f'lsqcap{v}' for v in [4,8,10,12,14,16,18,20,22,24,26,28,0]],
         [str(v) for v in [4,8,10,12,14,16,18,20,22,24,26,28]] + ['off'], 'LSQ Cap'),
        ('Inflight Cap (ROB)', 'inflight_cap',
         [f'robcap{v}' for v in [24,32,40,48,52,56,60,64,68,72,80,96,112,128,160,0]],
         [str(v) for v in [24,32,40,48,52,56,60,64,68,72,80,96,112,128,160]] + ['off'], 'Inflight Cap'),
        ('Rename Width', 'rename_width',
         [f'rw{i}' for i in range(1, 9)], [str(i) for i in range(1, 9)], 'Rename Width'),
        ('Dispatch Width', 'dispatch_width',
         [f'dw{i}' for i in range(1, 9)], [str(i) for i in range(1, 9)], 'Dispatch Width'),
    ]

    total = 0
    for pname, pslug, tags, xlabels, xlabel_axis in param_groups:
        out_dir = os.path.join(chart_base, pslug)
        for sig_display, sig_slug, sig_fn, sig_unit, sig_color in signals:
            fpath = make_single_chart(rows, bl, pname, tags, xlabels, xlabel_axis,
                                     sig_display, sig_slug, sig_fn, sig_unit, sig_color, out_dir)
            if fpath:
                total += 1
        print(f'  {pname}: {len(signals)} charts -> {out_dir}')

    print(f'\nTotal: {total} individual charts generated.')


if __name__ == '__main__':
    main()
