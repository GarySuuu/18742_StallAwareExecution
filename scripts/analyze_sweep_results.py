#!/usr/bin/env python3
"""Analyze parameter sweep results with low-level architectural signals."""

import csv
import os

def main():
    gem5_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(gem5_root, "results", "sweep_signals.csv")

    with open(csv_path) as f:
        rows = list(csv.DictReader(f))

    baseline = [r for r in rows if r['experiment'] == 'baseline'][0]
    b_ipc = float(baseline['ipc'])

    def get(tag):
        matches = [x for x in rows if x['experiment'] == f'sweep_{tag}']
        return matches[0] if matches else None

    def pct(val, total):
        return val / total * 100.0 if total else 0.0

    def ren_blk_pct(r):
        t = int(r['rename_idleCycles']) + int(r['rename_blockCycles']) + int(r['rename_runCycles'])
        return pct(int(r['rename_blockCycles']), t)

    def dec_blk_pct(r):
        t = int(r['decode_idleCycles']) + int(r['decode_blockedCycles']) + int(r['decode_runCycles'])
        return pct(int(r['decode_blockedCycles']), t)

    def dipc(r):
        return (float(r['ipc']) / b_ipc - 1) * 100.0

    def safe_int(r, key):
        v = r.get(key, '') or '0'
        return int(v)

    sep = '=' * 110

    # Group 1: Fetch Width
    print(sep)
    print('GROUP 1: Fetch Width (inflight cap=0, all other caps=0)')
    print(sep)
    hdr = f"{'Config':<8} {'IPC':>7} {'dIPC':>7} {'fetch_mean':>10} {'fetch_0%':>8} {'fetch_8%':>8} {'dec_blk%':>8} {'ren_blk%':>8} {'IQFull':>10} {'LQFull':>10} {'SQFull':>10}"
    print(hdr)
    print('-' * len(hdr))
    for tag in ['fw1', 'fw2', 'fw4', 'fw8']:
        r = get(tag)
        if not r: continue
        s = int(r['fetch_nisnDist_samples'])
        f0 = pct(int(r['fetch_nisnDist_0']), s)
        f8 = pct(int(r['fetch_nisnDist_8']), s)
        iq = safe_int(r, 'rename_IQFullEvents')
        lq = safe_int(r, 'rename_LQFullEvents')
        sq = safe_int(r, 'rename_SQFullEvents')
        print(f"{tag:<8} {float(r['ipc']):>7.3f} {dipc(r):>+6.1f}% {float(r['fetch_nisnDist_mean']):>10.2f} {f0:>7.1f}% {f8:>7.1f}% {dec_blk_pct(r):>7.1f}% {ren_blk_pct(r):>7.1f}% {iq:>10} {lq:>10} {sq:>10}")

    # Group 2: IQ Cap
    print()
    print(sep)
    print('GROUP 2: IQ Cap (inflight cap=0, fetch width=0, other caps=0)')
    print(sep)
    hdr = f"{'Config':<10} {'IPC':>7} {'dIPC':>7} {'issue_mean':>10} {'IQFull':>10} {'ren_blk%':>8} {'dec_blk%':>8} {'forwLoads':>10}"
    print(hdr)
    print('-' * len(hdr))
    for tag in ['iqcap16', 'iqcap24', 'iqcap32', 'iqcap48', 'iqcap0']:
        r = get(tag)
        if not r: continue
        iq = safe_int(r, 'rename_IQFullEvents')
        print(f"{tag:<10} {float(r['ipc']):>7.3f} {dipc(r):>+6.1f}% {float(r['numIssuedDist_mean']):>10.3f} {iq:>10} {ren_blk_pct(r):>7.1f}% {dec_blk_pct(r):>7.1f}% {r['lsq_forwLoads']:>10}")

    # Group 3: LSQ Cap
    print()
    print(sep)
    print('GROUP 3: LSQ Cap (inflight cap=0, fetch width=0, IQ cap=0)')
    print(sep)
    hdr = f"{'Config':<10} {'IPC':>7} {'dIPC':>7} {'LQFull':>10} {'SQFull':>10} {'forwLoads':>10} {'blkCache':>9} {'memOrdViol':>10}"
    print(hdr)
    print('-' * len(hdr))
    for tag in ['lsqcap8', 'lsqcap12', 'lsqcap16', 'lsqcap24', 'lsqcap0']:
        r = get(tag)
        if not r: continue
        lq = safe_int(r, 'rename_LQFullEvents')
        sq = safe_int(r, 'rename_SQFullEvents')
        print(f"{tag:<10} {float(r['ipc']):>7.3f} {dipc(r):>+6.1f}% {lq:>10} {sq:>10} {r['lsq_forwLoads']:>10} {r['lsq_blockedByCache']:>9} {r['lsq_memOrderViolation']:>10}")

    # Group 4: Inflight Cap / ROB
    print()
    print(sep)
    print('GROUP 4: Inflight Cap / ROB (fetch width=0, all other caps=0)')
    print(sep)
    hdr = f"{'Config':<10} {'IPC':>7} {'dIPC':>7} {'ROBFull':>10} {'IQFull':>10} {'ren_blk%':>8} {'dec_blk%':>8} {'rob_writes':>11}"
    print(hdr)
    print('-' * len(hdr))
    for tag in ['robcap32', 'robcap48', 'robcap64', 'robcap96', 'robcap128', 'robcap0']:
        r = get(tag)
        if not r: continue
        rob = safe_int(r, 'rename_ROBFullEvents')
        iq = safe_int(r, 'rename_IQFullEvents')
        print(f"{tag:<10} {float(r['ipc']):>7.3f} {dipc(r):>+6.1f}% {rob:>10} {iq:>10} {ren_blk_pct(r):>7.1f}% {dec_blk_pct(r):>7.1f}% {r['rob_writes']:>11}")

    # Group 5: Rename Width
    print()
    print(sep)
    print('GROUP 5: Rename Width (fetch width=0, inflight cap=0)')
    print(sep)
    hdr = f"{'Config':<8} {'IPC':>7} {'dIPC':>7} {'ren_run%':>8} {'ren_blk%':>8} {'ren_idle%':>9} {'renamedInsts':>13} {'dec_blk%':>8}"
    print(hdr)
    print('-' * len(hdr))
    for tag in ['rw1', 'rw2', 'rw4', 'rw8']:
        r = get(tag)
        if not r: continue
        t = int(r['rename_idleCycles']) + int(r['rename_blockCycles']) + int(r['rename_runCycles'])
        rr = pct(int(r['rename_runCycles']), t)
        rb = pct(int(r['rename_blockCycles']), t)
        ri = pct(int(r['rename_idleCycles']), t)
        print(f"{tag:<8} {float(r['ipc']):>7.3f} {dipc(r):>+6.1f}% {rr:>7.1f}% {rb:>7.1f}% {ri:>8.1f}% {r['rename_renamedInsts']:>13} {dec_blk_pct(r):>7.1f}%")

    # Group 6: Dispatch Width
    print()
    print(sep)
    print('GROUP 6: Dispatch Width (fetch width=0, inflight cap=0)')
    print(sep)
    hdr = f"{'Config':<8} {'IPC':>7} {'dIPC':>7} {'issue_mean':>10} {'commit_mean':>11} {'dec_blk%':>8} {'ren_blk%':>8}"
    print(hdr)
    print('-' * len(hdr))
    for tag in ['dw1', 'dw2', 'dw4', 'dw8']:
        r = get(tag)
        if not r: continue
        print(f"{tag:<8} {float(r['ipc']):>7.3f} {dipc(r):>+6.1f}% {float(r['numIssuedDist_mean']):>10.3f} {float(r['commit_numCommittedDist_mean']):>11.3f} {dec_blk_pct(r):>7.1f}% {ren_blk_pct(r):>7.1f}%")

    # Group 7: Combined
    print()
    print(sep)
    print('GROUP 7: Combined Fetch Width + Inflight Cap')
    print(sep)
    hdr = f"{'Config':<15} {'IPC':>7} {'dIPC':>7} {'fetch_mean':>10} {'ren_blk%':>8} {'dec_blk%':>8}"
    print(hdr)
    print('-' * len(hdr))
    for tag in ['fw2_cap64', 'fw2_cap96', 'fw2_cap128', 'fw4_cap64', 'fw4_cap96', 'fw4_cap128']:
        r = get(tag)
        if not r: continue
        print(f"{tag:<15} {float(r['ipc']):>7.3f} {dipc(r):>+6.1f}% {float(r['fetch_nisnDist_mean']):>10.2f} {ren_blk_pct(r):>7.1f}% {dec_blk_pct(r):>7.1f}%")

    # Baseline for reference
    print()
    print(sep)
    print(f"BASELINE REFERENCE: IPC = {b_ipc:.3f}, simTicks = {baseline['simTicks']}")
    print(sep)

if __name__ == '__main__':
    main()
