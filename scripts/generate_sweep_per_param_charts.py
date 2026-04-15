#!/usr/bin/env python3
"""
Generate per-parameter × per-signal charts for the dense parameter sweep.
Each parameter group gets one figure with subplots for every observed signal.
"""

import csv
import os
import re
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
C_LIME = '#CDDC39'
C_BROWN = '#795548'

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
    try:
        return float(v)
    except ValueError:
        return 0.0

def safe_int(r, key):
    v = r.get(key, '') or '0'
    try:
        return int(v)
    except ValueError:
        return 0

def pct_of(num_key, denom_keys, r):
    """Compute num / sum(denoms) * 100."""
    num = safe_int(r, num_key)
    denom = sum(safe_int(r, k) for k in denom_keys)
    return num / denom * 100.0 if denom else 0.0


# Signal definitions: (display_name, extraction_function, unit, color)
def define_signals():
    return [
        ('IPC', lambda r: safe_float(r, 'ipc'), '', C_BLUE),
        ('Fetch Width Mean\n(fetch.nisnDist::mean)', lambda r: safe_float(r, 'fetch_nisnDist_mean'), 'insns/cyc', C_INDIGO),
        ('Fetch Idle %\n(fetch_nisnDist::0 / samples)', lambda r: safe_int(r, 'fetch_nisnDist_0') / max(safe_int(r, 'fetch_nisnDist_samples'), 1) * 100, '%', C_TEAL),
        ('Fetch Full-Width %\n(fetch_nisnDist::8 / samples)', lambda r: safe_int(r, 'fetch_nisnDist_8') / max(safe_int(r, 'fetch_nisnDist_samples'), 1) * 100, '%', C_GREEN),
        ('Issue Rate Mean\n(numIssuedDist::mean)', lambda r: safe_float(r, 'numIssuedDist_mean'), 'insns/cyc', C_ORANGE),
        ('Commit Rate Mean\n(commit.numCommittedDist::mean)', lambda r: safe_float(r, 'commit_numCommittedDist_mean'), 'insns/cyc', C_RED),
        ('Decode Blocked %\n(decode.blockedCycles / total)', lambda r: pct_of('decode_blockedCycles', ['decode_idleCycles','decode_blockedCycles','decode_runCycles'], r), '%', C_PURPLE),
        ('Rename Blocked %\n(rename.blockCycles / total)', lambda r: pct_of('rename_blockCycles', ['rename_idleCycles','rename_blockCycles','rename_runCycles'], r), '%', C_PINK),
        ('IQ Full Events\n(rename.IQFullEvents)', lambda r: safe_int(r, 'rename_IQFullEvents') / 1e6, 'millions', C_RED),
        ('LQ Full Events\n(rename.LQFullEvents)', lambda r: safe_int(r, 'rename_LQFullEvents') / 1e6, 'millions', C_TEAL),
        ('SQ Full Events\n(rename.SQFullEvents)', lambda r: safe_int(r, 'rename_SQFullEvents') / 1e6, 'millions', C_LIME),
        ('ROB Full Events\n(rename.ROBFullEvents)', lambda r: safe_int(r, 'rename_ROBFullEvents') / 1e6, 'millions', C_BROWN),
        ('Store-to-Load Forwarding\n(lsq0.forwLoads)', lambda r: safe_int(r, 'lsq_forwLoads') / 1e6, 'millions', C_BLUE),
        ('Mem Order Violations\n(lsq0.memOrderViolation)', lambda r: safe_int(r, 'lsq_memOrderViolation') / 1e3, 'thousands', C_RED),
        ('ROB Writes\n(rob.writes)', lambda r: safe_int(r, 'rob_writes') / 1e6, 'millions', C_ORANGE),
        ('Fetch Squash Cycles\n(fetch.squashCycles)', lambda r: safe_int(r, 'fetch_squashCycles') / 1e6, 'millions', C_PURPLE),
        ('Branch Mispredicts\n(commit.branchMispredicts)', lambda r: safe_int(r, 'commit_branchMispredicts') / 1e3, 'thousands', C_PINK),
    ]


def make_param_chart(rows, bl, param_name, tags, x_values, x_label, signals, chart_dir):
    """Generate one multi-panel figure for a parameter group."""
    n_signals = len(signals)
    ncols = 3
    nrows = (n_signals + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 4.2 * nrows))
    axes_flat = axes.flatten() if hasattr(axes, 'flatten') else [axes]

    fig.suptitle(f'Parameter Sweep: {param_name}\n(baseline IPC = {safe_float(bl, "ipc"):.3f})',
                 fontsize=16, fontweight='bold', y=1.0)

    b_ipc = safe_float(bl, 'ipc')

    # Collect data
    available_tags = []
    available_x = []
    for tag, xv in zip(tags, x_values):
        r = get(rows, tag)
        if r:
            available_tags.append(tag)
            available_x.append(xv)

    if not available_tags:
        plt.close()
        return

    for idx, (sig_name, sig_fn, sig_unit, sig_color) in enumerate(signals):
        if idx >= len(axes_flat):
            break
        ax = axes_flat[idx]

        y_vals = []
        for tag in available_tags:
            r = get(rows, tag)
            y_vals.append(sig_fn(r) if r else 0)

        bl_val = sig_fn(bl)

        # Use string x-labels for even spacing
        x_labels = [str(v) for v in available_x]
        x_pos = np.arange(len(x_labels))

        ax.bar(x_pos, y_vals, color=sig_color, alpha=0.75, edgecolor='white', linewidth=0.5)
        ax.axhline(y=bl_val, color='black', linestyle='--', linewidth=1.0, alpha=0.7, label=f'baseline={bl_val:.2f}')

        # Find and highlight the best point (for IPC: max; for blocked%: min is better)
        if 'Blocked' in sig_name or 'Full' in sig_name or 'Squash' in sig_name or 'Violation' in sig_name:
            best_idx = y_vals.index(min(y_vals))
            best_label = 'min'
        else:
            best_idx = y_vals.index(max(y_vals))
            best_label = 'max'

        ax.bar(x_pos[best_idx], y_vals[best_idx], color=sig_color, alpha=1.0,
               edgecolor=C_GREEN, linewidth=2.5)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, fontsize=7, rotation=45 if len(x_labels) > 10 else 0)
        ax.set_xlabel(x_label, fontsize=9)
        ax.set_ylabel(f'{sig_unit}' if sig_unit else 'value', fontsize=9)
        ax.set_title(sig_name, fontsize=9, fontweight='bold')
        ax.legend(fontsize=7, loc='best')
        ax.tick_params(labelsize=7)

    # Hide unused subplots
    for idx in range(n_signals, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fname = f'sweep_detail_{param_name.lower().replace(" ","_").replace("/","_").replace("(","").replace(")","")}.png'
    plt.savefig(os.path.join(chart_dir, fname), dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved {fname}')


def main():
    gem5_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(gem5_root, 'results', 'sweep_signals.csv')
    chart_dir = os.path.join(gem5_root, 'results', 'charts')
    os.makedirs(chart_dir, exist_ok=True)

    rows = load_data(csv_path)
    bl = baseline(rows)
    signals = define_signals()

    # Group 1: Fetch Width 1-8
    make_param_chart(rows, bl, 'Fetch Width',
        [f'fw{i}' for i in range(1, 9)],
        list(range(1, 9)),
        'Fetch Width', signals, chart_dir)

    # Group 2: IQ Cap
    iq_vals = [8, 12, 16, 20, 22, 24, 26, 28, 30, 32, 40, 48, 0]
    iq_labels = [str(v) if v > 0 else 'off' for v in iq_vals]
    make_param_chart(rows, bl, 'IQ Cap',
        [f'iqcap{v}' for v in iq_vals],
        iq_labels,
        'IQ Cap', signals, chart_dir)

    # Group 3: LSQ Cap
    lsq_vals = [4, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 0]
    lsq_labels = [str(v) if v > 0 else 'off' for v in lsq_vals]
    make_param_chart(rows, bl, 'LSQ Cap',
        [f'lsqcap{v}' for v in lsq_vals],
        lsq_labels,
        'LSQ Cap', signals, chart_dir)

    # Group 4: Inflight Cap
    rob_vals = [24, 32, 40, 48, 52, 56, 60, 64, 68, 72, 80, 96, 112, 128, 160, 0]
    rob_labels = [str(v) if v > 0 else 'off' for v in rob_vals]
    make_param_chart(rows, bl, 'Inflight Cap ROB',
        [f'robcap{v}' for v in rob_vals],
        rob_labels,
        'Inflight Cap', signals, chart_dir)

    # Group 5: Rename Width 1-8
    make_param_chart(rows, bl, 'Rename Width',
        [f'rw{i}' for i in range(1, 9)],
        list(range(1, 9)),
        'Rename Width', signals, chart_dir)

    # Group 6: Dispatch Width 1-8
    make_param_chart(rows, bl, 'Dispatch Width',
        [f'dw{i}' for i in range(1, 9)],
        list(range(1, 9)),
        'Dispatch Width', signals, chart_dir)

    print('\nAll per-parameter detail charts generated.')


if __name__ == '__main__':
    main()
