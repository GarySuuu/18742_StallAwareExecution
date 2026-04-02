# V1 To V2 Summary

This file tracks the concrete changes adopted from adaptive `v1` to `v2`,
the microbenchmark result deltas relative to baseline, and the main tuning
attempts made along the way.

Notes:
- Performance is reported as `simTicks change` relative to baseline.
- Lower `simTicks` is better, so negative percentages are improvements.
- Lower `Runtime Dynamic Power` and `Total Runtime Energy` are better.
- `v1` numbers come from [microbenchmark_suite.md](/mnt/c/Users/garsy/Documents/18742project/gem5/docs/microbenchmark_suite.md).
- `v2` numbers come from the current repo `runs/adaptive/v2/*/latest` results
  against the matching `runs/baseline/*/latest` baseline runs.

Terminology used in this file:
- `baseline`: gem5 runs with the adaptive controller disabled.
- `v1`: the earlier 4-class classification + 2-mode execution design.
- `v2`: the later tuned version that keeps the same basic 2-mode mechanism
  but changes the policy defaults and classification thresholds.
- `aggressive mode`: the CPU keeps its normal / wide execution settings.
- `conservative mode`: the CPU uses tighter front-end / inflight limits to
  save power when the controller believes wider execution is wasteful.
- `legacy aggressive/conservative path`: the original mapping where the four
  detected classes still collapse into only two execution modes:
  serialized/control -> conservative, high-MLP/resource -> aggressive.
- `serial_bias`: the policy direction adopted for `v2`. In plain terms, it
  means the controller is made more willing to treat ambiguous memory-blocked
  windows as serialized-memory-like and to switch earlier into conservative
  mode, because this policy tested best on the key workloads.

## 1. Adopted Changes From V1 To V2

1. Conservative mode limits: what `v1` restricted and what `v2` restricts

The important clarification is that the adopted `v2` mainline did **not**
change which microarchitectural knobs are restricted in conservative mode.
`v1` and `v2` use the same conservative-mode limits; `v2` mainly changed
**when** the CPU enters conservative mode, not **what** conservative mode does.

In the legacy 2-mode path, conservative mode can limit:
- fetch width
- total inflight instruction count proxy
- optional IQ cap
- optional LSQ cap
- optional rename width
- optional dispatch width

The adopted settings are:

| Conservative-mode parameter | What it limits | V1 adopted value | V2 adopted value |
|---|---|---:|---:|
| `adaptiveConservativeFetchWidth` | front-end fetch width while in conservative mode | `2` | `2` |
| `adaptiveConservativeInflightCap` | soft cap on inflight / ROB-like pressure while in conservative mode | `96` | `96` |
| `adaptiveConservativeIQCap` | optional issue queue cap (`0` means disabled) | `0` | `0` |
| `adaptiveConservativeLSQCap` | optional LSQ cap (`0` means disabled) | `0` | `0` |
| `adaptiveConservativeRenameWidth` | optional rename width cap (`0` means keep baseline rename width) | `0` | `0` |
| `adaptiveConservativeDispatchWidth` | optional dispatch width cap (`0` means keep baseline dispatch width) | `0` | `0` |

So the honest summary is:
- `v1` conservative mode already meant “fetch=2, inflight cap=96”
- `v2` kept the same conservative restriction
- the real `v2` improvement came from policy tuning, not from a harsher
  conservative datapath

2. Adopted the `serial_bias` policy direction

`serial_bias` is not a separate hardware state.
It is a **named tuned policy point** built on the same `v1` controller logic.

What it tries to do:
- switch earlier
- classify more borderline memory-blocked windows as `Serialized` rather than
  `High-MLP`
- because in the legacy path:
  - `Serialized` maps to `Conservative`
  - `High-MLP` maps to `Aggressive`

That means `serial_bias` is effectively a policy that makes the CPU enter
conservative mode earlier and more often for memory-blocked windows that do
not look strongly parallel.

3. Reduced switching inertia so the controller reacts earlier.

| Parameter | Meaning | V1 / old default | V2 / adopted default |
|---|---|---:|---:|
| `adaptiveSwitchHysteresis` | how many consecutive windows a new class must persist before switching | `2` | `1` |
| `adaptiveMinModeWindows` | minimum number of windows the current mode must be held before another switch is allowed | `2` | `1` |

4. Retuned the classification thresholds used by `serial_bias`

These are the parameters that actually make the controller more
serialized-memory-biased:

| Parameter | Meaning | V1 / old default | V2 / adopted default |
|---|---|---:|---:|
| `adaptiveMemBlockRatioThres` | minimum fraction of commit-blocked-by-memory cycles before the controller considers the window memory-dominated | `0.15` | `0.12` |
| `adaptiveOutstandingMissThres` | minimum outstanding-miss proxy needed before the controller classifies a memory-blocked window as high-MLP rather than serialized | `8` | `12` |

5. How `serial_bias` is implemented in the classifier

The classifier logic in [cpu.cc](/mnt/c/Users/garsy/Documents/18742project/gem5/src/cpu/o3/cpu.cc) works like this:

1. It first checks whether the window is memory-blocked:
   - `mem_block_ratio >= adaptiveMemBlockRatioThres`

2. If yes, it then checks the outstanding-miss proxy:
   - `avg_outstanding_misses_proxy >= adaptiveOutstandingMissThres`

3. The classification decision is then:
   - memory-blocked + high outstanding misses -> `High-MLP`
   - memory-blocked + lower outstanding misses -> `Serialized`

4. In the legacy 2-mode path, the mode mapping is:
   - `Serialized` -> `Conservative`
   - `Control` -> `Conservative`
   - `High-MLP` -> `Aggressive`
   - `Resource` -> `Aggressive`

So the concrete effect of the `v1 -> v2` parameter changes is:
- lowering `adaptiveMemBlockRatioThres` from `0.15` to `0.12`
  - more windows are recognized as memory-blocked
- raising `adaptiveOutstandingMissThres` from `8` to `12`
  - fewer of those memory-blocked windows qualify as `High-MLP`
  - so more fall into `Serialized`
- reducing `adaptiveSwitchHysteresis` / `adaptiveMinModeWindows` from `2/2` to `1/1`
  - once the window is classified as `Serialized`, the CPU moves into
    conservative mode faster

This is why the policy is called `serial_bias`:
- it biases ambiguous memory-blocked behavior toward the `Serialized` class
- and because `Serialized` maps to `Conservative`, it increases conservative-mode usage

6. Kept the main execution mechanism on the legacy 2-mode path instead of
adopting more complex per-class execution profiles.

7. Standardized the `v2` experiment flow around the current adaptive scripts.
   This is an engineering change rather than a controller-logic change, but it
   is part of what made the `v2` results reproducible and comparable:
   - [run_adaptive.sh](/mnt/c/Users/garsy/Documents/18742project/gem5/scripts/run_adaptive.sh)
   - [run_adaptive_unique.sh](/mnt/c/Users/garsy/Documents/18742project/gem5/scripts/run_adaptive_unique.sh)

## 2. Microbenchmark Comparison: V1 vs V2

All percentage values below are relative to baseline.

| Benchmark | V1 simTicks | V2 simTicks | V1 IPC | V2 IPC | V1 Power | V2 Power | V1 Energy | V2 Energy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `serialized_pointer_chase` | `+5.931%` | `+5.959%` | `-5.599%` | `-5.624%` | `-17.121%` | `-17.161%` | `-10.985%` | `-11.001%` |
| `branch_entropy` | `+0.086%` | `-0.175%` | `-0.086%` | `+0.175%` | `-0.945%` | `-11.614%` | `-0.818%` | `-11.262%` |
| `hash_probe_chain` | `0.000%` | `0.000%` | `0.000%` | `0.000%` | `+0.042%` | `+0.042%` | `+0.037%` | `+0.037%` |
| `phase_scan_mix` | `-0.277%` | `-1.051%` | `+0.278%` | `+1.062%` | `-4.575%` | `-17.065%` | `-4.449%` | `-16.488%` |
| `stream_cluster_reduce` | `0.000%` | `0.000%` | `0.000%` | `0.000%` | `+0.049%` | `+0.049%` | `+0.043%` | `+0.043%` |
| `compute_queue_pressure` | `0.000%` | `0.000%` | `0.000%` | `0.000%` | `+0.015%` | `+0.015%` | `+0.014%` | `+0.014%` |

Short reading:
- `branch_entropy` improved the most from `v1` to `v2`.
- `phase_scan_mix` also improved clearly in both performance and energy.
- `serialized_pointer_chase` remained an energy-saving but performance-losing case.
- `hash_probe_chain`, `stream_cluster_reduce`, and `compute_queue_pressure`
  still show little or no benefit.

## 3. Attempts From V1 To V2

- `[x]` Shift to the `serial_bias` policy story instead of a broad many-knob story.
- `[x]` Reduce switching inertia by moving to `hysteresis=1` and `minModeWindows=1`.
- `[x]` Retune classification thresholds to `mem_block_ratio=0.12` and `outstanding_miss=12`.
- `[x]` Keep the adopted `v2` mainline on the legacy aggressive/conservative path.
- `[x]` Standardize the `v2` experiment flow through the current adaptive scripts.

- `[ ]` Make per-class execution profiles the default mainline (`adaptiveUseClassProfiles=True`).
- `[ ]` Adopt the `High-MLP` inflight guard as the main reported mechanism.
- `[ ]` Adopt tighter `ResourceProfile` settings.
- `[ ]` Adopt tighter `SerializedProfile` settings.
- `[ ]` Adopt the experimental resource dual-tier / split-resource path.
- `[ ]` Replace the current 5000-cycle mainline with the shorter 2500-cycle window.
