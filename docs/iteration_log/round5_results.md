# Round 5 Results

## 1. Config A (v3t6a): Strict Control threshold (branch>=0.15, squash>=0.25)

| Bench | IPC | Energy (J) | IPC% vs BL | Energy% vs BL | WPE% |
|-------|-----|-----------|------------|---------------|------|
| bfs | 1.350180 | 3.47854 | -4.24% | -16.96% | +0.25% |
| bc | 1.339671 | 3.61989 | -4.07% | -14.20% | -0.26% |
| pr | 1.336057 | 3.42080 | -5.00% | -18.70% | +0.04% |
| cc | 1.341599 | 3.39899 | -4.90% | -13.65% | -1.08% |
| sssp | 1.348106 | 3.48986 | -3.11% | -12.94% | +0.24% |
| tc | 1.401135 | 4.09554 | +4.11% | -25.00% | +9.39% |
| **AVG** | | | | | **+1.43%** |

## 2. Config B (v3t6b): Mild threshold (branch>=0.12, squash>=0.22)

| Bench | IPC | Energy (J) | IPC% vs BL | Energy% vs BL | WPE% |
|-------|-----|-----------|------------|---------------|------|
| bfs | 1.350180 | 3.47854 | -4.24% | -16.96% | +0.25% |
| bc | 1.339671 | 3.61989 | -4.07% | -14.20% | -0.26% |
| pr | 1.336057 | 3.42080 | -5.00% | -18.70% | +0.04% |
| cc | 1.341599 | 3.39899 | -4.90% | -13.65% | -1.08% |
| sssp | 1.348106 | 3.48986 | -3.11% | -12.94% | +0.24% |
| tc | 1.401135 | 4.09554 | +4.11% | -25.00% | +9.39% |
| **AVG** | | | | | **+1.43%** |

## 3. Classification Distribution Comparison

### v3t4 vs CfgA vs CfgB -- Per Benchmark

All three configs produce **identical** classification and mode distributions:

| Bench | Total Windows | Serialized-mem (%) | High-MLP (%) | Control (%) | Resource (%) | Aggressive (%) | Light-Cons (%) | Conservative (%) |
|-------|--------------|-------------------|-------------|------------|-------------|---------------|---------------|-----------------|
| bfs | 14785-14786 | ~100% | <0.01% | 0% | 0% | <0.01% | ~100% | 0% |
| bc | 14901-14902 | ~100% | <0.01% | 0% | 0% | <0.01% | ~100% | 0% |
| pr | 14940-14941 | 100% | 0% | 0% | 0% | <0.01% | ~100% | 0% |
| cc | 14881-14882 | ~100% | <0.01% | 0% | 0% | <0.01% | ~100% | 0% |
| sssp | 14808-14809 | ~100% | <0.01% | 0% | 0% | <0.01% | ~100% | 0% |
| tc | 14247-14248 | ~100% | <0.01% | 0% | 0% | <0.01% | ~100% | 0% |

**No change in classification distribution.** The Control classification thresholds (branchRecoveryRatioThres, squashRatioThres) have **zero effect** on any GAPBS benchmark because the classification logic checks `mem_block_ratio >= 0.12` first (line 779 in cpu.cc). Since all GAPBS windows satisfy this memory-dominated check, they are classified as Serialized-memory or High-MLP **before** the Control check (line 793) is ever reached. The Control branch is unreachable for these workloads.

### Root Cause Analysis

The classification function in `src/cpu/o3/cpu.cc` (adaptiveClassifyWindow) has a priority-ordered structure:

1. **First check**: `mem_block_ratio >= 0.12` (memory-dominated)
   - If true and outstanding misses high -> HighMLP or Resource
   - If true and outstanding misses low -> **Serialized** (this is where ALL GAPBS windows land)
2. **Second check**: `branch_recovery >= threshold AND squash >= threshold` -> **Control**
3. **Third check**: IQ saturation -> Resource
4. **Default**: Resource

Since all GAPBS benchmarks have `mem_block_ratio >= 0.12`, the first check always fires and the function returns before reaching the Control check. Changing the Control thresholds is therefore a no-op for these workloads.

The strategy document's premise that GAPBS benchmarks had "47% Aggressive + 53% Conservative (Control windows)" was incorrect -- that distribution does not match the actual v3t4 data, which shows 100% Serialized/light-conservative for all GAPBS benchmarks.

## 4. WPE Comparison: V2 vs v3t4 vs CfgA vs CfgB

| Bench | V2 WPE% | v3t4 WPE% | CfgA WPE% | CfgB WPE% | Best |
|-------|---------|-----------|-----------|-----------|------|
| bfs | +0.11% | +0.26% | +0.25% | +0.25% | v3t4 |
| bc | -0.22% | -0.26% | -0.26% | -0.26% | V2 |
| pr | -0.10% | +0.04% | +0.04% | +0.04% | v3t4/CfgA/CfgB |
| cc | -0.57% | -1.08% | -1.08% | -1.08% | V2 |
| sssp | +0.14% | +0.23% | +0.24% | +0.24% | CfgA/CfgB |
| tc | +7.38% | +9.39% | +9.39% | +9.39% | v3t4/CfgA/CfgB |
| **AVG** | **+1.12%** | **+1.43%** | **+1.43%** | **+1.43%** | **v3t4/CfgA/CfgB** |

**CfgA and CfgB are functionally identical to v3t4.** The tiny IPC differences (e.g., bfs: 1.350317 vs 1.350180) are within simulation noise and do not represent meaningful changes.

## 5. Best Config Selection

**Neither Config A nor Config B produces any change compared to v3t4.** The Control threshold parameters are unreachable for GAPBS workloads because the memory-dominated classification check has higher priority and fires first for all windows.

The best GAPBS config remains **v3t4** (fw=4, cap=128, iq=0, lsq=0, window=2500, mem_block=0.12).

## 6. Final Overall WPE (Best GAPBS + Micro v3t3)

### Micro v3t3 results (unchanged)

| Bench | WPE% |
|-------|------|
| balanced_pipeline_stress | -0.87% |
| branch_entropy | +13.59% |
| compute_queue_pressure | -0.45% |
| phase_scan_mix | +2.95% |
| serialized_pointer_chase | -0.87% |
| stream_cluster_reduce | -0.01% |
| **Micro AVG** | **+2.39%** |

### Overall (v3t4 GAPBS + v3t3 Micro)

- GAPBS avg (v3t4): +1.43%
- Micro avg (v3t3): +2.39%
- **Overall avg (12 benchmarks): +1.91%**

## 7. Summary

| Criterion | Target | Result | Met? |
|-----------|--------|--------|------|
| Any Config GAPBS avg WPE > v3t4 (+1.43%) | > +1.43% | +1.43% (identical) | NO |
| Improve cc/bc without hurting tc | any improvement | no change | NO |
| Control window % reduced | any reduction | 0% -> 0% | N/A |

**Round 5 produced no improvement.** The hypothesis that adjusting Control classification thresholds would reduce unnecessary throttling on cc/bc was invalid because GAPBS benchmarks never reach the Control classification branch. All windows are classified as Serialized-memory dominated due to the memory-dominated check having higher priority in the classification logic. The Control thresholds only affect workloads where `mem_block_ratio < 0.12` and `branch_recovery_ratio` and `squash_ratio` are both above their respective thresholds -- a condition that no current GAPBS benchmark satisfies.

**Best overall configuration remains unchanged: v3t4 GAPBS + v3t3 Micro = +1.91% avg WPE across 12 benchmarks.**
