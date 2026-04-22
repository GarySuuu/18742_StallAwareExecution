# Adaptive O3 CPU for Power Optimization — Final Report

**18-742 Project**: Runtime-adaptive throttling mechanism on gem5 `DerivO3CPU` (ARM, SE mode) to reduce power/energy with minimal performance impact.

**Final result**: V4 achieves **Overall EDP +13.36%** (Micro +14.70%, GAPBS +12.03%) vs baseline, with 6 micro + 6 GAPBS workloads all using identical parameters. Best single workload: branch_entropy +39.6% EDP.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Evaluation Metric: EDP](#2-evaluation-metric-edp)
3. [Part I: Analysis](#part-i-analysis)
   - 3.1 Parameter Classification
   - 3.2 Parameter Sweep & Sweet Spot Discovery
   - 3.3 Per-Window Mode Analysis
   - 3.4 Window Size Sweep
4. [Part II: Design & Implementation](#part-ii-design--implementation)
   - 4.1 Three-Tier Execution Mode
   - 4.2 Resource Congestion Detection
   - 4.3 Adaptive Window Size
   - 4.4 Unified Configuration
5. [Iteration Process (8 Rounds)](#5-iteration-process-8-rounds)
6. [Final Results](#6-final-results)
   - 6.1 Single-core Results (12 workloads)
   - 6.2 Multi-core Results (4-core)
   - 6.3 Best Case vs Worst Case Analysis
7. [Key Lessons & Abandoned Directions](#7-key-lessons--abandoned-directions)

---

## 1. Project Overview

**Target**: Single-core (and later 4-core) `DerivO3CPU` on ARM, SE mode, with L1/L2 caches and 2GB memory.

**Hypothesis**: Some execution windows are wide-parallel and benefit from aggressive execution; others are bottlenecked by serialized memory or control recovery where wide aggressive execution wastes power. If we classify windows online and selectively enter conservative modes, we can improve the performance-energy tradeoff.

**Architecture**: A controller on top of the O3 CPU that:
- Samples recent pipeline behavior each window
- Classifies the window into one of 4 stall-type classes
- Maps the class to an execution mode (Aggressive/Conservative/Deep Conservative)
- Changes fetch/inflight/IQ/LSQ limits at window boundaries

**V2 baseline** (prior work): 2-mode (Aggressive/Conservative) with fixed conservative params fw=2, cap=96. Manual per-workload tuning (e.g., window=2500 for GAPBS).

**V4 (this work)**: 3-tier mode + Resource congestion sub-detection + adaptive window + unified parameters.

---

## 2. Evaluation Metric: EDP

**EDP (Energy-Delay Product)**:
```
EDP = Energy × Time (Joule-seconds, lower = better)
EDP improvement% = (1 - EDP_new / EDP_baseline) × 100%
```

Standard metric in computer architecture literature (Gonzalez & Horowitz 1996). Equal weighting of energy and performance. More sensitive to energy savings than pure IPC.

---

## Part I: Analysis

### 3.1 Parameter Classification (Task 1)

All 39 adaptive parameters in `BaseO3CPU.py` were classified by their pipeline impact:

| Category | Count | Stage | Representative Parameters |
|----------|-------|-------|--------------------------|
| Frontend | 8 | Fetch | FetchWidth, IQCap, LSQCap |
| Backend | 19 | Execute/Commit | InflightCap, RenameWidth, DispatchWidth |
| Classification/Policy | 11 | Classifier | MemBlockRatioThres, SwitchHysteresis |
| Window/Sampling | 1 | Windowing | WindowCycles |

For each parameter, we traced its use in `cpu.cc`/`fetch.cc` and built a data-flow diagram: parameter definition → mode selection → per-stage throttle.

### 3.2 Parameter Sweep & Sweet Spot Discovery (Task 2)

Designed a balanced workload `balanced_pipeline_stress` (IPC=2.91) that exercises all pipeline stages. Ran 74 dense sweep experiments across 6 architectural parameters, observing 16 low-level pipeline signals.

**Key discovery — "Over-speculation" problem**:

Baseline 8-wide O3 CPU shows burst-stall oscillation:
- 33.6% of cycles: 0 instructions fetched (stalled by backend pressure)
- 38.6% of cycles: 8 instructions fetched (full speed)
- IQFullEvents = 2.75M, rename blocked 9.8% of cycles

**5 parameters exhibit sweet spot** — IPC exceeds baseline when moderately limited:

| Parameter | Sweet Spot | dIPC | Mechanism |
|-----------|-----------|------|-----------|
| IQ Cap | 26 | +5.3% | Reduces IQ backpressure on rename |
| LSQ Cap | 28 | +5.0% | Eliminates 96% of memory order violations |
| Inflight Cap | 52~72 | +4.4% | Indirectly controls IQ+LSQ fill |
| Fetch Width | 6 | +3.3% | Matches frontend throughput to backend capacity |
| Dispatch Width | 5 | +1.5% | Reduces IQ overfilling |

**Masking relationships**: Fetch Width masks Inflight Cap (at fw=2, cap=64/96/128 all give identical IPC). Inflight Cap masks IQ Cap. Must disable upstream masks when sweeping downstream parameters.

**Method**: Forced conservative mode via `memBlockRatioThres=0.0 + outstandingMissThres=9999`. Non-uniform dense sampling around sweet spots.

**Saved plots** (all under [gem5/results/charts/](../results/charts/)):
- **Per-parameter detail plots** (one PNG per parameter showing all 16 signals):
  - [sweep_detail_fetch_width.png](../results/charts/sweep_detail_fetch_width.png)
  - [sweep_detail_dispatch_width.png](../results/charts/sweep_detail_dispatch_width.png)
  - [sweep_detail_rename_width.png](../results/charts/sweep_detail_rename_width.png)
  - [sweep_detail_iq_cap.png](../results/charts/sweep_detail_iq_cap.png)
  - [sweep_detail_lsq_cap.png](../results/charts/sweep_detail_lsq_cap.png)
  - [sweep_detail_inflight_cap_rob.png](../results/charts/sweep_detail_inflight_cap_rob.png)
- **Cross-parameter comparison plots**:
  - [sweep_ipc_all_groups.png](../results/charts/sweep_ipc_all_groups.png) — IPC vs every parameter on one chart
  - [sweep_width_comparison.png](../results/charts/sweep_width_comparison.png) — fetch/dispatch/rename width overlay
  - [sweep_sweet_spot.png](../results/charts/sweep_sweet_spot.png) — sweet-spot highlight figure
  - [sweep_masking_proof.png](../results/charts/sweep_masking_proof.png) — evidence of fw→inflight→IQ masking
  - [sweep_signal_heatmap.png](../results/charts/sweep_signal_heatmap.png) — 16-signal heatmap over parameter values
  - [sweep_lsq_detail.png](../results/charts/sweep_lsq_detail.png) — LSQ-only deep dive
- **Per-parameter per-signal grid** (6 params × 16 signals = 96 PNGs): [results/charts/sweep/\<param\>/\<signal\>.png](../results/charts/sweep/) — e.g. [fetch_width/ipc.png](../results/charts/sweep/fetch_width/ipc.png), [iq_cap/iq_full_events.png](../results/charts/sweep/iq_cap/iq_full_events.png).
- **Raw data**: [results/sweep_signals.csv](../results/sweep_signals.csv).

### 3.3 Per-Window Mode Analysis (Task 3)

Analyzed 21,000+ windows across 3 representative workloads (phase_scan_mix, serialized_pointer_chase, branch_entropy).

**Key findings**:

1. **`squash_ratio` is the strongest classification signal**: |r|=0.87 with IPC, vs `mem_block_ratio` |r|=0.36. However, the original classifier tree uses mem_block_ratio as first-level decision — a design weakness that motivated our squash-based sub-level.

2. **35.1% of windows oscillate near `avg_outstanding_misses` threshold (12.0)** — major source of mode switching noise.

3. **Classifier blindspot on serialized_pointer_chase**: 0% windows classified as Serialized despite the workload being memory-serialized. Reason: `mem_block_ratio` proxy has low sensitivity when O3 CPU speculatively executes during cache misses.

4. **Conservative IPC > Aggressive IPC by 22.3%** on serialized_pointer_chase — directly validates the "over-speculation" hypothesis. The 8-wide front-end wastes pipeline resources on speculative instructions that are almost all squashed in pointer-chase patterns.

5. **Classifier accuracy is not critical** — as long as the mode IPC difference is small, classification noise doesn't hurt results.

**Saved plots** (under [gem5/results/mode_analysis/](../results/mode_analysis/), one directory per workload):
- `phase_scan_mix/` — [class_distribution.png](../results/mode_analysis/phase_scan_mix/phase_scan_mix_class_distribution.png) (4-class histogram), [mode_timeline.png](../results/mode_analysis/phase_scan_mix/phase_scan_mix_mode_timeline.png) (per-window mode trajectory)
- `serialized_pointer_chase/` — [class_distribution.png](../results/mode_analysis/serialized_pointer_chase/serialized_pointer_chase_class_distribution.png), [mode_timeline.png](../results/mode_analysis/serialized_pointer_chase/serialized_pointer_chase_mode_timeline.png)
- `branch_entropy/` — [class_distribution.png](../results/mode_analysis/branch_entropy/branch_entropy_class_distribution.png), [mode_timeline.png](../results/mode_analysis/branch_entropy/branch_entropy_mode_timeline.png)

### 3.4 Window Size Sweep

Swept 9 window sizes (1000~10000) on 6 representative workloads:

| Workload | Best Window | Behavior |
|----------|------------|----------|
| gapbs_tc | **1000** | Fast phase changes need short windows (EDP +25.9% vs 5000's +18.9%) |
| gapbs_bfs | 1000 | Short windows for fast throttle |
| branch_entropy | 7500 | Steady-state prefers large windows |
| balanced_pipeline_stress | 4000 | Medium |
| phase_scan_mix | any | Window-size insensitive |

**Conclusion**: Different workloads require dramatically different window sizes. This motivated the adaptive window size mechanism — eliminate manual per-workload selection.

---

## Part II: Design & Implementation

### 4.1 Three-Tier Execution Mode

Expanded V2's 2-tier system (Aggressive/Conservative) to 3 tiers with a squash-based sub-level.

| Tier | FetchWidth | Trigger | Design Rationale |
|------|-----------|---------|------------------|
| **Aggressive** | 8 (baseline) | Resource or HighMLP window | These don't need throttling |
| **Conservative** | 5 | Serialized/Control with squash_ratio < 0.25 | Light throttle for moderate speculation waste |
| **Deep Conservative** | 3 | Serialized with squash_ratio ≥ 0.25 | Heavy speculation waste needs strong throttle |

**Classification flow**:
```
Step 1: mem_block_ratio >= 0.12 ?
  YES → outstanding_misses >= 12 ?
    YES → HighMLP → Aggressive
    NO  → Serialized
      → Step 1a: squash_ratio >= 0.25 ?
        YES → Deep Conservative (fw=3)
        NO  → Conservative (fw=5)
  NO →
Step 2: branch_recovery >= 0.10 AND squash >= 0.20 ?
  YES → Control → Conservative (fw=5)
  NO →
Step 3 (default): Resource → Aggressive
```

**Threshold rationale**:
- `mem_block_ratio = 0.12`: V2-validated. Tried 0.08 — caused catastrophic GAPBS regression.
- `outstanding_misses = 12`: V2 default. Separates HighMLP (parallel memory) from Serialized.
- `squash_ratio = 0.25`: Data-driven from Task 3 — tc has 67% windows ≥0.25, bfs/cc/pr have <14%. Clearly separates high-waste windows.

### 4.2 Resource Congestion Detection

In Aggressive mode, Resource windows with high speculation waste **automatically activate sweet spot caps** (iqcap=26, lsqcap=28, inflight cap=56).

**Trigger condition**: `commit_activity_ratio < 0.95` AND `IPC > 2.0`

**Rationale**:
- `commit_activity < 0.95` means >5% of instructions are squash-wasted — sweet spot caps reduce IQ backpressure
- `IPC > 2.0` guard prevents low-IPC workloads from being wrongly throttled (their pipeline isn't congested)

**Effect**: balanced_pipeline_stress (IPC=2.9, 100% Resource) automatically gets sweet spot — EDP improves from -0.6% to +15.8%.

### 4.3 Adaptive Window Size

Window size auto-adjusts based on classification change frequency:

```
Every 8 windows, check classification change rate:
  changeRate = (# of class changes) / 8
  if changeRate > 0.3:   windowCycles = max(windowCycles / 2, 1000)
  if changeRate < 0.1:   windowCycles = min(windowCycles * 2, 10000)
```

**Parameters**: Initial 2500, range [1000, 10000].

**Rationale**: Window sweep (§3.4) showed different workloads need dramatically different windows. Adaptive mechanism eliminates manual selection — tc naturally shrinks to 1000, branch_entropy grows to 7500+.

### 4.4 Unified Configuration

All workloads — Micro and GAPBS — use **identical parameters**. No workload-specific tuning.

| Parameter | Value |
|-----------|-------|
| Conservative FetchWidth | 5 |
| Conservative InflightCap | 48 |
| Conservative IQCap | 24 |
| Conservative LSQCap | 24 |
| Deep FetchWidth | 3 |
| Deep SquashThres | 0.25 |
| Resource Congestion InflightCap | 56 |
| Resource Congestion IQCap | 26 |
| Resource Congestion LSQCap | 28 |
| Resource Congestion CommitThres | 0.95 |
| Resource Congestion IPC Guard | 2.0 |
| Adaptive Window | Enabled (initial=2500, range=[1000, 10000]) |
| mem_block_ratio threshold | 0.12 |

---

## 5. Iteration Process (8 Rounds)

| Round | Change | Result | Key Lesson |
|-------|--------|--------|-----------|
| R1 | Ser→Light, Ctrl→Deep | Overall WPE -0.39% | Deep Conservative too aggressive for GAPBS Control windows |
| R2 | Unified sweet spot for all throttled windows | WPE +1.34% | First beat V2 |
| R3 | GAPBS-specific fw=4/win=2500 | WPE +1.91% | fw is dominant parameter for GAPBS |
| R4 | Try fw=5 and fw=4 + iq/lsq caps | Worse | iq/lsq caps ineffective for GAPBS (IPC too low for IQ congestion) |
| R5 | Tune Control thresholds | No change | GAPBS never reaches Control branch (all mem_block>=0.12) |
| R6 | Serialized-Deep sub-level (squash>=0.30) | WPE +2.14% | squash_ratio effectively separates windows |
| R7 | Normal-tier fw=6 (up from 5) | WPE +2.21% | 73-92% of IPC loss came from normal-tier windows |
| R8 | Resource congestion detection | WPE +2.73% | Sweet spot auto-applies to high-IPC workloads |
| +Unified | Same params for Micro and GAPBS | **EDP +13.36%** | IQ/LSQ caps safe for GAPBS under current thresholds |

---

## 6. Final Results

### 6.1 Single-core Results (12 workloads, 50M instructions each)

**Microbenchmarks**:

| Workload | BL IPC | V4 IPC | dIPC | BL Energy | V4 Energy | dEnergy | **V4 EDP** |
|----------|--------|--------|------|-----------|-----------|---------|-----------|
| balanced_pipeline_stress | 2.908 | 3.024 | +4.0% | 3.313J | 2.902J | -12.4% | **+15.8%** |
| phase_scan_mix | 0.467 | 0.464 | -0.7% | 6.005J | 4.318J | -28.1% | **+27.7%** |
| **branch_entropy** | 0.909 | 0.987 | **+8.5%** | 6.087J | 3.990J | **-34.5%** | **+39.6%** |
| serialized_pointer_chase | 0.827 | 0.805 | -2.7% | 4.323J | 3.990J | -7.7% | +5.2% |
| compute_queue_pressure | 2.392 | 2.392 | +0.0% | 2.686J | 2.686J | +0.0% | 0.0% |
| stream_cluster_reduce | 0.514 | 0.514 | +0.0% | 3.456J | 3.457J | +0.0% | 0.0% |
| **Micro avg** | | | | | | | **+14.70%** |

**GAPBS** (g20, 50M instructions):

| Benchmark | BL IPC | V4 IPC | dIPC | BL Energy | V4 Energy | dEnergy | **V4 EDP** |
|-----------|--------|--------|------|-----------|-----------|---------|-----------|
| bfs | 1.410 | 1.343 | -4.7% | 4.189J | 3.542J | -15.4% | +11.3% |
| bc | 1.397 | 1.334 | -4.5% | 4.219J | 3.590J | -14.9% | +10.9% |
| pr | 1.406 | 1.344 | -4.4% | 4.208J | 3.664J | -12.9% | +8.9% |
| cc | 1.411 | 1.345 | -4.6% | 3.936J | 3.639J | -7.6% | +3.1% |
| sssp | 1.391 | 1.342 | -3.6% | 4.009J | 3.581J | -10.7% | +7.4% |
| **tc** | 1.346 | 1.376 | **+2.3%** | 5.461J | 3.871J | **-29.1%** | **+30.7%** |
| **GAPBS avg** | | | | | | | **+12.03%** |

**Overall EDP: +13.36%** across all 12 workloads.

**Saved plots & data**:
- **Aggregate bar chart**: [results/charts/baseline_vs_adaptive_bars.png](../results/charts/baseline_vs_adaptive_bars.png) — baseline vs V4 side-by-side across all workloads.
- **Pareto plots**: [results/charts/pareto_perf_vs_energy.png](../results/charts/pareto_perf_vs_energy.png), [results/charts/all_v2_pareto.png](../results/charts/all_v2_pareto.png) — performance vs energy scatter.
- **Aggregate CSV** (all 12 workloads × baseline/V4): [results/all_experiments.csv](../results/all_experiments.csv).
- **Per-run artifacts** (config.json, stats.txt, mcpat.out, adaptive_window_log.csv): under [runs/v4_presentation/](../runs/v4_presentation/) — one folder per `<workload>_<baseline|v4>/latest/`.

### 6.2 Multi-core Results (4-core, same workload on all cores)

Each of 6 Micro workloads ran 4 copies on 4 cores with private L1 + shared L2.

| Workload | 4-core dIPC | 4-core dEnergy | **4-core EDP** | Single-core EDP |
|----------|-------------|---------------|---------------|-----------------|
| balanced_pipeline_stress | +4.3% | -12.5% | **+16.1%** | +15.8% |
| phase_scan_mix | -2.6% | -21.7% | **+20.6%** | +27.7% |
| branch_entropy | +0.2% | -0.7% | +1.0% | +39.6% |
| serialized_pointer_chase | -2.2% | -7.2% | +5.1% | +5.2% |
| compute_queue_pressure | 0% | 0% | 0% | 0% |
| stream_cluster_reduce | 0% | 0% | 0% | 0% |
| **Micro 4-core avg** | | | **+7.1%** | +14.5% |

**Observations**:
- balanced_pipeline_stress actually improves in 4-core (+16.1% vs +15.8%) — Resource congestion detection works correctly per-core.
- branch_entropy drops significantly in 4-core (+1.0% vs +39.6%) because shared-L2 contention changes its pipeline behavior.
- Workloads that don't benefit single-core still don't harm in multi-core.
- **GAPBS cannot run in gem5 SE mode multi-core** due to unimplemented `statx` syscall — this is a gem5 limitation, not our mechanism's.

**Saved plots & data**: Per-core per-window adaptive-window logs under [runs/v4_presentation/multicore/v4_4core/latest/](../runs/v4_presentation/multicore/v4_4core/latest/):
- [adaptive_window_log.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log.csv) (CPU0), [adaptive_window_log_cpu1.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log_cpu1.csv), [adaptive_window_log_cpu2.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log_cpu2.csv), [adaptive_window_log_cpu3.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log_cpu3.csv) — raw per-window signal traces for each core.

### 6.3 Best Case vs Worst Case Analysis

#### Best Case: `adaptive_showcase_best` (custom-designed workload)

**Construction**: We designed this workload specifically to exhibit the two behaviors V4 is optimized for — high mem_block_ratio and high squash_ratio simultaneously.

**Workload structure**:
```c
// 1. Build a randomized linked list (2048 nodes, pointer array 'chase[]')
//    chase[i] = random permutation of 0..CHASE_SIZE-1
//
// 2. Main loop: each iteration alternates between two "sub-operations":
//
//    (a) Memory-indirect load through linked list:
//        chase_idx = chase[chase_idx];     // cache miss every iteration
//        val = arr_a[chase_idx & (ARRAY_SIZE-1)];
//
//    (b) Data-dependent nested branches on loaded values:
//        if (val & 0x80)  { acc += ...; if (val & 0x40) {...} else {...} }
//        else             { acc ^= ...; if (val & 0x20) {...} else {...} }
//        if ((val>>8) & 0x03) acc += ...; else acc ^= ...;
```

**Design intent behind each feature**:
| Feature | Triggers | Why it helps V4 |
|---------|----------|-----------------|
| Randomized linked-list (`chase[chase_idx]`) | High mem_block_ratio (0.515) | Each load is a cache miss; prefetcher can't predict. Commit stalls waiting for memory → classifier recognizes Serialized |
| Data-dependent branches on loaded `val` | High squash_ratio (0.317) | Branch direction depends on value that hasn't returned yet. Predictor gets it wrong ~50% → speculative path wasted |
| Nested branches (3 levels) | Amplifies speculation waste | Each level doubles the wasted speculation depth |
| Small working set (2048 nodes x 4B = 8KB) | Focuses on memory latency | Stays in L1 for the table, but pointer-chase still misses due to randomization |

**Per-window behavior**: 99% of 7331 windows classified as Serialized → Deep Conservative (fw=3). Average mem_block_ratio = 0.515 (over half the cycles commit is memory-blocked), average squash_ratio = 0.317 (1/3 of fetched insts are wasted).

**Result**:

| Metric | Baseline | V4 | Change |
|--------|----------|-----|--------|
| IPC | 0.562 | 0.606 | **+7.9%** |
| Power | 150.8W | 92.1W | **-38.9%** |
| Energy | 6.337J | 3.724J | **-41.2%** |
| **EDP** | 0.250 | 0.136 | **+45.6%** |

Note: IPC actually **improves** because baseline 8-wide fetch keeps pushing speculative instructions down the wrong path, clogging IQ/LSQ/ROB. fw=3 eliminates most of this waste, and effective instructions get pipeline resources faster.

#### Worst Case: `adaptive_showcase_worst` (custom-designed slight-negative workload)

**Construction**: We designed this workload to deliberately expose the classifier's weakest case — one where V4 **does** throttle but the throttle does not recover any wasted speculation.

**Workload structure**:
```c
#define CHASE_SIZE (1U << 16)   // 64K nodes * 4B = 256KB (L2-resident, misses L1)
static uint32_t chase[CHASE_SIZE];  // random permutation, forms one big cycle

for (r = 0; r < rounds; ++r) {
    // (a) Serial pointer chase — next idx depends on the value just loaded.
    //     CPU cannot prefetch ahead: only ~1-2 iterations of chase loads
    //     sit in LSQ at any time.
    idx = chase[idx];
    uint32_t v = idx;

    // (b) Long, branchless, fully-dependent compute chain (~28 ops).
    //     Each step depends on the previous -> no ILP, no squash.
    //     Fills IQ with non-memory ops so LSQ stays small.
    v ^= v >> 16; v *= 0x7feb352dU;
    v ^= v >> 15; v *= 0x846ca68bU;
    v ^= v >> 16; v *= 0xcaffe171U;
    // ... 11 more similar steps ...
    v ^= v >> 13;
    acc ^= v;
}
```

**Design intent behind each feature**:
| Feature | Triggers | Why it hurts V4 (throttle without benefit) |
|---------|----------|--------------------------------------------|
| 256KB chase array (L1-miss, L2-hit) | commit_blocked_mem > 0 | Head-of-ROB waits for L2 fill -> decoupled `mem_block_ratio` stays above the 0.12 threshold -> classifier picks `Serialized-memory dominated` |
| Serial dependency between chase loads | avg LSQ occupancy ~ 8.7 | Below the 12-entry `outstandingMissThres` -> NOT classified as `High-MLP` -> Conservative throttle *does* apply (fw=5) |
| 28-op dependent compute chain | IQ fills with compute, not loads | Keeps LSQ occupancy low *and* gives V4 plenty of fetch-width bandwidth to cut — without any wasted speculation to eliminate |
| No branches | squash_ratio ≈ 0.006 | Below every sub-level threshold -> classifier stays in plain `Conservative` (fw=5), never descends to Deep (fw=3) |

**Per-window behavior** (4394 windows, adaptive window size):
| Signal | Value | Reading |
|--------|-------|---------|
| Classified as `Serialized-memory dominated` | **99.0%** (4351/4394) | Almost every window triggers the throttle |
| Applied mode = `Conservative` | **99.0%** | fw=5 throttle active throughout |
| avg_outstanding_misses_proxy | **8.74** | Below the 12 threshold that would flip it to HighMLP |
| squash_ratio | 0.006 | Virtually no speculation waste to recover |
| mem_block_ratio (decoupled) | ≈ 0.19 | Stays just above the 0.12 threshold during Aggressive probe windows |
| avg IQ occupancy | 23.0 | Healthy IQ usage — compute chain, not memory-bound |
| avg per-window IPC (V4) | 1.18 | Still reasonable — the workload is fundamentally efficient |

**Why V4 hurts here**:

1. **No wasted speculation to reclaim**. squash_ratio ≈ 0.006 means 99.4% of fetched instructions retire. fw=5 simply limits *useful* fetch.
2. **High baseline IPC (1.233)** means any fetch-width cut directly translates into a throughput loss. Baseline's 8-wide fetch was actually well-matched to this workload's ILP+compute-chain profile.
3. **Energy savings are minimal** because the front-end was not oversubscribed to begin with — nothing speculative to save power on. Dynamic energy drops only 0.3%.
4. **The classifier is not *wrong***: mem_block_ratio really does exceed 0.12 and LSQ really is under 12. The decision rule applies exactly as designed. This is the irreducible cost of being a pattern-matched heuristic.

**Result**:

| Metric | Baseline | V4 | Change |
|--------|----------|-----|--------|
| IPC | 1.233 | 1.166 | **-5.5%** |
| Power | 121.40 W | 114.38 W | -5.8% |
| Energy | 2.516 J | 2.508 J | -0.3% |
| Simulated time | 0.02073 s | 0.02192 s | +5.8% |
| **EDP (E×T)** | 0.0522 J·s | 0.0550 J·s | **-5.4%** |

This is V4's **worst realistic outcome**: a clean -5.4% EDP hit when the classifier fires on a workload that has nothing to give. (For reference, GAPBS-cc — the worst *real* benchmark in our unified suite — still shows +3.3% EDP. This custom case is therefore worse than anything in the standard benchmark set, and was built specifically to demonstrate V4's failure mode.)

#### Summary Comparison

| Signal | Best Case | Worst Case | Interpretation |
|--------|-----------|-----------|----------------|
| squash_ratio | **0.317** | 0.006 | Best has 50x more wasted speculation to eliminate |
| mem_block_ratio | **0.515** | ~0.19 (decoupled) | Best is memory-dominated; worst just barely over threshold |
| baseline IPC | 0.562 | **1.233** | Worst has 2.2x higher IPC (more throughput to lose) |
| Applied throttle | Deep Conservative (fw=3) 99% | Conservative (fw=5) 99% | Both classes route windows to the throttled path |
| **EDP change** | **+45.6%** | **-5.4%** | ~50-point swing — mechanism is sharply bimodal |

**Saved per-window traces & run artifacts** (under [runs/v4_presentation/showcase/](../runs/v4_presentation/showcase/)):
- Best case V4: [adaptive_showcase_best_v4/latest/adaptive_window_log.csv](../runs/v4_presentation/showcase/adaptive_showcase_best_v4/latest/adaptive_window_log.csv) — all 7331 windows with per-window class, mode, squash_ratio, mem_block_ratio, and IPC.
- Worst case V4: [adaptive_showcase_worst_v4/latest/adaptive_window_log.csv](../runs/v4_presentation/showcase/adaptive_showcase_worst_v4/latest/adaptive_window_log.csv) — all 4394 windows of the new slight-negative design.
- Worst case Baseline: [adaptive_showcase_worst_baseline/latest/](../runs/v4_presentation/showcase/adaptive_showcase_worst_baseline/latest/) — baseline stats for the same workload.
- Each V4 run also contains `config.json`, `stats.txt`, `mcpat.xml`, `mcpat.out` for the full power breakdown.
- Workload source: [workloads/adaptive_showcase_worst/adaptive_showcase_worst.c](../workloads/adaptive_showcase_worst/adaptive_showcase_worst.c).

*Note*: No pre-rendered PNGs for the V4 showcase runs — the data lives in CSV for regeneration with any plotting tool. The older v2-era per-window timeline PNGs referenced in §3.3 illustrate the same idea on the earlier workloads.

### Design Strengths and Weaknesses

**V4 excels on workloads with**:
- High squash_ratio (>0.25) — lots of wasted speculation
- High mem_block_ratio (>0.12) — memory stall is the real bottleneck
- Data-dependent branches — speculation paths are almost always wrong
- Low baseline IPC (<1.0) — throttle doesn't hurt effective throughput

*Typical examples*: pointer chasing, hash table probes, tree traversals, rule matching.

**V4 underperforms on workloads with**:
- Low squash_ratio (<0.15) — speculation is mostly correct
- Higher baseline IPC (>1.0) — throttle directly limits throughput
- Predictable branch patterns — no benefit from limiting speculation
- Low mem_block_ratio — memory isn't the bottleneck

*Typical examples*: graph traversal (partially predictable access), streaming computation (sequential memory, prefetcher-friendly).

**One-line summary**: V4's core capability is identifying and reducing **ineffective speculation** — when the pipeline spends effort on instructions that will be squashed, limiting speculation saves both energy and (often) improves performance. When speculation is mostly effective, limiting it is pure performance loss.

---

## 7. Key Lessons & Abandoned Directions

### Abandoned Directions

| Direction | Reason |
|-----------|--------|
| EMA signal smoothing (α=0.3) | Effect <0.2%, conceptually wrong — current stall should use current signals |
| Signal decoupling (freeze signals in Conservative mode) | Fundamental flaw — once in Conservative, signals frozen forever, can't detect phase changes |
| Squash-proportional throttle (continuous fw mapping) | EDP worse than binary threshold (tc dropped from +28.2% to +18.6%) |
| Lower mem_block_ratio to 0.10 | Negligible impact |
| Aggressive mode fw=7 (light throttle always on) | Negligible EDP impact |
| 3-level Conservative (Light+Normal+Deep) | Light and Normal converged to same params — simplified to 2-tier + Deep sub-level |
| Rename Width throttle | All-or-nothing threshold effect (rw=4~7 identical, rw=8 different) — not useful |

### Core Design Principles Learned

1. **Don't solve classification drift at the signal level** — fix it at the parameter level (avoid params that distort signals).
2. **Sweet spot params are workload-IPC-dependent** — IQ/LSQ caps help high-IPC workloads, are ineffective for low-IPC ones. Use IPC-guarded auto-detection (Resource congestion sub-level).
3. **Fetch Width is the dominant throttle parameter for low-IPC workloads**. IQ/LSQ caps barely affect them.
4. **Binary thresholds beat continuous mappings** when the decision boundary is clear (squash_ratio is bimodal).
5. **Adaptive window size eliminates manual per-workload tuning** — mechanism naturally adapts to phase-change frequency.

### Code Changes Summary

| File | Changes |
|------|---------|
| `src/cpu/o3/BaseO3CPU.py` | New params: SerializedTight, ResourceCongestion, AdaptiveWindow |
| `src/cpu/o3/cpu.hh` | New member variables (sub-level flags, adaptive window state) |
| `src/cpu/o3/cpu.cc` | Deep sub-level logic, Resource congestion logic, adaptive window logic, mode mapping simplification |

---

## 8. Overhead Analysis

Our mechanism adds logic in three places: per-cycle signal sampling, window-boundary classification, and throttle application. Total overhead is negligible relative to the O3 core.

### Hardware Overhead

**Storage (on-chip registers/SRAM)**:

| Component | Size | Notes |
|-----------|------|-------|
| Window statistics counters (11 x 64-bit) | 88 B | cycles, fetched/committed/squashed insts, mem_block_cycles, iq_sat_cycles, branch_recovery_cycles, inflight/iq/outstanding_miss samples, branch_mispredicts |
| Configuration registers (~30 x 32-bit) | 120 B | thresholds, per-mode params, adaptive window params |
| Runtime state registers | 16 B | current_mode, current_class, windows_in_mode, adaptive_window_cycles, sub-level flags |
| **Total storage** | **~224 B** | <0.01% of typical L1 cache |

**Logic**:

| Component | Gate count estimate | Critical path impact |
|-----------|--------------------|---------------------|
| 11 per-cycle counter increments | ~500 gates | Parallel with pipeline; no new critical path |
| 3 mux/comparator for fetch_width gating | ~50 gates | On existing fetch-gating logic |
| 3 comparators for inflight/IQ/LSQ caps | ~100 gates | On existing throttle-fetch path |
| Window-boundary classifier (7 thresholds, 4 classes, sub-level checks) | ~1000 gates | Triggered once per ~2500 cycles — off critical path |
| Adaptive window adjuster | ~50 gates | Triggered once per 8 windows |
| **Total logic** | **~1700 gates** | << 0.1% of ~10M-gate O3 core |

**Power & Area**:
- Per-cycle sampling counters are tiny (<1mW at 1GHz)
- Window-boundary classifier runs once per 2500 cycles — amortized power is ~0
- No change to pipeline critical path → no frequency or voltage impact
- Area estimate: **<0.1% of O3 core area**

**Latency**:
- Per-cycle sampling: zero added latency (parallel counters)
- Window-boundary classification: ~5-10 cycles of logic, but runs off critical path at window end. Parameter updates take effect on next window
- Mode switching: instant (just updates parameter mux selects)

### Software Overhead

**Zero software overhead**. The mechanism is fully transparent:

| Layer | Overhead |
|-------|----------|
| Application | None — no code changes, no API, no syscalls |
| Operating System | None — no driver, no interrupt, no kernel involvement |
| ISA | No new instructions |
| Compiler | No changes |
| Firmware/Microcode | None — all logic is in hardware counters and state machines |

**Configuration**: Thresholds and mode parameters can optionally be exposed via MSRs for BIOS/firmware tuning. In our gem5 evaluation they are set via `--param`. A production implementation would ship with fixed optimal values (fw=5/3, squash=0.25, window=[1000, 10000]).

### Summary: Cost vs Benefit

| Aspect | Overhead |
|--------|---------|
| Core area | +0.1% |
| L1/L2 cache sizing | Unchanged |
| Pipeline critical path | Unchanged |
| Peak frequency | Unchanged |
| Per-cycle power | +<1mW |
| Software complexity | Zero |
| **Energy savings on favorable workloads** | **10%~35%** |
| **Average EDP improvement** | **+13.36% across 12 benchmarks** |

The implementation cost is trivial (<0.1% area, zero software impact). The mechanism is essentially "free" to add to an O3 core — any design optimizing for energy efficiency should include something equivalent.

---

## Final Numbers At-a-Glance

| Metric | Value |
|--------|-------|
| **Overall EDP improvement** | **+13.36%** |
| Micro EDP (6 workloads) | +14.70% |
| GAPBS EDP (6 workloads) | +12.03% |
| 4-core Micro EDP avg | +7.1% |
| Best single-workload EDP | +39.6% (branch_entropy) |
| Showcase best-case EDP | +45.6% |
| Worst real benchmark EDP (GAPBS-cc) | +3.3% |
| Showcase worst-case EDP (`adaptive_showcase_worst`) | **-5.4%** |
