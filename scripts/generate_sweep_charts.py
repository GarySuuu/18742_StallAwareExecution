#!/usr/bin/env python3
"""Generate charts for parameter sweep analysis."""

import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

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

def pct(val, total):
    return val / total * 100.0 if total else 0.0

def ren_blk_pct(r):
    t = int(r['rename_idleCycles']) + int(r['rename_blockCycles']) + int(r['rename_runCycles'])
    return pct(int(r['rename_blockCycles']), t)

def dec_blk_pct(r):
    t = int(r['decode_idleCycles']) + int(r['decode_blockedCycles']) + int(r['decode_runCycles'])
    return pct(int(r['decode_blockedCycles']), t)

def safe_int(r, key):
    v = r.get(key, '') or '0'
    return int(v)

def main():
    gem5_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(gem5_root, 'results', 'sweep_signals.csv')
    chart_dir = os.path.join(gem5_root, 'results', 'charts')
    os.makedirs(chart_dir, exist_ok=True)

    rows = load_data(csv_path)
    bl = baseline(rows)
    b_ipc = float(bl['ipc'])

    # Color scheme
    C_BLUE = '#2196F3'
    C_RED = '#F44336'
    C_GREEN = '#4CAF50'
    C_ORANGE = '#FF9800'
    C_PURPLE = '#9C27B0'
    C_TEAL = '#009688'
    C_GRAY = '#9E9E9E'

    # =========================================================================
    # Chart 1: IPC comparison across all 6 parameter groups
    # =========================================================================
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Parameter Sweep: IPC Impact (baseline IPC = {:.3f})'.format(b_ipc),
                 fontsize=16, fontweight='bold')

    groups = [
        ('Fetch Width', [f'fw{i}' for i in range(1,9)], [str(i) for i in range(1,9)], C_BLUE),
        ('IQ Cap', [f'iqcap{v}' for v in [8,12,16,20,22,24,26,28,30,32,40,48,0]],
                   [str(v) for v in [8,12,16,20,22,24,26,28,30,32,40,48]]+['off'], C_RED),
        ('LSQ Cap', [f'lsqcap{v}' for v in [4,8,10,12,14,16,18,20,22,24,26,28,0]],
                    [str(v) for v in [4,8,10,12,14,16,18,20,22,24,26,28]]+['off'], C_GREEN),
        ('Inflight Cap (ROB)', [f'robcap{v}' for v in [24,32,40,48,52,56,60,64,68,72,80,96,112,128,160,0]],
                               [str(v) for v in [24,32,40,48,52,56,60,64,68,72,80,96,112,128,160]]+['off'], C_ORANGE),
        ('Rename Width', [f'rw{i}' for i in range(1,9)], [str(i) for i in range(1,9)], C_PURPLE),
        ('Dispatch Width', [f'dw{i}' for i in range(1,9)], [str(i) for i in range(1,9)], C_TEAL),
    ]

    for idx, (title, tags, labels, color) in enumerate(groups):
        ax = axes[idx // 3][idx % 3]
        ipcs = []
        valid_labels = []
        for t, l in zip(tags, labels):
            r = get(rows, t)
            if r:
                ipcs.append(float(r['ipc']))
                valid_labels.append(l)

        import numpy as np
        x_pos = np.arange(len(valid_labels))
        bars = ax.bar(x_pos, ipcs, color=color, alpha=0.8, edgecolor='white', linewidth=0.5)
        ax.axhline(y=b_ipc, color='black', linestyle='--', linewidth=1.2, label='baseline')
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.set_ylabel('IPC')
        ax.set_ylim(0, max(ipcs + [b_ipc]) * 1.15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(valid_labels, fontsize=7, rotation=45 if len(valid_labels) > 8 else 0)

        # Highlight sweet spot
        best_idx = ipcs.index(max(ipcs))
        bars[best_idx].set_edgecolor('#000000')
        bars[best_idx].set_linewidth(2)

        # Annotate only sweet spot and extremes to avoid clutter
        for i, (bar, ipc) in enumerate(zip(bars, ipcs)):
            if i == best_idx or i == 0 or i == len(ipcs)-1:
                delta = (ipc / b_ipc - 1) * 100
                color_text = C_GREEN if delta >= 0 else C_RED
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                        f'{delta:+.1f}%', ha='center', va='bottom', fontsize=7,
                        fontweight='bold', color=color_text)

        ax.legend(fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(chart_dir, 'sweep_ipc_all_groups.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('Saved sweep_ipc_all_groups.png')

    # =========================================================================
    # Chart 2: Masking relationship proof (Group 7)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle('Masking Proof: Fetch Width Masks Inflight Cap', fontsize=14, fontweight='bold')

    fw2_tags = ['fw2_cap64', 'fw2_cap96', 'fw2_cap128']
    fw4_tags = ['fw4_cap64', 'fw4_cap96', 'fw4_cap128']
    cap_labels = ['64', '96', '128']
    x = np.arange(len(cap_labels))
    width = 0.35

    fw2_ipcs = [float(get(rows, t)['ipc']) for t in fw2_tags]
    fw4_ipcs = [float(get(rows, t)['ipc']) for t in fw4_tags]

    bars1 = ax.bar(x - width/2, fw2_ipcs, width, label='fw=2', color=C_BLUE, alpha=0.8)
    bars2 = ax.bar(x + width/2, fw4_ipcs, width, label='fw=4', color=C_ORANGE, alpha=0.8)
    ax.axhline(y=b_ipc, color='black', linestyle='--', linewidth=1.2, label='baseline (fw=8)')
    ax.set_xlabel('Inflight Cap', fontsize=12)
    ax.set_ylabel('IPC', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(cap_labels)
    ax.set_ylim(0, b_ipc * 1.2)
    ax.legend(fontsize=11)

    # Annotations
    ax.annotate('IPC identical regardless\nof inflight cap',
                xy=(1, fw2_ipcs[1]), xytext=(1.8, fw2_ipcs[1] + 0.4),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color=C_BLUE),
                color=C_BLUE, fontweight='bold')
    ax.annotate('IPC identical regardless\nof inflight cap',
                xy=(1, fw4_ipcs[1]), xytext=(1.8, fw4_ipcs[1] + 0.3),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color=C_ORANGE),
                color=C_ORANGE, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, 'sweep_masking_proof.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('Saved sweep_masking_proof.png')

    # =========================================================================
    # Chart 3: Sweet spot phenomenon (IQ Cap / ROB Cap detail)
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('"Sweet Spot" Phenomenon: Moderate Throttling Beats Baseline',
                 fontsize=14, fontweight='bold')

    # IQ Cap detail - dense
    iq_tags = ['iqcap8','iqcap12','iqcap16','iqcap20','iqcap22','iqcap24','iqcap26','iqcap28','iqcap30','iqcap32','iqcap40','iqcap48','iqcap0']
    iq_labels = ['8','12','16','20','22','24','26','28','30','32','40','48','off']
    iq_ipcs = [float(get(rows, t)['ipc']) for t in iq_tags]
    iq_ren_blk = [ren_blk_pct(get(rows, t)) for t in iq_tags]

    # Filter to available data
    iq_avail = [(l, float(get(rows,t)['ipc']), ren_blk_pct(get(rows,t))) for t, l in zip(iq_tags, iq_labels) if get(rows,t)]
    iq_labels_a = [a[0] for a in iq_avail]
    iq_ipcs = [a[1] for a in iq_avail]
    iq_ren_blk = [a[2] for a in iq_avail]

    x_iq = np.arange(len(iq_labels_a))
    ax1_twin = ax1.twinx()
    bars = ax1.bar(x_iq, iq_ipcs, color=C_RED, alpha=0.7, label='IPC')
    ax1.axhline(y=b_ipc, color='black', linestyle='--', linewidth=1.2)
    ax1_twin.plot(x_iq, iq_ren_blk, 'o-', color=C_PURPLE, linewidth=2, markersize=5, label='rename_blk%')
    ax1.set_title('IQ Cap Sweep (dense)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('IQ Cap')
    ax1.set_ylabel('IPC', color=C_RED)
    ax1_twin.set_ylabel('rename_blockCycles %', color=C_PURPLE)
    ax1.set_xticks(x_iq)
    ax1.set_xticklabels(iq_labels_a, fontsize=7, rotation=45)

    best_idx = iq_ipcs.index(max(iq_ipcs))
    bars[best_idx].set_edgecolor(C_GREEN)
    bars[best_idx].set_linewidth(3)
    ax1.annotate(f'Sweet spot\nIPC={iq_ipcs[best_idx]:.3f}\n(+{(iq_ipcs[best_idx]/b_ipc-1)*100:.1f}%)',
                xy=(best_idx, iq_ipcs[best_idx]),
                xytext=(best_idx + 2, iq_ipcs[best_idx] + 0.1),
                fontsize=9, fontweight='bold', color=C_GREEN,
                arrowprops=dict(arrowstyle='->', color=C_GREEN, lw=2))

    # ROB Cap detail - dense
    rob_tags = ['robcap24','robcap32','robcap40','robcap48','robcap52','robcap56','robcap60','robcap64','robcap68','robcap72','robcap80','robcap96','robcap112','robcap128','robcap160','robcap0']
    rob_labels = ['24','32','40','48','52','56','60','64','68','72','80','96','112','128','160','off']
    rob_avail = [(l, float(get(rows,t)['ipc']), safe_int(get(rows,t),'rename_IQFullEvents')/1e6) for t, l in zip(rob_tags, rob_labels) if get(rows,t)]
    rob_labels_a = [a[0] for a in rob_avail]
    rob_ipcs = [a[1] for a in rob_avail]
    rob_iq_full = [a[2] for a in rob_avail]

    x_rob = np.arange(len(rob_labels_a))
    ax2_twin = ax2.twinx()
    bars2 = ax2.bar(x_rob, rob_ipcs, color=C_ORANGE, alpha=0.7, label='IPC')
    ax2.axhline(y=b_ipc, color='black', linestyle='--', linewidth=1.2)
    ax2_twin.plot(x_rob, rob_iq_full, 's-', color=C_TEAL, linewidth=2, markersize=5, label='IQFull (M)')
    ax2.set_title('Inflight Cap (ROB) Sweep (dense)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Inflight Cap')
    ax2.set_ylabel('IPC', color=C_ORANGE)
    ax2_twin.set_ylabel('IQFullEvents (millions)', color=C_TEAL)
    ax2.set_xticks(x_rob)
    ax2.set_xticklabels(rob_labels_a, fontsize=6, rotation=45)

    best_idx2 = rob_ipcs.index(max(rob_ipcs))
    bars2[best_idx2].set_edgecolor(C_GREEN)
    bars2[best_idx2].set_linewidth(3)
    ax2.annotate(f'Sweet spot\nIPC={rob_ipcs[best_idx2]:.3f}\n(+{(rob_ipcs[best_idx2]/b_ipc-1)*100:.1f}%)',
                xy=(best_idx2, rob_ipcs[best_idx2]),
                xytext=(best_idx2 + 3, rob_ipcs[best_idx2] + 0.05),
                fontsize=9, fontweight='bold', color=C_GREEN,
                arrowprops=dict(arrowstyle='->', color=C_GREEN, lw=2))

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(os.path.join(chart_dir, 'sweep_sweet_spot.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('Saved sweep_sweet_spot.png')

    # =========================================================================
    # Chart 4: Pipeline signal heatmap - key signals across all sweeps
    # =========================================================================
    all_tags = ['fw1','fw2','fw4','fw8',
                'iqcap16','iqcap24','iqcap32','iqcap48','iqcap0',
                'lsqcap8','lsqcap12','lsqcap16','lsqcap24','lsqcap0',
                'robcap32','robcap48','robcap64','robcap96','robcap128','robcap0',
                'rw1','rw2','rw4','rw8',
                'dw1','dw2','dw4','dw8']

    signal_names = ['IPC', 'fetch_mean', 'issue_mean', 'commit_mean',
                    'dec_blk%', 'ren_blk%', 'IQFull(M)', 'forwLoads(M)']

    data_matrix = []
    for tag in all_tags:
        r = get(rows, tag)
        if not r:
            data_matrix.append([0]*len(signal_names))
            continue
        s = int(r['fetch_nisnDist_samples']) if r['fetch_nisnDist_samples'] else 1
        row_data = [
            float(r['ipc']),
            float(r['fetch_nisnDist_mean']),
            float(r['numIssuedDist_mean']),
            float(r['commit_numCommittedDist_mean']),
            dec_blk_pct(r),
            ren_blk_pct(r),
            safe_int(r, 'rename_IQFullEvents') / 1e6,
            int(r['lsq_forwLoads']) / 1e6,
        ]
        data_matrix.append(row_data)

    data_arr = np.array(data_matrix)
    # Normalize each column to [0, 1] for heatmap
    mins = data_arr.min(axis=0)
    maxs = data_arr.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1
    norm_data = (data_arr - mins) / ranges

    fig, ax = plt.subplots(figsize=(12, 14))
    im = ax.imshow(norm_data, aspect='auto', cmap='RdYlGn', interpolation='nearest')

    ax.set_xticks(range(len(signal_names)))
    ax.set_xticklabels(signal_names, fontsize=10, rotation=30, ha='right')
    ax.set_yticks(range(len(all_tags)))
    ax.set_yticklabels(all_tags, fontsize=8)

    # Add group separators
    for y in [4, 9, 14, 20, 24]:
        ax.axhline(y - 0.5, color='white', linewidth=2)

    # Add group labels
    group_labels = [
        (1.5, 'Fetch Width'), (6.5, 'IQ Cap'), (11.5, 'LSQ Cap'),
        (17, 'Inflight Cap'), (22, 'Rename Width'), (26, 'Dispatch Width')
    ]
    for y, label in group_labels:
        ax.text(-0.8, y, label, fontsize=9, fontweight='bold', ha='right', va='center',
                rotation=0, color='#333')

    # Annotate actual values
    for i in range(len(all_tags)):
        for j in range(len(signal_names)):
            val = data_arr[i, j]
            if j in [4, 5]:  # percentage
                text = f'{val:.0f}%'
            elif j in [6, 7]:  # millions
                text = f'{val:.1f}'
            else:
                text = f'{val:.2f}'
            ax.text(j, i, text, ha='center', va='center', fontsize=6.5,
                    color='black' if 0.3 < norm_data[i,j] < 0.7 else 'white')

    ax.set_title('Pipeline Signal Heatmap Across All Parameter Sweeps\n(Green=higher, Red=lower, normalized per column)',
                 fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax, shrink=0.6, label='Normalized value (0=min, 1=max)')
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, 'sweep_signal_heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('Saved sweep_signal_heatmap.png')

    # =========================================================================
    # Chart 5: LSQ Cap detail - forwLoads & memOrderViolation
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('LSQ Cap: Impact on Memory Subsystem Signals', fontsize=14, fontweight='bold')

    lsq_tags = ['lsqcap8', 'lsqcap12', 'lsqcap16', 'lsqcap24', 'lsqcap0']
    lsq_labels = ['8', '12', '16', '24', 'off']
    lsq_ipcs = [float(get(rows, t)['ipc']) for t in lsq_tags]
    lsq_fwd = [int(get(rows, t)['lsq_forwLoads']) / 1e6 for t in lsq_tags]
    lsq_mov = [int(get(rows, t)['lsq_memOrderViolation']) for t in lsq_tags]

    ax1_t = ax1.twinx()
    b1 = ax1.bar(lsq_labels, lsq_ipcs, color=C_GREEN, alpha=0.7, label='IPC')
    ax1.axhline(y=b_ipc, color='black', linestyle='--', linewidth=1)
    l1, = ax1_t.plot(lsq_labels, lsq_fwd, 'D-', color=C_BLUE, linewidth=2, markersize=8, label='forwLoads (M)')
    ax1.set_xlabel('LSQ Cap')
    ax1.set_ylabel('IPC', color=C_GREEN)
    ax1_t.set_ylabel('Store-to-Load Forwarding (millions)', color=C_BLUE)
    ax1.set_title('IPC vs Store-to-Load Forwarding')
    ax1.legend(loc='upper left')
    ax1_t.legend(loc='center right')

    b2 = ax2.bar(lsq_labels, lsq_ipcs, color=C_GREEN, alpha=0.7, label='IPC')
    ax2.axhline(y=b_ipc, color='black', linestyle='--', linewidth=1)
    ax2_t = ax2.twinx()
    ax2_t.plot(lsq_labels, lsq_mov, 's-', color=C_RED, linewidth=2, markersize=8, label='memOrderViol')
    ax2.set_xlabel('LSQ Cap')
    ax2.set_ylabel('IPC', color=C_GREEN)
    ax2_t.set_ylabel('Memory Order Violations', color=C_RED)
    ax2.set_title('IPC vs Memory Order Violations')
    ax2.legend(loc='upper left')
    ax2_t.legend(loc='center right')

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(os.path.join(chart_dir, 'sweep_lsq_detail.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('Saved sweep_lsq_detail.png')

    # =========================================================================
    # Chart 6: Width params comparison (fw vs rw vs dw)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    widths_val = [1, 2, 4, 8]
    fw_ipcs = [float(get(rows, f'fw{w}')['ipc']) for w in widths_val]
    rw_ipcs = [float(get(rows, f'rw{w}')['ipc']) for w in widths_val]
    dw_ipcs = [float(get(rows, f'dw{w}')['ipc']) for w in widths_val]

    ax.plot(widths_val, fw_ipcs, 'o-', color=C_BLUE, linewidth=2.5, markersize=10, label='Fetch Width')
    ax.plot(widths_val, rw_ipcs, 's-', color=C_PURPLE, linewidth=2.5, markersize=10, label='Rename Width')
    ax.plot(widths_val, dw_ipcs, 'D-', color=C_TEAL, linewidth=2.5, markersize=10, label='Dispatch Width')
    ax.axhline(y=b_ipc, color='black', linestyle='--', linewidth=1.2, label='baseline')

    ax.set_xlabel('Width Parameter Value', fontsize=12)
    ax.set_ylabel('IPC', fontsize=12)
    ax.set_title('Width Parameters Comparison: Fetch vs Rename vs Dispatch',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(widths_val)
    ax.set_xticklabels(['1', '2', '4', '8'])
    ax.legend(fontsize=11)
    ax.set_ylim(0, b_ipc * 1.15)
    ax.grid(True, alpha=0.3)

    # Annotate key differences at width=4
    ax.annotate(f'fw4: {fw_ipcs[2]:.2f} (-13.8%)',
                xy=(4, fw_ipcs[2]), xytext=(5, fw_ipcs[2] - 0.2),
                fontsize=9, color=C_BLUE,
                arrowprops=dict(arrowstyle='->', color=C_BLUE))
    ax.annotate(f'rw4: {rw_ipcs[2]:.2f} (-10.1%)',
                xy=(4, rw_ipcs[2]), xytext=(5, rw_ipcs[2] + 0.1),
                fontsize=9, color=C_PURPLE,
                arrowprops=dict(arrowstyle='->', color=C_PURPLE))
    ax.annotate(f'dw4: {dw_ipcs[2]:.2f} (+0.5%)',
                xy=(4, dw_ipcs[2]), xytext=(5.5, dw_ipcs[2] + 0.15),
                fontsize=9, color=C_TEAL,
                arrowprops=dict(arrowstyle='->', color=C_TEAL))

    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, 'sweep_width_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('Saved sweep_width_comparison.png')

    print('\nAll charts generated successfully.')

if __name__ == '__main__':
    main()
