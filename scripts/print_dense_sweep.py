#!/usr/bin/env python3
import csv, os

gem5_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(gem5_root, 'results', 'sweep_signals.csv')) as f:
    rows = list(csv.DictReader(f))

bl = [r for r in rows if r['experiment'] == 'baseline'][0]
b_ipc = float(bl['ipc'])

def safe_int(r, k):
    v = r.get(k, '') or '0'
    try: return int(v)
    except: return 0

def safe_float(r, k):
    v = r.get(k, '') or '0'
    try: return float(v)
    except: return 0.0

def ren_blk(r):
    t = safe_int(r,'rename_idleCycles') + safe_int(r,'rename_blockCycles') + safe_int(r,'rename_runCycles')
    return safe_int(r,'rename_blockCycles') / t * 100 if t else 0

def dec_blk(r):
    t = safe_int(r,'decode_idleCycles') + safe_int(r,'decode_blockedCycles') + safe_int(r,'decode_runCycles')
    return safe_int(r,'decode_blockedCycles') / t * 100 if t else 0

groups = [
    ('Fetch Width', [f'fw{i}' for i in range(1,9)], [str(i) for i in range(1,9)]),
    ('IQ Cap', [f'iqcap{v}' for v in [8,12,16,20,22,24,26,28,30,32,40,48,0]],
               [str(v) for v in [8,12,16,20,22,24,26,28,30,32,40,48]] + ['off']),
    ('LSQ Cap', [f'lsqcap{v}' for v in [4,8,10,12,14,16,18,20,22,24,26,28,0]],
                [str(v) for v in [4,8,10,12,14,16,18,20,22,24,26,28]] + ['off']),
    ('Inflight Cap', [f'robcap{v}' for v in [24,32,40,48,52,56,60,64,68,72,80,96,112,128,160,0]],
                     [str(v) for v in [24,32,40,48,52,56,60,64,68,72,80,96,112,128,160]] + ['off']),
    ('Rename Width', [f'rw{i}' for i in range(1,9)], [str(i) for i in range(1,9)]),
    ('Dispatch Width', [f'dw{i}' for i in range(1,9)], [str(i) for i in range(1,9)]),
]

for gname, tags, labels in groups:
    print(f'\n{"="*90}')
    print(f'  {gname}')
    print(f'{"="*90}')
    header = f'{"Label":<6} {"IPC":>7} {"dIPC%":>8} {"fetch_m":>7} {"issue_m":>7} {"comit_m":>7} {"dec_b%":>6} {"ren_b%":>6} {"IQFull":>8} {"LQFull":>8} {"fwdLds":>8} {"robWr":>8}'
    print(header)
    print('-' * len(header))

    best_ipc = -1
    best_label = ''

    for tag, label in zip(tags, labels):
        matches = [x for x in rows if x['experiment'] == f'sweep_{tag}']
        if not matches:
            print(f'{label:<6}   [missing]')
            continue
        r = matches[0]
        ipc = float(r['ipc'])
        d = (ipc / b_ipc - 1) * 100

        if ipc > best_ipc:
            best_ipc = ipc
            best_label = label

        marker = ' *' if ipc >= best_ipc else ''

        print(f'{label:<6} {ipc:>7.3f} {d:>+7.1f}% {safe_float(r,"fetch_nisnDist_mean"):>7.2f} '
              f'{safe_float(r,"numIssuedDist_mean"):>7.3f} {safe_float(r,"commit_numCommittedDist_mean"):>7.3f} '
              f'{dec_blk(r):>5.1f}% {ren_blk(r):>5.1f}% '
              f'{safe_int(r,"rename_IQFullEvents")/1e3:>7.0f}K '
              f'{safe_int(r,"rename_LQFullEvents")/1e3:>7.0f}K '
              f'{safe_int(r,"lsq_forwLoads")/1e6:>7.2f}M '
              f'{safe_int(r,"rob_writes")/1e6:>7.1f}M')

    print(f'\n  >> Sweet spot: {gname} = {best_label} (IPC = {best_ipc:.3f}, dIPC = {(best_ipc/b_ipc-1)*100:+.1f}%)')
