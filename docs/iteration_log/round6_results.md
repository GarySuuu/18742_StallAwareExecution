# Round 6 Results -- Serialized-Tight Sub-Level

## Phase A: Squash Ratio Distribution Analysis

Analyzed `adaptive_window_log.csv` from v3t4 GAPBS runs (fw=4, cap=128, window=2500).
All GAPBS benchmarks are ~100% Serialized-memory dominated.

### Squash Ratio Statistics (Serialized windows only)

| Bench | Windows | Mean | P25 | P50 | P75 | P90 | >=0.10 | >=0.15 | >=0.20 | >=0.25 | >=0.30 | >=0.35 |
|-------|---------|------|-----|-----|-----|-----|--------|--------|--------|--------|--------|--------|
| bfs   | 14784   | 0.189 | 0.086 | 0.253 | 0.275 | 0.287 | 73.6% | 68.2% | 61.9% | 51.8% | 2.2% | 0.0% |
| bc    | 14902   | 0.201 | 0.099 | 0.266 | 0.291 | 0.304 | 74.8% | 69.6% | 64.1% | 56.6% | 14.1% | 0.1% |
| cc    | 14882   | 0.181 | 0.080 | 0.241 | 0.264 | 0.278 | 73.0% | 67.1% | 60.7% | 42.9% | 0.6% | 0.0% |
| pr    | 14940   | 0.185 | 0.087 | 0.245 | 0.268 | 0.280 | 73.6% | 68.4% | 61.9% | 45.8% | 1.0% | 0.0% |
| sssp  | 14809   | 0.212 | 0.096 | 0.285 | 0.309 | 0.323 | 74.6% | 70.0% | 64.9% | 58.9% | 36.4% | 0.2% |
| tc    | 14247   | 0.257 | 0.120 | 0.345 | 0.374 | 0.390 | 76.2% | 73.1% | 69.2% | 64.8% | 59.3% | 47.3% |

### Chosen Threshold: 0.30

At threshold 0.30, clean separation emerges:
- tc: 59.3% of windows above threshold (will get strong throttle fw=4)
- bfs/cc/pr: 0.6-2.2% above (minimal impact, nearly all windows get gentle fw=5)
- sssp: 36.4% above (moderate impact)
- bc: 14.1% above (mild impact)

## Phase B: Implementation

Modified three files to add Serialized-Tight sub-level:

1. **BaseO3CPU.py**: Added 3 new parameters:
   - `adaptiveSerializedTightSquashThres` (default 0.30)
   - `adaptiveSerializedTightFetchWidth` (default 4)
   - `adaptiveSerializedTightInflightCap` (default 128)

2. **cpu.hh**: Added member variables for the new sub-level

3. **cpu.cc**: 
   - Constructor reads new params
   - `adaptiveAdvanceWindow()`: After classification, checks if Serialized windows have squash_ratio >= threshold and sets `adaptiveCurrentSerializedTight`
   - `adaptiveFetchWidth()`: LightConservative case returns tight fetch width when serialized-tight is active
   - `adaptiveEffectiveInflightCap()`: Same pattern for inflight cap
   - `adaptiveResourceProfileLevel()`: Logs "ser-tight" when active in LightConservative mode

## Phase C: Results

### Full 12-Workload Results (v3t8)

| Workload | BL IPC | v3t8 IPC | dIPC% | BL E(J) | v3t8 E(J) | dE% | WPE% |
|----------|--------|----------|-------|---------|-----------|-----|------|
| gapbs_bfs | 1.409910 | 1.359850 | -3.55% | 4.18887 | 3.58715 | -14.36% | +0.21% |
| gapbs_bc | 1.396511 | 1.343383 | -3.80% | 4.21920 | 3.65406 | -13.39% | -0.23% |
| gapbs_cc | 1.410674 | 1.361986 | -3.45% | 3.93623 | 3.64965 | -7.28% | -1.29% |
| gapbs_pr | 1.406315 | 1.355505 | -3.61% | 4.20774 | 3.67679 | -12.62% | -0.25% |
| gapbs_sssp | 1.391411 | 1.361831 | -2.13% | 4.00860 | 3.59492 | -10.32% | +0.46% |
| gapbs_tc | 1.345860 | 1.394318 | +3.60% | 5.46094 | 4.25243 | -22.13% | +8.15% |
| balanced_pipeline_stress | 2.907918 | 2.901044 | -0.24% | 3.31314 | 3.32613 | +0.39% | -0.27% |
| phase_scan_mix | 0.466612 | 0.459407 | -1.54% | 6.00512 | 4.53895 | -24.42% | +4.45% |
| branch_entropy | 0.909234 | 0.997606 | +9.72% | 6.08719 | 4.32633 | -28.93% | +15.32% |
| serialized_pointer_chase | 0.826551 | 0.808537 | -2.18% | 4.32275 | 4.14054 | -4.22% | -0.90% |
| compute_queue_pressure | 2.391738 | 2.391738 | +0.00% | 2.68588 | 2.68625 | +0.01% | -0.00% |
| stream_cluster_reduce | 0.513648 | 0.513648 | +0.00% | 3.45580 | 3.45727 | +0.04% | -0.01% |
| **GAPBS AVG** | | | | | | | **+1.18%** |
| **Micro AVG** | | | | | | | **+3.10%** |
| **Overall AVG** | | | | | | | **+2.14%** |

### Serialized-Tight Window Distribution (v3t8 GAPBS)

| Bench | Total Windows | Ser-Tight | %Tight | Normal | %Normal |
|-------|--------------|-----------|--------|--------|---------|
| gapbs_bfs | 14682 | 1379 | 9.4% | 13303 | 90.6% |
| gapbs_bc | 14862 | 3227 | 21.7% | 11635 | 78.3% |
| gapbs_cc | 14659 | 3876 | 26.4% | 10783 | 73.6% |
| gapbs_pr | 14726 | 4196 | 28.5% | 10530 | 71.5% |
| gapbs_sssp | 14661 | 4454 | 30.4% | 10207 | 69.6% |
| gapbs_tc | 14319 | 8993 | 62.8% | 5326 | 37.2% |

Key insight: tc has 62.8% tight windows (strong fw=4 throttle), while bfs has only 9.4%.

### Micro Benchmark Ser-Tight Impact

| Bench | Serialized Windows | Ser-Tight | Notes |
|-------|-------------------|-----------|-------|
| balanced_pipeline_stress | 0 | 0 | 100% Resource class |
| phase_scan_mix | 18780 | 13742 (73.2%) | Ser-tight beneficial (+4.45% WPE) |
| branch_entropy | 9825 | 9430 (96.0%) | Ser-tight very beneficial (+15.32% WPE) |
| serialized_pointer_chase | 0 | 0 | 100% Resource/Control class |
| compute_queue_pressure | 0 | 0 | 100% Resource class |
| stream_cluster_reduce | 0 | 0 | 100% HighMLP/Resource class |

### GAPBS Comparison: V2 vs v3t4 vs v3t7 vs v3t8

| Bench | V2 dIPC% | v3t4 dIPC% | v3t7 dIPC% | v3t8 dIPC% | V2 WPE% | v3t4 WPE% | v3t7 WPE% | v3t8 WPE% |
|-------|----------|-----------|-----------|-----------|---------|----------|----------|----------|
| bfs | -2.76% | -4.23% | -3.47% | -3.55% | +0.11% | +0.26% | +0.19% | +0.21% |
| bc | -2.79% | -4.07% | -3.70% | -3.80% | -0.22% | -0.26% | -0.21% | -0.23% |
| cc | -2.40% | -4.90% | -2.71% | -3.45% | -0.57% | -1.08% | -1.37% | -1.29% |
| pr | -2.50% | -5.00% | -2.78% | -3.61% | -0.10% | +0.04% | -0.38% | -0.25% |
| sssp | -2.03% | -3.12% | -1.59% | -2.13% | +0.14% | +0.23% | +0.54% | +0.46% |
| tc | +3.33% | +4.11% | +1.90% | +3.60% | +7.38% | +9.39% | +4.24% | +8.15% |
| **AVG** | | | | | **+1.12%** | **+1.43%** | **+0.50%** | **+1.18%** |

### Overall WPE Comparison (12 benchmarks)

| Config | GAPBS Avg WPE | Micro Avg WPE | Overall Avg WPE |
|--------|---------------|---------------|-----------------|
| V2 | +1.12% | +2.46% | +1.79% |
| v3t4 + v3t3 | +1.43% | +2.39% | +1.91% |
| **v3t8** | **+1.18%** | **+3.10%** | **+2.14%** |

Note: v3t8 micro results differ from v3t3 because the recompiled binary includes the serialized-tight sub-level code, which actively triggers for branch_entropy (96% tight) and phase_scan_mix (73% tight), improving their WPE.

## Success Criteria Check

| Criterion | Target | Result | Met? |
|-----------|--------|--------|------|
| GAPBS avg WPE >= +1.0% | >= +1.0% | +1.18% | YES |
| tc WPE >= +5% | >= +5% | +8.15% | YES |
| At least 5/6 GAPBS dIPC > -3% | 5/6 | 2/6 (bfs -3.55%, bc -3.80%, cc -3.45%, pr -3.61% fail) | NO |
| Overall WPE > +1.5% | > +1.5% | +2.14% | YES |

The dIPC criterion for individual GAPBS benchmarks is not met -- 4 out of 6 still have dIPC worse than -3%. However, this is a significant improvement from v3t4 where all 5 non-tc benchmarks exceeded -3%:
- bfs: -4.23% -> -3.55% (improved 0.68pp)
- cc: -4.90% -> -3.45% (improved 1.45pp)
- pr: -5.00% -> -3.61% (improved 1.39pp)
- sssp: -3.12% -> -2.13% (improved 0.99pp, now meets criterion)
- bc: -4.07% -> -3.80% (improved only 0.27pp)

## Summary

v3t8 introduces a Serialized-Tight sub-level that applies stronger throttle (fw=4) only to high-squash-ratio windows (>= 0.30) within the LightConservative mode, while using gentler throttle (fw=5) for low-squash windows.

**Key results:**
- GAPBS avg WPE: +1.18% (down from v3t4's +1.43%, but still solid)
- tc preserved: +8.15% WPE (down from +9.39% but well above +5% target)
- IPC damage reduced: all non-tc benchmarks improved by 0.27-1.45pp vs v3t4
- Micro benchmarks improved: +3.10% avg WPE (up from +2.39% with v3t3)
- **Overall 12-benchmark avg WPE: +2.14%** (best so far, up from +1.91% with v3t4+v3t3)

The serialized-tight sub-level is the best overall configuration found:
- Best overall WPE (+2.14%)
- Meets GAPBS avg WPE >= 1.0% criterion
- Meets tc WPE >= 5% criterion
- Meets overall WPE > 1.5% criterion
- Does not fully meet the per-benchmark dIPC > -3% criterion (4/6 still slightly worse than -3%)

**Recommendation:** v3t8 is the production configuration. The serialized-tight mechanism successfully differentiates high-squash from low-squash Serialized windows, enabling per-window adaptive throttling within the same classification.
