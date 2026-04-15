# Task Execution Report

## Overview

Six tasks executed successfully. 260 experiments in the database (up from 246).
4-core adaptive multicore simulation is running in background (~2hrs expected).

---

## Task 1: Parameter Taxonomy

**Output**: `docs/adaptive_parameter_taxonomy.md`

Categorized all 39 adaptive parameters:
- Frontend (8): fetch width variants, IQ/LSQ caps
- Backend (19): inflight caps, rename/dispatch widths for all 6 mode variants
- Classification/Policy (12): thresholds, hysteresis, mode selection
- Window/Sampling (1): window cycle count

Includes data-flow diagram and V2 script-vs-code default comparison table.

---

## Task 2: Data Extraction & Charts

**Output**: `results/all_experiments.csv` (260 experiments), `results/charts/`

### Generated Charts
1. **baseline_vs_adaptive_bars.png** -- Bar chart of IPC, Power, Energy for 6 microbenchmarks
2. **pareto_perf_vs_energy.png** -- Performance vs energy tradeoff scatter
3. **all_v2_pareto.png** -- All 162 V2 experiments on single Pareto plot

### Key Table: Baseline vs Adaptive V2 (50M instructions)

| Workload | dPerf% | dPower% | dEnergy% | Verdict |
|----------|--------|---------|----------|---------|
| serialized_pointer_chase | +5.96% | -17.16% | -11.00% | Power/energy win, perf cost |
| branch_entropy | -0.18% | -11.61% | -11.26% | Near win-win |
| hash_probe_chain | 0% | 0% | 0% | No effect |
| **phase_scan_mix** | **-1.05%** | **-17.07%** | **-16.49%** | **Best: win-win** |
| stream_cluster_reduce | 0% | 0% | 0% | No effect |
| compute_queue_pressure | 0% | 0% | 0% | No effect |

---

## Task 3: Parameter Sensitivity (New Microbenchmarks)

**Output**: 4 new workloads compiled and tested (5M instructions each)

### Baseline Performance of New Workloads

| Workload | IPC | simTicks | Stress Target |
|----------|-----|----------|---------------|
| fetch_bandwidth_stress | 1.053 | 2.37B | Fetch width |
| iq_pressure_stress | 3.541 | 0.71B | IQ capacity |
| lsq_pressure_stress | 1.830 | 1.37B | LSQ capacity |
| rename_dispatch_stress | 1.680 | 1.49B | Rename/dispatch width |

### Sensitivity Results (Forced Conservative Mode)

All workloads forced into conservative mode via `adaptiveMemBlockRatioThres=0.0`:

| Workload | Baseline IPC | Forced Cons. IPC | **Delta** | Target Param |
|----------|-------------|-----------------|-----------|-------------|
| fetch_bandwidth_stress | 1.053 | 1.053 | **0%** | FetchWidth=2 |
| iq_pressure_stress | 3.541 | 3.541 | **0%** | IQCap=32 |
| **lsq_pressure_stress** | **1.830** | **1.087** | **-40.6%** | **LSQCap=16** |
| rename_dispatch_stress | 1.680 | 1.680 | **0%** | RenameWidth=2, DispatchWidth=2 |

### Key Finding

**LSQ cap is the only parameter among the tested set that produces a large measurable
effect.** Reducing the LSQ cap to 16 caused a 40.6% IPC drop on the LSQ-stress workload.
All other parameters (fetch width=2, IQ cap=32, rename/dispatch width=2) had zero
measurable impact in forced-conservative mode.

**Interpretation**: The O3 pipeline's bottleneck under conservative throttling is
dominated by the inflight cap (ROB occupancy limit at 96) and memory blocking behavior,
not by fetch width or IQ/dispatch width individually. The LSQ cap matters because it
directly limits outstanding memory operations, creating a hard barrier for memory-heavy
workloads.

---

## Task 4: Mode Analysis & Visualization

**Output**: `results/mode_analysis/` with timeline plots, pie charts, and quality reports

### phase_scan_mix (best adaptive workload)
- 21,206 windows, 2,462 mode switches (11.6%)
- Classification: 51.8% Serialized, 31.7% Resource, 14.0% HighMLP, 2.4% Control
- Mode: 50.6% conservative, 49.4% aggressive
- Switch quality: 49.4% beneficial, 50.6% harmful (avg IPC delta: +0.000043)
- 1,921 rapid oscillation events detected (phase transition boundary noise)

### serialized_pointer_chase
- Clear two-phase behavior: aggressive in init/warmup, then conservative during pointer chasing
- 73.5% aggressive, 26.5% conservative
- Visible transition point where mem_block_ratio jumps above threshold

### branch_entropy
- Rapid oscillation between aggressive and conservative throughout
- 70.1% aggressive, 29.9% conservative
- High squash_ratio and branch_recovery_ratio throughout

---

## Task 5: Multicore Conversion

**Output**: Modified `cpu.cc` (per-CPU log naming), multicore run scripts

### Code Change
`cpu.cc:202`: Window log filename now includes CPU ID for multi-CPU configs:
- CPU 0: `adaptive_window_log.csv` (backward compatible)
- CPU 1+: `adaptive_window_log_cpu{N}.csv`

### 4-Core Baseline Results (Mixed Workloads, 5M insts)

| CPU | Workload | IPC (4-core) | IPC (1-core) | Delta |
|-----|----------|-------------|-------------|-------|
| 0 | serialized_pointer_chase | 0.523 | 0.827 | -36.8% |
| 1 | branch_entropy | 1.022 | 0.910 | +12.3% |
| 2 | phase_scan_mix | 0.432 | 0.467 | -7.5% |
| 3 | compute_queue_pressure | 2.311 | 2.395 | -3.5% |

**Key Finding**: Shared L2 contention significantly impacts memory-sensitive workloads.
`serialized_pointer_chase` loses 36.8% IPC due to L2 contention, while compute-bound
`compute_queue_pressure` loses only 3.5%.

### 4-Core Adaptive V2 Results (Mixed Workloads, 5M insts)

| CPU | Workload | Baseline IPC | Adaptive IPC | Delta |
|-----|----------|-------------|-------------|-------|
| 0 | serialized_pointer_chase | 0.5230 | 0.5231 | +0.02% |
| 1 | branch_entropy | 1.0216 | 1.0231 | +0.15% |
| 2 | phase_scan_mix | 0.4321 | 0.4319 | -0.05% |
| 3 | compute_queue_pressure | 2.3113 | 2.3113 | 0% |

Per-CPU window logs generated correctly:
- `adaptive_window_log.csv` (CPU 0)
- `adaptive_window_log_cpu1.csv` (CPU 1)
- `adaptive_window_log_cpu2.csv` (CPU 2)
- `adaptive_window_log_cpu3.csv` (CPU 3)

**Finding**: With only 5M instructions, adaptive V2 shows minimal impact in multicore.
The short run length means most windows stay in aggressive mode. Longer runs (50M+)
are needed to see meaningful mode switching and energy differences -- consistent with
the single-core observation that V2's benefit grows with run length.

**Note on --param syntax**: gem5 multicore requires `system.cpu[N].param` (bracket
notation, matching Python object paths), not `system.cpu{N}.param`. The
`run_adaptive_multicore.sh` script has been fixed accordingly.

---

## Task 6: Design Exploration

**Output**: `docs/design_exploration.md`

Top 3 recommended extensions:
1. **DVFS Integration** (High impact) -- Reduce frequency during memory-stall phases
2. **Shared-Resource-Aware Adaptation** (High impact) -- L2 contention feedback to per-CPU classifiers
3. **Prefetcher Control** (Medium impact, quick win) -- Disable prefetcher for serialized, enable for HighMLP

---

## Files Created/Modified

### New Documents
- `docs/adaptive_parameter_taxonomy.md`
- `docs/design_exploration.md`

### New Scripts
- `scripts/extract_all_results.py`
- `scripts/generate_comparison_tables.py`
- `scripts/generate_charts.py`
- `scripts/visualize_mode_timeline.py`
- `scripts/analyze_classification_quality.py`
- `scripts/analyze_signal_correlations.py`
- `scripts/run_sensitivity_sweep.sh`
- `scripts/run_baseline_multicore.sh`
- `scripts/run_adaptive_multicore.sh`

### New Workloads
- `workloads/fetch_bandwidth_stress/`
- `workloads/iq_pressure_stress/`
- `workloads/lsq_pressure_stress/`
- `workloads/rename_dispatch_stress/`

### Modified Files
- `src/cpu/o3/cpu.cc` (line 202: per-CPU window log naming)
- `workloads/Makefile` (added 4 new workload directories)

### Generated Results
- `results/all_experiments.csv` (260 experiments)
- `results/charts/baseline_vs_adaptive_bars.png`
- `results/charts/pareto_perf_vs_energy.png`
- `results/charts/all_v2_pareto.png`
- `results/mode_analysis/{workload}/` (timelines, distributions, quality reports)
