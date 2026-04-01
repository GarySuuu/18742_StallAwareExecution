# Adaptive Mechanism v1 (4-class classification + 2-mode execution)

## Scope and goals

This is a first runnable version of the adaptive mechanism for the project:

- **Detection / Classification**: 4 stall classes (rule-based)
- **Execution**: 2 runtime modes (`aggressive`, `conservative`)
- **Baseline compatibility**: baseline script and baseline behavior stay intact

`baseline` and `adaptive` run paths are isolated:

- Baseline: `scripts/run_baseline.sh` -> `runs/baseline/...`
- Adaptive v1: `scripts/run_adaptive.sh` -> `runs/adaptive/v1/...`

## What changed vs baseline

### Files modified

- `src/cpu/o3/BaseO3CPU.py`
- `src/cpu/o3/cpu.hh`
- `src/cpu/o3/cpu.cc`
- `src/cpu/o3/fetch.cc`
- `src/cpu/o3/commit.hh`
- `src/cpu/o3/commit.cc`
- `scripts/run_adaptive.sh` (new)
- `docs/adaptive_mechanism_v1.md` (new)

### Module-level changes

- **New adaptive params** in `BaseO3CPU`:
  - enable/disable switch (`enableStallAdaptive`)
  - window size (`adaptiveWindowCycles`)
  - hysteresis + minimum mode hold windows
  - conservative controls (`adaptiveConservativeFetchWidth`, `adaptiveConservativeInflightCap`)
  - rule thresholds
- **CPU-level adaptive controller** in `cpu.cc/cpu.hh`:
  - per-window counters and derived metrics
  - rule-based 4-class classifier
  - class->mode mapping
  - hysteresis-controlled mode transitions (window boundaries only)
  - CSV logging (`adaptive_window_log.csv`)
- **Execution-stage hooks**:
  - `fetch.cc`: fetch-width control + conservative-mode fetch throttling + fetched-inst counting
  - `commit.cc`: committed/squashed/branch-mispredict counting

No baseline command was changed; baseline remains static unless adaptive params are explicitly enabled.

## Classification stage (Detection/Classification)

## Sampling model

- Fixed window: `adaptiveWindowCycles` (default 5000 cycles)
- Window update point: CPU tick at window boundary only

### Collected counters/signals

Implemented in `CPU::adaptiveRecordCycleSignals()` plus fetch/commit hooks:

- `fetched_insts`: from `Fetch::fetch()` instruction enqueue path
- `committed_insts`: from commit success path
- `squashed_insts`: from commit retiring squashed head
- `branch_mispredict_events`: from commit mispredict squash handling
- `commit_blocked_mem_cycles` (proxy):
  - ROB non-empty + ROB head not ready + LSQ/memory backpressure
- `avg_outstanding_misses` (proxy):
  - per-cycle LQ occupancy average
- `iq occupancy`: per-cycle IQ occupancy average
- `iq saturation`: fraction of cycles with IQ full
- `branch_recovery_cycles` (proxy):
  - cycles with commit in `ROBSquashing`
- `avg inflight insts` (proxy):
  - per-cycle ROB occupancy average

### Proxy notes

The following are **currently proxy-based**, not exact microarchitectural ground-truth signals:

- `avg_outstanding_misses` -> uses LQ occupancy proxy
- `commit_blocked_mem_cycles` -> uses ROB-head-not-ready + memory-backpressure heuristic
- `branch_recovery_cycles` -> uses commit squashing-state cycles
- `avg inflight insts` -> uses ROB occupancy proxy

These are adequate for v1 bring-up and debug; refine in later phase if needed.

### Derived metrics and rules

Per-window derived metrics:

- `mem_block_ratio = commit_blocked_mem_cycles / cycles`
- `avg_outstanding_misses_proxy = outstandingMissSamples / cycles`
- `branch_recovery_ratio = branch_recovery_cycles / cycles`
- `squash_ratio = squashed_insts / max(fetched_insts, 1)`
- `iq_saturation_ratio = iq_saturation_cycles / cycles`
- `commit_activity_ratio = committed_insts / max(fetched_insts, 1)`

Rule-based class decision order:

1. If `mem_block_ratio >= mem_block_thres`:
   - and `avg_outstanding_misses_proxy >= outstanding_miss_thres` -> **High-MLP memory dominated**
   - else -> **Serialized-memory dominated**
2. Else if `branch_recovery_ratio >= branch_recovery_thres` and `squash_ratio >= squash_thres`:
   - -> **Control dominated**
3. Else if `iq_saturation_ratio >= iq_sat_thres` and `commit_activity_ratio >= commit_activity_thres`:
   - -> **Resource-contention / compute dominated**
4. Else:
   - -> **Resource-contention / compute dominated** (v1 default fallback)

## Execution stage (2 modes only)

### Modes

- **Aggressive mode**:
  - baseline-like O3 behavior
  - no extra adaptive fetch/inflight restrictions
- **Conservative mode**:
  - fetch throttling enabled
  - soft in-flight cap via ROB occupancy proxy

### Class to mode mapping

- Serialized-memory dominated -> **conservative**
- High-MLP memory dominated -> **aggressive**
- Control dominated -> **conservative**
- Resource-contention / compute dominated -> **aggressive**

### Mode switch policy

- Switch/check only on **window boundaries**
- Hysteresis: class must persist for `adaptiveSwitchHysteresis` windows
- Minimum hold: current mode must be held for at least `adaptiveMinModeWindows`

## Observable outputs for validation

Each adaptive run writes:

- `run.log`
- `config.ini` / `config.json`
- `stats.txt`
- `adaptive_window_log.csv` (window-level metrics + class + target/applied mode + switch flag)
- `adaptive_config_summary.md` (auto-generated run/parameter summary)

Archive/layout:

- Active outdir: user-provided argument
- Archived copy: `runs/adaptive/v1/archive/<timestamp>/`
- Latest symlink: `runs/adaptive/v1/latest`

## Fair-comparison constraints

For baseline vs adaptive comparison, keep fixed:

- ISA, binary/workload, input, maxinsts
- CPU type (`DerivO3CPU`), core count
- cache hierarchy and memory size
- gem5 build, compiler/toolchain environment

Only adaptive knobs should vary when evaluating mechanism impact:

- conservative fetch width
- conservative in-flight cap
- window size
- classification thresholds
- hysteresis / min-mode-hold parameters

## Current limitations (do not over-interpret yet)

- Signals use proxies for first implementation
- Conservative mode currently controls only fetch throttling + soft in-flight cap
- No learning-based classifier, no multi-level aggressiveness, no deep memory hierarchy redesign
