# Adaptive O3 CPU -- Parameter Taxonomy

This document categorizes all 39 adaptive parameters defined in
`src/cpu/o3/BaseO3CPU.py` (lines 196-330) by the pipeline stage they affect.

## Data-Flow Summary

```
BaseO3CPU.py             cpu.cc                         fetch.cc / cpu.cc
(parameter defs)    (classification + mode select)    (per-stage throttle)
     |                        |                              |
     v                        v                              v
  Params  -->  adaptiveClassifyWindow()  -->  adaptiveFetchWidth()         [Frontend]
               adaptiveMapClassToMode()       adaptiveShouldThrottleFetch() [Frontend]
               adaptiveMaybeSwitch()          adaptiveRenameWidth()         [Backend]
                                              adaptiveDispatchWidth()       [Backend]
                                              adaptiveEffectiveInflightCap()[Backend]
```

---

## A. Frontend Parameters (8)

These parameters affect the fetch stage. They are consumed in `fetch.cc` via
`cpu->adaptiveFetchWidth()` (cpu.cc:572) and
`cpu->adaptiveShouldThrottleFetch()` (cpu.cc:626).

| # | Parameter | Type | Default | Description | Code Path |
|---|-----------|------|---------|-------------|-----------|
| 1 | `adaptiveConservativeFetchWidth` | Unsigned | 2 | Fetch width in conservative mode | `adaptiveFetchWidth()` cpu.cc:592 |
| 2 | `adaptiveSerializedFetchWidth` | Unsigned | 2 | Fetch width for Serialized class profile | `adaptiveFetchWidth()` cpu.cc:581 |
| 3 | `adaptiveHighMLPFetchWidth` | Unsigned | 0 | Fetch width for HighMLP class (0=baseline) | `adaptiveFetchWidth()` cpu.cc:583 |
| 4 | `adaptiveControlFetchWidth` | Unsigned | 2 | Fetch width for Control class profile | `adaptiveFetchWidth()` cpu.cc:585 |
| 5 | `adaptiveResourceFetchWidth` | Unsigned | 0 | Fetch width for Resource class (0=baseline) | `adaptiveFetchWidth()` cpu.cc:590 |
| 6 | `adaptiveResourceTightFetchWidth` | Unsigned | 2 | Fetch width for Resource-tight sub-profile | `adaptiveFetchWidth()` cpu.cc:588 |
| 7 | `adaptiveConservativeIQCap` | Unsigned | 0 | IQ occupancy cap (blocks fetch if hit; 0=off) | `adaptiveShouldThrottleFetch()` cpu.cc:639 |
| 8 | `adaptiveConservativeLSQCap` | Unsigned | 0 | LSQ occupancy cap (blocks fetch if hit; 0=off) | `adaptiveShouldThrottleFetch()` cpu.cc:645 |

**How they work:**
- Fetch width params: `adaptiveFetchWidth()` returns the per-cycle fetch limit based on the current mode. Called in `fetch.cc:1187` to cap `numInst` in the fetch loop.
- IQ/LSQ caps: `adaptiveShouldThrottleFetch()` returns true if ROB, IQ, or LSQ occupancy exceeds the configured cap. Checked at `fetch.cc:1092` -- if true, fetch is completely stalled for that cycle.

---

## B. Backend Parameters (19)

These parameters affect inflight instruction cap (ROB occupancy limit for
fetch throttling), rename width, and dispatch width.

### B1. Inflight Cap (applied via `adaptiveEffectiveInflightCap()` -> `adaptiveShouldThrottleFetch()`)

| # | Parameter | Type | Default | Description |
|---|-----------|------|---------|-------------|
| 9 | `adaptiveConservativeInflightCap` | Unsigned | 96 | ROB cap in conservative mode |
| 10 | `adaptiveSerializedInflightCap` | Unsigned | 64 | ROB cap for Serialized profile |
| 11 | `adaptiveHighMLPInflightCap` | Unsigned | 0 | ROB cap for HighMLP (0=no limit) |
| 12 | `adaptiveControlInflightCap` | Unsigned | 96 | ROB cap for Control profile |
| 13 | `adaptiveResourceInflightCap` | Unsigned | 96 | ROB cap for Resource profile |
| 14 | `adaptiveResourceTightInflightCap` | Unsigned | 72 | ROB cap for Resource-tight sub-profile |

### B2. Rename Width (applied via `adaptiveRenameWidth()` in cpu.cc:600)

| # | Parameter | Type | Default | Description |
|---|-----------|------|---------|-------------|
| 15 | `adaptiveConservativeRenameWidth` | Unsigned | 0 | Rename width limit in conservative (0=baseline) |
| 16 | `adaptiveSerializedRenameWidth` | Unsigned | 4 | Rename width for Serialized profile |
| 17 | `adaptiveHighMLPRenameWidth` | Unsigned | 0 | Rename width for HighMLP (0=baseline) |
| 18 | `adaptiveControlRenameWidth` | Unsigned | 4 | Rename width for Control profile |
| 19 | `adaptiveResourceRenameWidth` | Unsigned | 5 | Rename width for Resource profile |
| 20 | `adaptiveResourceTightRenameWidth` | Unsigned | 4 | Rename width for Resource-tight sub-profile |

### B3. Dispatch Width (applied via `adaptiveDispatchWidth()` in cpu.cc:613)

| # | Parameter | Type | Default | Description |
|---|-----------|------|---------|-------------|
| 21 | `adaptiveConservativeDispatchWidth` | Unsigned | 0 | Dispatch width limit in conservative (0=baseline) |
| 22 | `adaptiveSerializedDispatchWidth` | Unsigned | 4 | Dispatch width for Serialized profile |
| 23 | `adaptiveHighMLPDispatchWidth` | Unsigned | 0 | Dispatch width for HighMLP (0=baseline) |
| 24 | `adaptiveControlDispatchWidth` | Unsigned | 4 | Dispatch width for Control profile |
| 25 | `adaptiveResourceDispatchWidth` | Unsigned | 5 | Dispatch width for Resource profile |
| 26 | `adaptiveResourceTightDispatchWidth` | Unsigned | 4 | Dispatch width for Resource-tight sub-profile |

**How they work:**
- Inflight cap: ROB occupancy is checked in `adaptiveShouldThrottleFetch()` (cpu.cc:634). If `rob_occupancy >= inflight_cap`, fetch stalls.
- Rename width: `adaptiveRenameWidth(base_width)` returns `min(base_width, limit)`. Called in the rename stage.
- Dispatch width: `adaptiveDispatchWidth(base_width)` returns `min(base_width, limit)`. Called in the IEW stage.

---

## C. Classification / Policy Parameters (12)

These parameters control the classifier decision tree
(`adaptiveClassifyWindow()` at cpu.cc:724) and the mode-switch policy
(`adaptiveMaybeSwitch()` at cpu.cc:877).

### C1. Master Enable and Mode Selection

| # | Parameter | Type | Default | Description |
|---|-----------|------|---------|-------------|
| 27 | `enableStallAdaptive` | Bool | False | Master enable for the adaptive controller |
| 28 | `adaptiveUseClassProfiles` | Bool | False | If true: per-class profiles; if false: legacy 2-mode |

### C2. Switching Policy

| # | Parameter | Type | Default | Description |
|---|-----------|------|---------|-------------|
| 29 | `adaptiveSwitchHysteresis` | Unsigned | 2 | Consecutive windows with same class before switch |
| 30 | `adaptiveMinModeWindows` | Unsigned | 2 | Minimum windows to hold current mode |

### C3. Classification Thresholds (used in `adaptiveClassifyWindow()` cpu.cc:724-767)

| # | Parameter | Type | Default | Metric | Decision |
|---|-----------|------|---------|--------|----------|
| 31 | `adaptiveMemBlockRatioThres` | Float | 0.15 | `commit_blocked_mem_cycles / cycles` | If >= threshold -> memory-dominated branch |
| 32 | `adaptiveOutstandingMissThres` | Float | 8.0 | `outstanding_miss_samples / cycles` | If >= threshold -> HighMLP; else -> Serialized |
| 33 | `adaptiveHighMLPMaxInflightProxy` | Float | 32.0 | `inflight_inst_samples / cycles` | Guard: must be <= threshold for HighMLP (0=disable) |
| 34 | `adaptiveBranchRecoveryRatioThres` | Float | 0.10 | `branch_recovery_cycles / cycles` | If >= threshold AND squash >= threshold -> Control |
| 35 | `adaptiveSquashRatioThres` | Float | 0.20 | `squashed_insts / fetched_insts` | Combined with branch recovery for Control class |
| 36 | `adaptiveIQSaturationRatioThres` | Float | 0.10 | `iq_saturation_cycles / cycles` | If >= threshold AND commit activity >= threshold -> Resource |
| 37 | `adaptiveCommitActivityRatioThres` | Float | 0.20 | `committed_insts / fetched_insts` | Combined with IQ saturation for Resource class |

### C4. Resource-Tight Sub-Profile Triggers

| # | Parameter | Type | Default | Description |
|---|-----------|------|---------|-------------|
| 38 | `adaptiveResourceTightMaxInflightProxy` | Float | 24.0 | If Resource class and avg inflight <= this -> use tight sub-profile (0=off) |
| 39 | `adaptiveResourceTightMinSquashRatio` | Float | 0.15 | If Resource class and squash ratio >= this -> use tight sub-profile (0=off) |

**Classification Decision Tree** (cpu.cc:742-767):
```
1. mem_block_ratio >= MemBlockRatioThres ?
   YES -> outstanding_misses >= OutstandingMissThres ?
          YES -> inflight_proxy <= HighMLPMaxInflightProxy ?
                 YES -> HighMLP
                 NO  -> Resource (inflight guard fallback)
          NO  -> Serialized
   NO  ->
2. branch_recovery_ratio >= BranchRecoveryRatioThres AND squash_ratio >= SquashRatioThres ?
   YES -> Control
   NO  ->
3. iq_saturation_ratio >= IQSaturationRatioThres AND commit_activity_ratio >= CommitActivityRatioThres ?
   YES -> Resource
   NO  -> Resource (default)
```

**Legacy 2-Mode Mapping** (cpu.cc:776-784):
- Serialized + Control -> Conservative
- HighMLP + Resource -> Aggressive

---

## D. Window / Sampling Parameters (1)

| # | Parameter | Type | Default | Description | Code Path |
|---|-----------|------|---------|-------------|-----------|
| 40 | `adaptiveWindowCycles` | Unsigned | 5000 | Sampling window size in cycles | `adaptiveAdvanceWindow()` in cpu.cc |

Note: `adaptiveWindowCycles` is listed as the 40th parameter here because the
total count includes `enableStallAdaptive` which is the master enable but was
counted in section C1. The original count of 39 in BaseO3CPU.py is correct
(lines 196-330).

---

## Summary by Pipeline Stage

```
                     FRONTEND                          BACKEND
              +-----------------------+    +-------------------------------+
              | Fetch Width (6 params)|    | Inflight Cap (6 params)       |
  Instruction | IQ Cap    (1 param)   |    | Rename Width (6 params)       |
  Stream  --> | LSQ Cap   (1 param)   |--->| Dispatch Width (6 params)     |
              +-----------------------+    +-------------------------------+
                        ^                              ^
                        |                              |
              +---------------------------------------------------+
              |       Classification / Policy (12 params)          |
              |  Thresholds (7) + Switching (2) + Enable (2)       |
              |  + Resource-tight triggers (2)                     |
              +---------------------------------------------------+
                        ^
                        |
              +-------------------+
              | Window (1 param)  |
              +-------------------+
```

## V2 Script Defaults vs Code Defaults

Some parameters are overridden by the run scripts (`scripts/run_adaptive.sh`):

| Parameter | Code Default | V2 Script Default |
|-----------|-------------|-------------------|
| `adaptiveSwitchHysteresis` | 2 | 1 |
| `adaptiveMinModeWindows` | 2 | 1 |
| `adaptiveMemBlockRatioThres` | 0.15 | 0.12 |
| `adaptiveOutstandingMissThres` | 8.0 | 12 |
