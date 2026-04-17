# Round 4 Results

## 1. Config A (v3t5a): fw=5, cap=96, iq=0, lsq=0, window=2500, mem_block=0.12

| Bench | IPC | Energy (J) | IPC% vs BL | Energy% vs BL | WPE% |
|-------|-----|-----------|------------|---------------|------|
| bfs | 1.360119 | 3.42380 | -3.53% | -14.80% | +0.33% |
| bc | 1.344616 | 3.48705 | -3.72% | -13.84% | -0.05% |
| pr | 1.366813 | 3.65309 | -2.81% | -9.51% | -0.28% |
| cc | 1.371702 | 3.60149 | -2.76% | -4.36% | -1.34% |
| sssp | 1.368625 | 3.48365 | -1.64% | -9.18% | +0.61% |
| tc | 1.371213 | 4.60645 | +1.88% | -12.79% | +4.32% |
| **AVG** | | | | | **+0.60%** |

## 2. Config B (v3t5b): fw=4, cap=128, iq=26, lsq=28, window=2500, mem_block=0.12

| Bench | IPC | Energy (J) | IPC% vs BL | Energy% vs BL | WPE% |
|-------|-----|-----------|------------|---------------|------|
| bfs | 1.346955 | 3.29946 | -4.47% | -17.89% | +0.29% |
| bc | 1.338354 | 3.43808 | -4.16% | -15.05% | -0.14% |
| pr | 1.335361 | 3.23113 | -5.05% | -19.96% | +0.31% |
| cc | 1.338236 | 3.21914 | -5.13% | -14.52% | -1.07% |
| sssp | 1.344742 | 3.31341 | -3.35% | -13.62% | +0.20% |
| tc | 1.398141 | 3.92574 | +3.88% | -25.68% | +9.40% |
| **AVG** | | | | | **+1.50%** |

## 3. Comparison Table (GAPBS)

| Bench | V2 WPE% | v3t4 WPE% | CfgA WPE% | CfgB WPE% | Best |
|-------|---------|-----------|-----------|-----------|------|
| bfs | +0.24% | +0.48% | +0.33% | +0.29% | v3t4 |
| bc | -0.11% | -0.08% | -0.05% | -0.14% | CfgA |
| pr | +0.01% | +0.29% | -0.28% | +0.31% | CfgB |
| cc | -0.48% | -0.88% | -1.34% | -1.07% | V2 |
| sssp | +0.24% | +0.40% | +0.61% | +0.20% | CfgA |
| tc | +7.53% | +9.60% | +4.32% | +9.40% | v3t4 |
| **AVG** | **+1.24%** | **+1.64%** | **+0.60%** | **+1.50%** | **v3t4** |

## 4. Best GAPBS Config Selection

**Config B (v3t5b)** has the highest GAPBS avg WPE at +1.50%, but **v3t4** at +1.64% still beats both new configs.

- Config A (fw=5) badly hurts tc (+4.32% vs v3t4's +9.60%), losing 5.28pp on tc. The fw=5 helps pr/cc IPC slightly but not enough to compensate.
- Config B (fw=4, iq=26, lsq=28) is essentially identical to v3t4 on tc (+9.40% vs +9.60%), but worse on bfs/bc/sssp. Adding IQ/LSQ caps did not help the non-tc benchmarks.

Neither new config beats v3t4. The best GAPBS config remains **v3t4** (fw=4, cap=128, iq=0, lsq=0).

However, since we must select between Config A and Config B: **Config B** wins with avg +1.50% (vs Config A's +0.60%), and no workload < -3%.

## 5. Overall Avg WPE (Config B GAPBS + Micro v3t3)

### Micro v3t3 results (unchanged from prior rounds)

| Bench | WPE% |
|-------|------|
| balanced_pipeline_stress | -0.87% |
| branch_entropy | +13.85% |
| compute_queue_pressure | -0.45% |
| phase_scan_mix | +3.53% |
| serialized_pointer_chase | -0.78% |
| stream_cluster_reduce | -0.01% |
| **Micro AVG** | **+2.55%** |

### Overall (Config B + Micro v3t3)

- GAPBS avg (Config B): +1.50%
- Micro avg (v3t3): +2.55%
- **Overall avg (12 benchmarks): +2.02%**

### Overall (v3t4 GAPBS + Micro v3t3) for reference

- GAPBS avg (v3t4): +1.64%
- Micro avg (v3t3): +2.55%
- **Overall avg (12 benchmarks): +2.10%**

## 6. Summary and Success Criteria

| Criterion | Target | Config B Result | Met? |
|-----------|--------|----------------|------|
| GAPBS avg WPE > v3t4 (+1.43%) | > +1.43% | +1.50% | YES (marginally) |
| Overall avg WPE > v3t4 (+1.91%) | > +1.91% | +2.02% | YES (marginally) |
| No workload < -3% | all >= -3% | worst = cc at -1.07% | YES |

**Note**: The strategy doc quoted v3t4 GAPBS avg as +1.43% and overall as +1.91%. Re-computing from raw data gives v3t4 GAPBS avg = +1.64% and overall = +2.10%. Against the re-computed baseline:
- Config B GAPBS avg (+1.50%) is BELOW v3t4 (+1.64%) by 0.14pp
- Config B overall (+2.02%) is BELOW v3t4 (+2.10%) by 0.08pp

**Conclusion**: Neither Config A nor Config B improves over v3t4. The best overall configuration remains **v3t4** (fw=4, cap=128, iq=0, lsq=0) for GAPBS, combined with v3t3 micro settings.

### Key findings:
1. **fw=5 (Config A) hurts tc badly**: tc WPE drops from +9.60% to +4.32% (-5.28pp). The small improvements on other benchmarks (+0.2pp on sssp, +0.03pp on bc) do not compensate.
2. **IQ/LSQ caps (Config B) are neutral-to-negative**: Adding iq=26, lsq=28 to the fw=4 config does not help non-tc benchmarks. bfs drops 0.19pp, sssp drops 0.20pp, tc drops 0.20pp.
3. **v3t4 remains the best GAPBS config found so far** at +1.64% avg WPE.
4. **Overall best: v3t4 GAPBS + v3t3 micro = +2.10% avg WPE across 12 benchmarks.**
