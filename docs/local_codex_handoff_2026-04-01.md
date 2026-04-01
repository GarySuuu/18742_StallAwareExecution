# Local Codex Handoff (2026-04-01)

## Goal

Continue the adaptive-controller work on a local machine because the server build/run workload was too heavy.

The immediate goal is:

1. build `build/ARM/gem5.opt` locally
2. validate that legacy `v2` behavior still works
3. validate the new per-class execution-profile path
4. compare the new path against current `v2`

## Current State

The repository already contains the earlier adaptive-controller work (`v1` / `v2`) plus a new, unvalidated batch of changes for class-specific execution profiles.

Important: these latest changes were **edited and syntax-checked**, but they were **not fully built or runtime-tested yet**. The server build was interrupted because the machine became unstable, not because we saw a confirmed adaptive-specific compile failure.

## Files Touched In This Batch

Core implementation:

- `src/cpu/o3/BaseO3CPU.py`
- `src/cpu/o3/cpu.hh`
- `src/cpu/o3/cpu.cc`

Script / observability support:

- `scripts/run_adaptive.sh`
- `scripts/run_adaptive_unique.sh`

## What Was Added

### 1. Per-class execution profile support

The new code adds a gated path controlled by:

- `adaptiveUseClassProfiles`

When `False`:

- behavior should remain the legacy `v2` style:
  - serialized/control -> conservative
  - high-MLP/resource -> aggressive

When `True`:

- class decisions map to distinct applied modes:
  - `SerializedProfile`
  - `HighMLPProfile`
  - `ControlProfile`
  - `ResourceProfile`

### 2. New profile parameters

Added per-class controls for:

- fetch width
- inflight cap
- rename width
- dispatch width

Specifically:

- `adaptiveSerializedFetchWidth`
- `adaptiveSerializedInflightCap`
- `adaptiveSerializedRenameWidth`
- `adaptiveSerializedDispatchWidth`
- `adaptiveHighMLPFetchWidth`
- `adaptiveHighMLPInflightCap`
- `adaptiveHighMLPRenameWidth`
- `adaptiveHighMLPDispatchWidth`
- `adaptiveControlFetchWidth`
- `adaptiveControlInflightCap`
- `adaptiveControlRenameWidth`
- `adaptiveControlDispatchWidth`
- `adaptiveResourceFetchWidth`
- `adaptiveResourceInflightCap`
- `adaptiveResourceRenameWidth`
- `adaptiveResourceDispatchWidth`

### 3. Runtime behavior changes

The controller now has helper functions to compute effective limits from the current adaptive mode:

- fetch width
- inflight cap
- rename width
- dispatch width

The new profile modes are also emitted in `adaptive_window_log.csv` via `target_mode` / `applied_mode`.

### 4. Script-side summary support

`run_adaptive.sh` and `run_adaptive_unique.sh` were updated so the generated summaries can show the new profile-related parameters.

## What Was Checked Already

These checks passed:

- `python3 -m py_compile src/cpu/o3/BaseO3CPU.py`
- `bash -n scripts/run_adaptive.sh`
- `bash -n scripts/run_adaptive_unique.sh`

I also checked parameter-name consistency across:

- `BaseO3CPU.py`
- `cpu.hh`
- `cpu.cc`
- the two adaptive run scripts

## What Was NOT Finished

- full `scons` build did not finish on the server
- no smoke run was completed for the new profile path
- no baseline / legacy-v2 / profile-v2 performance comparison was completed

## Important Implementation Notes

### Legacy compatibility intent

The latest code is intentionally designed so that:

- `adaptiveUseClassProfiles=False` should preserve legacy behavior
- `adaptiveUseClassProfiles=True` should activate the new profile logic

### Known design limitation still present

`adaptiveConservativeIQCap` and `adaptiveConservativeLSQCap` are still legacy shared knobs. The latest batch did **not** introduce per-class IQ/LSQ caps. The first validation pass should therefore focus on:

- fetch
- inflight
- rename
- dispatch

### Initial profile defaults in code

The current default class profiles in `BaseO3CPU.py` are:

- Serialized: `fetch=2`, `inflight=64`, `rename=4`, `dispatch=4`
- HighMLP: `fetch=0`, `inflight=0`, `rename=0`, `dispatch=0`
- Control: `fetch=2`, `inflight=96`, `rename=4`, `dispatch=4`
- Resource: `fetch=0`, `inflight=128`, `rename=6`, `dispatch=6`

Here `0` means "keep baseline width" or "disable the cap", depending on the parameter.

## Recommended Local Workflow

### Step 1. Sync the workspace

At minimum sync:

- `/home/rock/project/gem5`

If your local path differs, that is fine. Just keep the repo self-contained.

### Step 2. Prepare local dependencies

You need a working local gem5 build environment with at least:

- `python3`
- `scons`
- a recent `g++`
- `pkg-config`
- protobuf dev packages
- zlib dev packages
- hdf5 dev packages
- libpng dev packages

The server used Python 3.12 and standard gem5 ARM build dependencies.

### Step 3. Build once

Recommended build command:

```bash
scons -C /path/to/gem5 build/ARM/gem5.opt -j$(nproc)
```

If the local machine is memory-sensitive, use a smaller job count.

### Step 4. First smoke: legacy v2 path

Use a short run first to confirm the repo still behaves like old `v2`.

Example:

```bash
cd /path/to/gem5
./scripts/run_adaptive.sh 1000000 5000 \
  --run-tag phase_scan_mix_v2_legacy_smoke \
  --workload /path/to/gem5/workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix
```

What to check:

- run completes
- `config.ini` contains `adaptiveUseClassProfiles=False` or does not override it
- `adaptive_window_log.csv` still shows `aggressive` / `conservative`

### Step 5. Second smoke: per-class profile path

Then enable the new path explicitly:

```bash
cd /path/to/gem5
./scripts/run_adaptive.sh 1000000 5000 \
  --run-tag phase_scan_mix_class_profiles_smoke \
  --workload /path/to/gem5/workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix \
  --param "system.cpu[0].adaptiveUseClassProfiles=True"
```

What to check:

- run completes
- `config.ini` shows the new profile params
- `adaptive_window_log.csv` contains profile names like:
  - `serialized-profile`
  - `high-mlp-profile`
  - `control-profile`
  - `resource-profile`

### Step 6. Recommended first comparison set

After smoke tests, compare these three workloads first:

- `phase_scan_mix`
- `branch_entropy`
- `compute_queue_pressure`

Reason:

- `phase_scan_mix` was the strongest `v2` win
- `branch_entropy` was the second strongest `v2` win
- `compute_queue_pressure` was basically neutral before, so it is a good regression detector

### Step 7. Suggested comparison matrix

For each workload, run:

1. baseline
2. legacy `v2`
3. `v2 + adaptiveUseClassProfiles=True`

Use the same `maxinsts` for all three.

Recommended first pass:

- smoke / debug: `1M`
- quick comparison: `10M`
- serious comparison: `50M`

## What To Measure

Minimum:

- `simTicks`
- `system.cpu.ipc`
- `Runtime Dynamic Power`
- `Total Runtime Energy`
- `EDP`

Also inspect:

- class distribution in `adaptive_window_log.csv`
- applied mode distribution in `adaptive_window_log.csv`

## Most Likely Success Criteria

The new path is worth keeping if it does at least one of these:

- improves `phase_scan_mix` beyond legacy `v2`
- improves `branch_entropy` beyond legacy `v2`
- keeps the previous wins while reducing damage on neutral workloads

The new path is likely not worth keeping if:

- it introduces widespread churn with no extra gain
- `compute_queue_pressure` / `stream_cluster_reduce` regress noticeably
- most windows still collapse into effectively the same behavior as old `v2`

## Open Risks To Check First

1. `AdaptiveMode` enum expansion may require a full successful compile before we know everything is wired cleanly.
2. Some logic still conceptually assumes a 2-mode controller, even though the code now supports profile modes.
3. IQ/LSQ caps are still shared legacy knobs, so profile separation is incomplete.
4. The new defaults may need tuning even if the mechanism works.

## Suggested Message To Local Codex

If you want to brief a local Codex instance, this is the shortest useful prompt:

```text
Please continue from docs/local_codex_handoff_2026-04-01.md.
Build the ARM gem5 target once, verify the new adaptive class-profile path compiles,
then run paired smoke tests for legacy v2 and adaptiveUseClassProfiles=True.
After smoke passes, compare phase_scan_mix, branch_entropy, and compute_queue_pressure
against baseline and current v2, and summarize whether the per-class profile path is worth keeping.
Do not rewrite docs first; prioritize build, validation, and experimental results.
```

## Final Status At Handoff Time

- code edits are present
- syntax checks passed
- full build not completed
- runtime tests not completed
- next action should be one local full build, then focused paired experiments
