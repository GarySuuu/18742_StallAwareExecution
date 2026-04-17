# Round 7 Phase A: Per-Window Deep Analysis of v3t8

## 1. Per-Mode IPC Summary

### GAPBS Benchmarks (window=2500 cycles)

| Benchmark | Mode | Windows | Avg IPC | Std | Avg Squash |
|-----------|------|---------|---------|-----|------------|
| bfs | aggressive | 1 | 0.3552 | 0 | 0.4230 |
| bfs | light-conservative | 14681 | 1.4021 | 0.0967 | 0.1955 |
| bc | aggressive | 1 | 0.3552 | 0 | 0.4182 |
| bc | light-conservative | 14861 | 1.3851 | 0.1001 | 0.2056 |
| pr | aggressive | 1 | 0.3504 | 0 | 0.4644 |
| pr | light-conservative | 14725 | 1.3979 | 0.0978 | 0.2090 |
| cc | aggressive | 1 | 0.3552 | 0 | 0.4167 |
| cc | light-conservative | 14658 | 1.4042 | 0.0977 | 0.2049 |
| sssp | aggressive | 1 | 0.3552 | 0 | 0.4026 |
| sssp | light-conservative | 14660 | 1.4039 | 0.0970 | 0.2091 |
| tc | aggressive | 1 | 0.3552 | 0 | 0.4197 |
| tc | light-conservative | 14318 | 1.4376 | 0.0942 | 0.2721 |

Key observation: All GAPBS benchmarks spend 99.99% of windows in light-conservative mode (only 1 aggressive window = warmup). The entire execution is throttled.

### Micro Benchmarks (window=5000 cycles)

| Benchmark | Mode | Windows | Avg IPC | Std | Avg Squash |
|-----------|------|---------|---------|-----|------------|
| balanced_pipeline_stress | aggressive | 3444 | 2.9018 | 0.1111 | 0.1572 |
| balanced_pipeline_stress | conservative | 2 | 2.6462 | 0.3504 | 0.1318 |
| branch_entropy | aggressive | 196 | 1.3069 | 0.4353 | 0.3214 |
| branch_entropy | light-conservative | 9825 | 1.1169 | 0.0371 | 0.3266 |
| branch_entropy | conservative | 2 | 1.1687 | 0.0805 | 0.3507 |
| compute_queue_pressure | aggressive | 4180 | 2.5262 | 0.0762 | 0.0003 |
| phase_scan_mix | aggressive | 2986 | 0.5274 | 0.0350 | 0.0015 |
| phase_scan_mix | light-conservative | 18780 | 0.4917 | 0.2533 | 0.3488 |
| serialized_pointer_chase | aggressive | 8875 | 0.7776 | 0.1778 | 0.1106 |
| serialized_pointer_chase | conservative | 3492 | 0.9942 | 0.0766 | 0.2920 |
| stream_cluster_reduce | aggressive | 19468 | 0.6201 | 0.1774 | 0.0000 |

## 2. Tight vs Normal Light-Conservative Split (GAPBS)

| Benchmark | Tight N | Tight IPC | Tight Squash | Normal N | Normal IPC | Normal Squash | IPC Gap |
|-----------|---------|-----------|-------------|----------|-----------|--------------|---------|
| bfs | 1,379 | 1.2512 | 0.3100 | 13,302 | 1.4177 | 0.1836 | -11.7% |
| bc | 3,227 | 1.2679 | 0.3129 | 11,634 | 1.4176 | 0.1759 | -10.6% |
| pr | 4,196 | 1.3384 | 0.3252 | 10,529 | 1.4216 | 0.1627 | -5.9% |
| cc | 3,876 | 1.3345 | 0.3209 | 10,782 | 1.4293 | 0.1632 | -6.6% |
| sssp | 4,454 | 1.2985 | 0.3152 | 10,206 | 1.4499 | 0.1628 | -10.4% |
| tc | 8,993 | 1.4020 | 0.3813 | 5,325 | 1.4977 | 0.0878 | -6.4% |

Key findings:
- Tight windows have **lower IPC** than normal windows (6-12% lower)
- Tight windows have higher squash ratios (0.31-0.38 vs 0.08-0.18)
- tc has the most tight windows (63% of all LC windows), but its IPC gap is moderate

## 3. Squash Threshold Sensitivity

| Benchmark | @0.25 | @0.30 (current) | @0.35 | @0.40 |
|-----------|-------|-----------------|-------|-------|
| bfs | 54.6% | 9.4% | 0.0% | 0.0% |
| bc | 58.1% | 21.7% | 0.1% | 0.0% |
| pr | 55.7% | 28.5% | 2.1% | 0.0% |
| cc | 54.3% | 26.4% | 1.0% | 0.0% |
| sssp | 58.4% | 30.4% | 0.2% | 0.0% |
| tc | 67.4% | 62.8% | 53.4% | 14.1% |

Key findings:
- At threshold=0.25, ~55% of windows become tight (massive IPC cost)
- At threshold=0.30, 9-31% are tight (current config)
- At threshold=0.35, almost no windows are tight (except tc at 53%)
- tc is an outlier: even at 0.35, 53% tight (inherently high squash workload)

## 4. IPC Loss Attribution (bfs/bc/pr/cc)

All GAPBS benchmarks have only 1 aggressive window, so loss attribution is measured relative to aggressive IPC (which is just the warmup window and not meaningful). Instead, the key insight is:

**Normal windows (fw=5) dominate**: 73-92% of the IPC "weight" comes from normal windows simply because they are much more numerous. Tight windows (fw=4) contribute 8-27%.

The real question is: can we raise normal fw from 5 to 6 (closer to baseline fw=8) without increasing squash waste?

Normal window avg squash is 0.16-0.18 -- relatively low, suggesting fw=5 may be over-throttling.
Tight window avg squash is 0.31-0.33 -- higher, justifying stronger throttle.

## 5. Micro Tight/Normal Split

| Benchmark | Tight | Normal LC | Tight Squash | Normal Squash |
|-----------|-------|-----------|-------------|--------------|
| branch_entropy | 9,430 | 395 | 0.3279 | 0.2939 |
| phase_scan_mix | 13,742 | 5,038 | 0.4766 | 0.0002 |

branch_entropy: almost entirely tight (96% of LC windows)
phase_scan_mix: 73% tight with very high squash (0.48)

## Summary / Recommendations for Phase B

1. **Normal fw=5 is the dominant source of IPC loss** for bfs/bc/pr/cc (73-92% of weighted windows)
2. Normal windows have low squash (~0.17), suggesting fw=6 may work without energy penalty
3. Tight windows correctly identify high-squash phases, but their fw=4 impact is a secondary concern
4. Testing fw=6 normal with different tight thresholds is the right approach
