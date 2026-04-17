# Round 1 Results

## Configuration

- **V3ml_t2 mapping**: Resource/HighMLP -> Aggressive, Serialized -> LightConservative (fw=6, cap=56, iqcap=26, lsqcap=28), Control -> Conservative (fw=4, cap=48, iqcap=20, lsqcap=16)
- **mem_block_ratio**: 0.12 (override via --param)
- **Window size**: 5000 cycles
- **Instructions**: 50M per workload
- **EMA signal decoupling**: enabled (only update EMA in aggressive mode)

## Summary

| Metric | V2 | V3t2 |
|--------|-----|------|
| Avg WPE (all 12) | **+0.96%** | -0.39% |
| Avg WPE (micro) | +0.81% | **+2.28%** |
| Avg WPE (GAPBS) | **+1.12%** | -3.06% |
| Wins | **8** | 1 |
| Ties | 3 | 3 |

**Verdict: V2 wins overall. V3t2 fails the success criteria (avg WPE < V2, and 4 workloads breach -3% threshold).**

## Full Results Table

| Workload | BL IPC | V2 IPC | T2 IPC | BL E(J) | V2 E(J) | T2 E(J) | V2 WPE | T2 WPE | V2 dWPE% | T2 dWPE% | Winner |
|----------|--------|--------|--------|---------|---------|---------|--------|--------|----------|----------|--------|
| balanced_pipeline_stress | 2.9079 | 2.9079 | 2.8913 | 3.3131 | 3.3135 | 3.3379 | 1.0000 | 0.9939 | -0.00% | -0.61% | V2 |
| phase_scan_mix | 0.4666 | 0.4716 | 0.4561 | 6.0051 | 5.0188 | 4.7414 | 1.0454 | 1.0295 | +4.54% | +2.95% | V2 |
| branch_entropy | 0.9092 | 0.9116 | 0.9876 | 6.0872 | 5.4191 | 4.4731 | 1.0256 | 1.1363 | +2.56% | +13.63% | **V3t2** |
| serialized_pointer_chase | 0.8266 | 0.7803 | 0.7803 | 4.3228 | 3.8472 | 3.8472 | 0.9775 | 0.9775 | -2.25% | -2.25% | TIE |
| compute_queue_pressure | 2.3917 | 2.3917 | 2.3917 | 2.6859 | 2.6862 | 2.6862 | 1.0000 | 1.0000 | -0.00% | -0.00% | TIE |
| stream_cluster_reduce | 0.5136 | 0.5136 | 0.5136 | 3.4558 | 3.4573 | 3.4573 | 0.9999 | 0.9999 | -0.01% | -0.01% | TIE |
| gapbs_bfs | 1.4099 | 1.3710 | 1.2902 | 4.1889 | 3.7256 | 3.8133 | 1.0011 | 0.9492 | +0.11% | **-5.08%** | V2 |
| gapbs_bc | 1.3965 | 1.3575 | 1.3125 | 4.2192 | 3.8099 | 3.8348 | 0.9978 | 0.9699 | -0.22% | **-3.01%** | V2 |
| gapbs_pr | 1.4063 | 1.3711 | 1.2967 | 4.2077 | 3.8204 | 3.8277 | 0.9990 | 0.9550 | -0.10% | **-4.50%** | V2 |
| gapbs_cc | 1.4107 | 1.3768 | 1.3131 | 3.9362 | 3.6754 | 3.6918 | 0.9943 | 0.9565 | -0.57% | **-4.35%** | V2 |
| gapbs_sssp | 1.3914 | 1.3632 | 1.3686 | 4.0086 | 3.6681 | 3.8259 | 1.0014 | 0.9961 | +0.14% | -0.39% | V2 |
| gapbs_tc | 1.3459 | 1.3907 | 1.2755 | 5.4609 | 4.3625 | 4.6438 | 1.0738 | 0.9895 | +7.38% | -1.05% | V2 |

## Per-Workload Mode Distribution (V3ml_t2)

### Micro benchmarks

| Workload | Aggressive | Light-Conservative | Conservative | Total |
|----------|------------|-------------------|--------------|-------|
| balanced_pipeline_stress | 3457 (99.97%) | 0 (0%) | 1 (0.03%) | 3458 |
| phase_scan_mix | 2986 (13.63%) | 18936 (86.37%) | 0 (0%) | 21922 |
| branch_entropy | 196 (1.93%) | 9927 (97.88%) | 2 (0.02%) | 10125 |
| serialized_pointer_chase | 9168 (71.53%) | 0 (0%) | 3647 (28.47%) | 12815 |
| compute_queue_pressure | 4180 (100%) | 0 (0%) | 0 (0%) | 4180 |
| stream_cluster_reduce | 19468 (100%) | 0 (0%) | 0 (0%) | 19468 |

### GAPBS benchmarks

| Workload | Aggressive | Light-Conservative | Conservative | Total |
|----------|------------|-------------------|--------------|-------|
| gapbs_bfs | 4715 (60.94%) | 1 (0.01%) | 3022 (39.05%) | 7738 |
| gapbs_bc | 4626 (60.84%) | 1 (0.01%) | 2980 (39.20%) | 7607 |
| gapbs_pr | 4675 (60.74%) | 1 (0.01%) | 3022 (39.25%) | 7698 |
| gapbs_cc | 4660 (61.30%) | 1 (0.01%) | 2942 (38.69%) | 7603 |
| gapbs_sssp | 0 (0%) | 7294 (100%) | 0 (0%) | 7294 |
| gapbs_tc | 4318 (55.18%) | 1 (0.01%) | 3509 (44.84%) | 7828 |

### Classification Distribution (V3ml_t2)

| Workload | Resource | HighMLP | Serialized | Control |
|----------|----------|---------|------------|---------|
| balanced_pipeline_stress | 3457 (99.97%) | 0 | 0 | 1 (0.03%) |
| phase_scan_mix | 8 (0.04%) | 2978 (13.58%) | 18936 (86.38%) | 0 |
| branch_entropy | 196 (1.94%) | 0 | 9927 (98.04%) | 2 (0.02%) |
| serialized_pointer_chase | 9168 (71.53%) | 0 | 0 | 3647 (28.47%) |
| compute_queue_pressure | 4179 (99.98%) | 1 (0.02%) | 0 | 0 |
| stream_cluster_reduce | 11387 (58.49%) | 8081 (41.51%) | 0 | 0 |
| gapbs_bfs | 4711 (60.88%) | 4 (0.05%) | 1 (0.01%) | 3022 (39.06%) |
| gapbs_bc | 4619 (60.72%) | 7 (0.09%) | 1 (0.01%) | 2980 (39.18%) |
| gapbs_pr | 4673 (60.70%) | 2 (0.03%) | 1 (0.01%) | 3022 (39.26%) |
| gapbs_cc | 4657 (61.25%) | 3 (0.04%) | 1 (0.01%) | 2942 (38.70%) |
| gapbs_sssp | 0 | 0 | 7294 (100%) | 0 |
| gapbs_tc | 4316 (55.14%) | 2 (0.03%) | 1 (0.01%) | 3509 (44.83%) |

## Analysis

### Why V3t2 wins on branch_entropy (+13.63% vs +2.56%)
- 98% of windows classified as Serialized -> LightConservative (fw=6, cap=56)
- V2 uses fw=2, cap=96 for the same windows -- the fw=6 sweet spot provides much better IPC for this workload (0.988 vs 0.912)
- Energy savings are massive (4.47J vs 5.42J for V2, 6.09J baseline) due to the higher IPC needing fewer cycles

### Why V3t2 loses on GAPBS (-3% to -5% on bfs/bc/pr/cc)
- ~39-45% of GAPBS windows are classified as Control -> Conservative (fw=4, cap=48, iqcap=20, lsqcap=16)
- This is **far too aggressive** for GAPBS. The deep conservative parameters (especially iqcap=20 and lsqcap=16) severely limit IPC
- V3t2 GAPBS IPC ratios: 0.91-0.95 (vs V2: 0.97-0.98), meaning V3t2 loses 5-9% IPC on these benchmarks
- The energy savings from throttling (~9-10%) do not compensate for the large IPC loss under the 80/20 WPE weighting
- Exception: gapbs_sssp is 100% Serialized -> LightConservative, and only loses -0.39% (close to V2's +0.14%)

### Why V3t2 loses on phase_scan_mix (+2.95% vs +4.54%)
- 86% Serialized -> LightConservative, but IPC drops to 0.456 from baseline 0.467 (ratio 0.978)
- V2 gets IPC 0.472 (ratio 1.011) -- V2 actually gains IPC on this workload
- V3t2 gets better energy (4.74J vs 5.02J) but the IPC loss dominates under 80/20 weighting

### Why V3t2 loses on balanced_pipeline_stress (-0.61%)
- 99.97% aggressive (=baseline), but IPC drops slightly from 2.908 to 2.891
- This small IPC loss (0.6%) is likely due to the single conservative window or a classifier-induced transient

### Key anomaly: gapbs_sssp classified 100% Serialized
- Unlike other GAPBS benchmarks (which are ~60% Resource, ~40% Control), sssp is 100% Serialized
- This maps to LightConservative rather than deep Conservative, so it only loses -0.39%
- This strongly suggests the Control classification + deep Conservative mapping is the root cause of GAPBS regression

### Root cause summary
1. **Control -> deep Conservative (fw=4, cap=48, iqcap=20, lsqcap=16) is too aggressive for GAPBS**. The ~40% Control windows in GAPBS lose too much IPC.
2. **The Control classification threshold may be too sensitive**, catching windows that don't actually need deep throttling.
3. **V2 uses a milder fw=2 + cap=96 for all throttled windows**, which happens to be less damaging for GAPBS than the deep conservative parameters.

### Observations for next iteration
- V3t2 micro average (+2.28%) beats V2 micro average (+0.81%) -- the multi-level approach helps on micro benchmarks
- The branch_entropy result (+13.63%) shows the potential of class-specific profiles
- The GAPBS problem is specifically in the Control -> Conservative mapping being too deep
- Possible fixes: (a) soften Control params, (b) raise Control classification threshold, (c) map Control to LightConservative instead of Conservative
