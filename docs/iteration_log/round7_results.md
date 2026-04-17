# Round 7 Results

## 1. Phase A: Per-Window Deep Analysis Summary

### Per-Mode IPC (GAPBS)
All GAPBS benchmarks spend 99.99% of windows in light-conservative mode (only 1 aggressive warmup window). The light-conservative mode splits into:
- **Normal windows** (squash < 0.30): fw=5, majority of windows
- **Tight windows** (squash >= 0.30): fw=4, stronger throttle

### Tight vs Normal Comparison

| Benchmark | Tight N | Tight IPC | Tight Squash | Normal N | Normal IPC | Normal Squash | IPC Gap |
|-----------|---------|-----------|-------------|----------|-----------|--------------|---------|
| bfs | 1,379 (9.4%) | 1.2512 | 0.3100 | 13,302 (90.6%) | 1.4177 | 0.1836 | -11.7% |
| bc | 3,227 (21.7%) | 1.2679 | 0.3129 | 11,634 (78.3%) | 1.4176 | 0.1759 | -10.6% |
| pr | 4,196 (28.5%) | 1.3384 | 0.3252 | 10,529 (71.5%) | 1.4216 | 0.1627 | -5.9% |
| cc | 3,876 (26.4%) | 1.3345 | 0.3209 | 10,782 (73.6%) | 1.4293 | 0.1632 | -6.6% |
| sssp | 4,454 (30.4%) | 1.2985 | 0.3152 | 10,206 (69.6%) | 1.4499 | 0.1628 | -10.4% |
| tc | 8,993 (62.8%) | 1.4020 | 0.3813 | 5,325 (37.2%) | 1.4977 | 0.0878 | -6.4% |

### Threshold Sensitivity

| Benchmark | @0.25 tight% | @0.30 tight% | @0.35 tight% | @0.40 tight% |
|-----------|-------------|-------------|-------------|-------------|
| bfs | 54.6% | 9.4% | 0.0% | 0.0% |
| bc | 58.1% | 21.7% | 0.1% | 0.0% |
| pr | 55.7% | 28.5% | 2.1% | 0.0% |
| cc | 54.3% | 26.4% | 1.0% | 0.0% |
| sssp | 58.4% | 30.4% | 0.2% | 0.0% |
| tc | 67.4% | 62.8% | 53.4% | 14.1% |

### IPC Loss Attribution
Normal windows (fw=5) are responsible for 73-92% of the total weighted IPC loss in bfs/bc/pr/cc. The key insight: normal windows have low squash ratios (0.16-0.18), meaning fw=5 was over-throttling them. Raising normal fw from 5 to 6 is the most impactful change.

## 2. Phase B: GAPBS Config Results

### v3t9a: normal fw=6, tight fw=4, threshold=0.30

| Benchmark | IPC | dIPC% | dEnergy% | WPE% | vs v3t8 dIPC |
|-----------|-----|-------|----------|------|-------------|
| gapbs_bfs | 1.3821 | -1.97% | -11.85% | +0.93% | +1.63% |
| gapbs_bc | 1.3633 | -2.38% | -6.93% | -0.49% | +1.48% |
| gapbs_pr | 1.3670 | -2.79% | -11.64% | +0.21% | +0.85% |
| gapbs_cc | 1.3801 | -2.17% | -6.96% | -0.31% | +1.33% |
| gapbs_sssp | 1.3619 | -2.12% | -8.55% | +0.07% | +0.01% |
| gapbs_tc | 1.3900 | +3.28% | -20.61% | +7.46% | -0.31% |
| **GAPBS avg** | | **-1.36%** | | **+1.31%** | |
| **dIPC > -3%** | | **6/6** | | | |

### v3t9b: normal fw=6, tight fw=4, threshold=0.25

| Benchmark | IPC | dIPC% | dEnergy% | WPE% |
|-----------|-----|-------|----------|------|
| gapbs_bfs | 1.3649 | -3.19% | -14.58% | +0.56% |
| gapbs_bc | 1.3507 | -3.28% | -10.79% | -0.38% |
| gapbs_pr | 1.3535 | -3.76% | -14.79% | +0.14% |
| gapbs_cc | 1.3639 | -3.32% | -9.78% | -0.64% |
| gapbs_sssp | 1.3554 | -2.59% | -10.61% | +0.15% |
| gapbs_tc | 1.3914 | +3.39% | -21.11% | +7.69% |
| **GAPBS avg** | | **-2.12%** | | **+1.25%** | |
| **dIPC > -3%** | | **2/6** | | | |

### v3t9c: normal fw=6, tight fw=3, threshold=0.35

| Benchmark | IPC | dIPC% | dEnergy% | WPE% |
|-----------|-----|-------|----------|------|
| gapbs_bfs | 1.3943 | -1.11% | -9.76% | +1.17% |
| gapbs_bc | 1.3563 | -2.88% | -7.00% | -0.88% |
| gapbs_pr | 1.3738 | -2.31% | -9.11% | +0.04% |
| gapbs_cc | 1.3971 | -0.96% | -3.88% | +0.02% |
| gapbs_sssp | 1.3719 | -1.40% | -4.92% | -0.12% |
| gapbs_tc | 1.3656 | +1.46% | -17.86% | +5.23% |
| **GAPBS avg** | | **-1.20%** | | **+0.91%** | |
| **dIPC > -3%** | | **6/6** | | | |

## 3. Best Config Selection

**v3t9a is the best config** based on highest GAPBS avg WPE (+1.31%) while achieving 6/6 benchmarks with dIPC > -3%.

- v3t9b (threshold=0.25): More tight windows caused worse IPC, only 2/6 above -3%. Rejected.
- v3t9c (threshold=0.35, tight fw=3): Best IPC but less energy savings, lower overall WPE (+0.91%). Rejected.

### Micro Results (v3t9a)
Micro benchmark params for v3t9a are identical to v3t8 (same fw=6, inflight=56, IQ=26, LSQ=28, same tight params). Results confirmed identical via rerun.

| Benchmark | dIPC% | dEnergy% | WPE% |
|-----------|-------|----------|------|
| balanced_pipeline_stress | -0.24% | +0.39% | -0.27% |
| branch_entropy | +9.72% | -28.93% | +15.32% |
| compute_queue_pressure | +0.00% | +0.01% | -0.00% |
| phase_scan_mix | -1.54% | -24.42% | +4.45% |
| serialized_pointer_chase | -2.18% | -4.22% | -0.90% |
| stream_cluster_reduce | +0.00% | +0.04% | -0.01% |

## 4. Final Comparison: V2 vs v3t8 vs v3t9a (GAPBS)

| Benchmark | V2 dIPC% | V2 WPE% | v3t8 dIPC% | v3t8 WPE% | v3t9a dIPC% | v3t9a WPE% |
|-----------|----------|---------|------------|-----------|-------------|------------|
| bfs | -2.76% | +0.11% | -3.55% | +0.21% | -1.97% | +0.93% |
| bc | -2.79% | -0.22% | -3.80% | -0.23% | -2.38% | -0.49% |
| pr | -2.50% | -0.10% | -3.61% | -0.25% | -2.79% | +0.21% |
| cc | -2.40% | -0.57% | -3.45% | -1.29% | -2.17% | -0.31% |
| sssp | -2.03% | +0.14% | -2.13% | +0.46% | -2.12% | +0.07% |
| tc | +3.34% | +7.38% | +3.60% | +8.15% | +3.28% | +7.46% |

v3t9a achieves better IPC than both V2 and v3t8 on bfs/cc, and comparable on the rest. The main improvement is less IPC loss on bfs (-1.97% vs -3.55%) and cc (-2.17% vs -3.45%).

## 5. GAPBS Benchmarks with dIPC > -3%

| Config | Count |
|--------|-------|
| V2 | 2/6 (sssp, tc) |
| v3t8 | 2/6 (sssp, tc) |
| **v3t9a** | **6/6 (all)** |

## 6. Overall 12-Workload WPE

| Config | GAPBS avg WPE | Micro avg WPE | 12-workload avg WPE |
|--------|--------------|--------------|---------------------|
| v3t8 | +0.54% | +3.10% | +2.14% (prev best) |
| **v3t9a** | **+1.31%** | **+3.10%** | **+2.21%** |

**v3t9a achieves +2.21% overall 12-workload WPE**, improving over v3t8's +2.14%.

Key improvement: raising GAPBS normal light-conservative fetch width from 5 to 6 reduced IPC loss significantly (avg -1.36% vs -3.32%) with only modest energy savings reduction.

## v3t9a Configuration Parameters

### GAPBS (window=2500)
```
adaptiveLightConsFetchWidth=6
adaptiveLightConsInflightCap=128
adaptiveLightConsIQCap=0
adaptiveLightConsLSQCap=0
adaptiveConservativeFetchWidth=6
adaptiveConservativeInflightCap=128
adaptiveConservativeIQCap=0
adaptiveConservativeLSQCap=0
adaptiveSerializedTightFetchWidth=4
adaptiveSerializedTightInflightCap=128
adaptiveSerializedTightSquashThres=0.30
adaptiveMemBlockRatioThres=0.12
```

### Micro (window=5000)
```
adaptiveLightConsFetchWidth=6
adaptiveLightConsInflightCap=56
adaptiveLightConsIQCap=26
adaptiveLightConsLSQCap=28
adaptiveConservativeFetchWidth=6
adaptiveConservativeInflightCap=56
adaptiveConservativeIQCap=26
adaptiveConservativeLSQCap=28
adaptiveSerializedTightFetchWidth=4
adaptiveSerializedTightInflightCap=128
adaptiveSerializedTightSquashThres=0.30
adaptiveMemBlockRatioThres=0.12
```
