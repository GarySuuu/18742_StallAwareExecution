# Round 2 Results

## Configuration

- **V3ml_t3 mapping**: Resource/HighMLP -> Aggressive, Serialized -> LightConservative, Control -> Conservative (but Conservative params overridden to match LightConservative)
- **Conservative override**: fw=6, cap=56, iqcap=26, lsqcap=28 (same as LightConservative sweet spot)
- **mem_block_ratio**: 0.12
- **Window size**: 5000 cycles
- **Instructions**: 50M per workload
- **Effect**: ALL throttled windows (both Serialized and Control) now use sweet spot parameters. Deep conservative is effectively eliminated.

## Summary

| Metric | V2 | V3t2 (Round 1) | V3t3 (Round 2) |
|--------|-----|----------------|----------------|
| Avg WPE (all 12) | +0.96% | -0.39% | **+1.34%** |
| Avg WPE (micro) | +0.81% | +2.28% | **+2.39%** |
| Avg WPE (GAPBS) | +1.12% | -3.06% | **+0.30%** |
| Wins vs V2 | -- | 1 | **5** |
| Ties | -- | 3 | 1 |
| Worst workload | -2.25% | -5.08% | **-0.87%** |
| Workloads < -3% | 0 | 4 | **0** |

## Success Criteria

| Criterion | Target | V3t3 Result | Status |
|-----------|--------|-------------|--------|
| Avg WPE > +1.0% | > +1.0% | +1.34% | **PASS** |
| No workload < -3% | 0 breaches | 0 breaches | **PASS** |
| Micro avg > +2% | > +2.0% | +2.39% | **PASS** |

**All three success criteria are met.**

## Full Results Table

| Workload | BL IPC | V2 IPC | T3 IPC | BL E(J) | V2 E(J) | T3 E(J) | V2 WPE | T3 WPE | V2 dWPE% | T3 dWPE% | Winner |
|----------|--------|--------|--------|---------|---------|---------|--------|--------|----------|----------|--------|
| balanced_pipeline_stress | 2.9079 | 2.9079 | 2.8793 | 3.3131 | 3.3135 | 3.3277 | 1.0000 | 0.9913 | -0.00% | -0.87% | V2 |
| phase_scan_mix | 0.4666 | 0.4716 | 0.4561 | 6.0051 | 5.0188 | 4.7415 | 1.0454 | 1.0295 | +4.54% | +2.95% | V2 |
| branch_entropy | 0.9092 | 0.9116 | 0.9872 | 6.0872 | 5.4191 | 4.4736 | 1.0256 | 1.1359 | +2.56% | +13.59% | **V3t3** |
| serialized_pointer_chase | 0.8266 | 0.7803 | 0.8088 | 4.3228 | 3.8472 | 4.1406 | 0.9775 | 0.9913 | -2.25% | -0.87% | **V3t3** |
| compute_queue_pressure | 2.3917 | 2.3917 | 2.3785 | 2.6859 | 2.6862 | 2.6869 | 1.0000 | 0.9955 | -0.00% | -0.45% | V2 |
| stream_cluster_reduce | 0.5136 | 0.5136 | 0.5136 | 3.4558 | 3.4573 | 3.4573 | 0.9999 | 0.9999 | -0.01% | -0.01% | TIE |
| gapbs_bfs | 1.4099 | 1.3710 | 1.4022 | 4.1889 | 3.7256 | 4.0180 | 1.0011 | 1.0040 | +0.11% | +0.40% | **V3t3** |
| gapbs_pr | 1.4063 | 1.3711 | 1.3985 | 4.2077 | 3.8204 | 4.0756 | 0.9990 | 1.0019 | -0.10% | +0.19% | **V3t3** |
| gapbs_cc | 1.4107 | 1.3768 | 1.4054 | 3.9362 | 3.6754 | 3.8845 | 0.9943 | 0.9996 | -0.57% | -0.04% | **V3t3** |
| gapbs_bc | 1.3965 | 1.3575 | 1.3899 | 4.2192 | 3.8099 | 4.2150 | 0.9978 | 0.9964 | -0.22% | -0.36% | V2 |
| gapbs_sssp | 1.3914 | 1.3632 | 1.3686 | 4.0086 | 3.6681 | 3.8259 | 1.0014 | 0.9961 | +0.14% | -0.39% | V2 |
| gapbs_tc | 1.3459 | 1.3907 | 1.3504 | 5.4609 | 4.3625 | 5.0202 | 1.0738 | 1.0197 | +7.38% | +1.97% | V2 |

## Per-Workload Mode Distribution (V3ml_t3)

Note: "conservative" mode now uses the same parameters as "light-conservative" (fw=6, cap=56, iqcap=26, lsqcap=28) due to the parameter override. The mode name differs but actual throttle behavior is identical.

### Micro benchmarks

| Workload | Aggressive | Light-Conservative | Conservative* | Total |
|----------|------------|-------------------|---------------|-------|
| balanced_pipeline_stress | 3470 (99.94%) | 0 (0%) | 2 (0.06%) | 3472 |
| phase_scan_mix | 2986 (13.62%) | 18937 (86.38%) | 0 (0%) | 21923 |
| branch_entropy | 195 (1.93%) | 9932 (98.05%) | 2 (0.02%) | 10129 |
| serialized_pointer_chase | 8881 (71.83%) | 0 (0%) | 3482 (28.16%) | 12363 |
| compute_queue_pressure | 4204 (100%) | 0 (0%) | 0 (0%) | 4204 |
| stream_cluster_reduce | 19468 (100%) | 0 (0%) | 0 (0%) | 19468 |

*Conservative mode uses same params as Light-Conservative in this run.

### GAPBS benchmarks

| Workload | Aggressive | Light-Conservative | Conservative* | Total |
|----------|------------|-------------------|---------------|-------|
| gapbs_bfs | 3309 (46.48%) | 0 (0%) | 3810 (53.52%) | 7119 |
| gapbs_bc | 2918 (40.63%) | 0 (0%) | 4264 (59.37%) | 7182 |
| gapbs_pr | 3123 (43.76%) | 0 (0%) | 4014 (56.25%) | 7137 |
| gapbs_cc | 3499 (49.26%) | 0 (0%) | 3604 (50.74%) | 7103 |
| gapbs_sssp | 2 (0.03%) | 7292 (99.97%) | 0 (0%) | 7294 |
| gapbs_tc | 2467 (33.37%) | 0 (0%) | 4926 (66.63%) | 7393 |

### Classification Distribution (V3ml_t3)

| Workload | Resource | HighMLP | Serialized | Control |
|----------|----------|---------|------------|---------|
| balanced_pipeline_stress | 3471 (99.97%) | 0 | 0 | 1 (0.03%) |
| phase_scan_mix | 8 (0.04%) | 2978 (13.58%) | 18937 (86.38%) | 0 |
| branch_entropy | 195 (1.93%) | 0 | 9932 (98.05%) | 2 (0.02%) |
| serialized_pointer_chase | 8791 (71.11%) | 0 | 0 | 3572 (28.89%) |
| compute_queue_pressure | 4203 (99.98%) | 1 (0.02%) | 0 | 0 |
| stream_cluster_reduce | 11387 (58.49%) | 8081 (41.51%) | 0 | 0 |
| gapbs_bfs | 3280 (46.07%) | 3 (0.04%) | 1 (0.01%) | 3835 (53.87%) |
| gapbs_bc | 2911 (40.53%) | 9 (0.13%) | 1 (0.01%) | 4261 (59.33%) |
| gapbs_pr | 3118 (43.69%) | 2 (0.03%) | 1 (0.01%) | 4016 (56.27%) |
| gapbs_cc | 3492 (49.16%) | 3 (0.04%) | 1 (0.01%) | 3607 (50.78%) |
| gapbs_sssp | 0 | 1 (0.01%) | 7293 (99.99%) | 0 |
| gapbs_tc | 2245 (30.37%) | 4 (0.05%) | 1 (0.01%) | 5143 (69.57%) |

## Analysis

### GAPBS recovery from Round 1

The primary goal of Round 2 was to fix the GAPBS regression caused by deep Conservative throttling. Results:

| GAPBS Benchmark | T2 dWPE (Round 1) | T3 dWPE (Round 2) | Improvement |
|-----------------|--------------------|--------------------|-------------|
| gapbs_bfs | -5.08% | +0.40% | +5.48pp |
| gapbs_bc | -3.01% | -0.36% | +2.65pp |
| gapbs_pr | -4.50% | +0.19% | +4.69pp |
| gapbs_cc | -4.35% | -0.04% | +4.31pp |
| gapbs_sssp | -0.39% | -0.39% | 0.00pp |
| gapbs_tc | -1.05% | +1.97% | +3.02pp |
| **Average** | **-3.06%** | **+0.30%** | **+3.36pp** |

Overriding Conservative params to match LightConservative eliminated all GAPBS breaches below -3%. The Control-dominated windows (53-70% of GAPBS windows) now use sweet-spot parameters instead of the overly aggressive deep Conservative.

### Micro benchmark stability

| Micro Benchmark | T2 dWPE (Round 1) | T3 dWPE (Round 2) | Change |
|-----------------|--------------------|--------------------|--------|
| balanced_pipeline_stress | -0.61% | -0.87% | -0.26pp |
| phase_scan_mix | +2.95% | +2.95% | 0.00pp |
| branch_entropy | +13.63% | +13.59% | -0.04pp |
| serialized_pointer_chase | -2.25% | -0.87% | +1.38pp |
| compute_queue_pressure | -0.00% | -0.45% | -0.45pp |
| stream_cluster_reduce | -0.01% | -0.01% | 0.00pp |
| **Average** | **+2.28%** | **+2.39%** | **+0.11pp** |

Micro avg WPE improved slightly from +2.28% to +2.39%. serialized_pointer_chase improved significantly (+1.38pp) because its 28.9% Control windows now also use sweet-spot params instead of deep Conservative. balanced_pipeline_stress and compute_queue_pressure regressed slightly (-0.26pp, -0.45pp) -- these are near-100% Aggressive workloads where the tiny Conservative overhead may have slightly different transient effects.

### V3t3 vs V2 head-to-head

- V3t3 wins: 5 (branch_entropy, serialized_pointer_chase, gapbs_bfs, gapbs_pr, gapbs_cc)
- V2 wins: 6 (balanced_pipeline_stress, phase_scan_mix, compute_queue_pressure, gapbs_bc, gapbs_sssp, gapbs_tc)
- Tie: 1 (stream_cluster_reduce)

V2 still wins on more individual workloads (6 vs 5), but V3t3 wins on aggregate WPE (+1.34% vs +0.96%) because the V3t3 wins are larger in magnitude (especially branch_entropy at +13.59% vs +2.56%).

### Key remaining gaps vs V2

1. **gapbs_tc**: V2 gets +7.38% (strong energy savings from fw=2), V3t3 gets +1.97%. V2's more aggressive throttling works better here.
2. **phase_scan_mix**: V2 gets +4.54%, V3t3 gets +2.95%. V2 gains IPC on this workload (0.472 vs 0.467 baseline) while V3t3 loses IPC (0.456).
3. **gapbs_sssp**: Both are similar (V2 +0.14%, V3t3 -0.39%), both use light throttling.

## Verdict

**V3t3 (Round 2) passes all success criteria and beats V2 on aggregate WPE (+1.34% vs +0.96%).** The strategy of eliminating deep Conservative by overriding its parameters to match LightConservative successfully fixed the GAPBS regression while maintaining micro benchmark gains. No workload breaches -3% (worst is -0.87%).
