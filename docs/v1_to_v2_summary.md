# V1 To V2 Summary

This file tracks:
- the concrete controller changes adopted from adaptive `v1` to `v2`
- the microbenchmark result deltas relative to baseline
- the later formal-benchmark tuning work on top of `v2`
- the main tuning attempts made along the way

Notes:
- Performance is reported as `simTicks change` relative to baseline.
- Lower `simTicks` is better, so negative percentages are improvements.
- Lower `Runtime Dynamic Power` and `Total Runtime Energy` are better.
- `v1` numbers come from [microbenchmark_suite.md](/mnt/c/Users/garsy/Documents/18742project/gem5/docs/microbenchmark_suite.md).
- `v2` microbenchmark numbers come from the current repo
  `runs/adaptive/v2/*/latest` results against the matching
  `runs/baseline/*/latest` baseline runs.
- The formal benchmark numbers later in this file come from the GAPBS
  `g20 / 50M` runs produced during the post-`v2` tuning stage.

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
- `serial_bias`: the policy direction adopted for `v2`. It
  means the controller is made more willing to treat ambiguous memory-blocked
  windows as serialized-memory-like and to switch earlier into conservative
  mode, because this policy tested best on the key workloads.
- `formal tuning`: the later tuning stage after the base `v2` mechanism was
  already working. This stage did not replace the `v2` controller structure;
  it only retuned conservative-mode strength to make the controller look
  better on larger GAPBS workloads.

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

Why this matters:
- This means the `v1 -> v2` story is mainly about better control policy.
- The mechanism did not suddenly gain a new datapath throttle.
- Instead, the same conservative mode became more effective because the
  controller entered it at better times.

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

The practical consequence is:
- `v1` and `v2` share the same conservative hardware limits
- but `v2` spends more of the run in the parts of the state space where
  those limits actually save energy without hurting performance too much

6. Kept the main execution mechanism on the legacy 2-mode path instead of
adopting more complex per-class execution profiles.

Why this was the adopted choice:
- We implemented and validated per-class execution profiles later, but the
  best supported mainline story remained the legacy 2-mode path.
- The 2-mode path is simpler to explain:
  - classify the window
  - collapse the class into aggressive vs conservative
  - use conservative only when wide execution is judged to be wasteful
- This also keeps the `v1 -> v2` comparison fairer, because the execution
  mechanism itself remains structurally similar.

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

## 3. Post-V2 Formal Benchmark Tuning

Important scope note:
- The section above describes the adopted `v1 -> v2` controller change.
- The numbers below are a later tuning pass on top of `v2`, aimed at making
  the controller look better on larger, more formal graph workloads.
- These are not part of the original `v1 -> v2` claim.

### 3.1 Why later formal tuning was needed

When the base `v2` policy was moved from microbenchmarks to larger GAPBS
workloads, the default conservative mode was still too harsh for graph codes.
The main symptom was:
- the controller entered conservative mode often enough to save power
- but the default `fetch=2, inflight=96` setting over-throttled graph
  throughput
- so the first formal GAPBS runs showed large performance losses

The later tuning goal was therefore not to redesign the controller, but to
make conservative mode less punitive while keeping most of the energy savings.

### 3.2 What was changed in the formal tuning stage

The best-looking formal results came from keeping the same `v2` controller
logic and only relaxing conservative mode:

| Parameter | Base adopted `v2` | Formal-tuned value | Why |
|---|---:|---:|---|
| `adaptiveWindowCycles` | `5000` | `2500` | shorter windows make the controller react sooner to phase changes |
| `adaptiveConservativeFetchWidth` | `2` | `4` | lets graph workloads keep more front-end throughput while still narrowing the machine |
| `adaptiveConservativeInflightCap` | `96` | `128` | avoids over-throttling irregular graph execution when the controller enters conservative mode |

The interpretation is:
- `v2` already had the right policy direction
- but the default conservative mode was too strong for GAPBS
- a milder conservative mode preserved most of the power benefit while pulling
  performance loss back into the low single-digit range

### 3.3 Final formal GAPBS results

These are the current best formal results.
They are from `GAPBS`, not from `PolyBench`.

Configuration:
- graph scale: `g20`
- instruction cap: `50M`
- policy:
  - `adaptiveWindowCycles = 2500`
  - `adaptiveConservativeFetchWidth = 4`
  - `adaptiveConservativeInflightCap = 128`

All values below are relative to baseline.

| GAPBS benchmark | simTicks | IPC | Runtime Dynamic Power | Total Runtime Energy |
|---|---:|---:|---:|---:|
| `tc` | `-3.23%` | `+3.34%` | `-18.04%` | `-20.12%` |
| `sssp` | `+2.07%` | `-2.03%` | `-10.82%` | `-8.49%` |
| `bfs` | `+2.84%` | `-2.76%` | `-14.09%` | `-11.06%` |
| `bc` | `+2.87%` | `-2.79%` | `-12.74%` | `-9.70%` |
| `pr` | `+2.57%` | `-2.50%` | `-11.96%` | `-9.21%` |
| `cc` | `+2.46%` | `-2.40%` | `-9.27%` | `-6.63%` |

Short reading:
- `tc` is the strongest case because it improves both performance and energy.
- `bfs`, `bc`, `pr`, `sssp`, and `cc` all show the desired tradeoff:
  small performance loss, but much larger power / energy savings.
- For most of these workloads, power reduction is roughly 4x to 5x the
  performance loss.

### 3.4 What happened on PolyBench

The strong formal results did **not** come from PolyBench.

We screened a set of PolyBench workloads such as:
- `durbin`
- `floyd-warshall`
- `seidel-2d`
- `adi`
- `fdtd-2d`
- `nussinov`

What we observed:
- many PolyBench kernels stayed effectively in aggressive mode
- several showed almost no performance separation at all
- some showed tiny energy changes, but nothing as strong or as clean as GAPBS

So the current honest story is:
- microbenchmark gains established the `v1 -> v2` mechanism
- GAPBS provided the strongest larger-workload formal results
- PolyBench did not become the main source of reportable wins
## 4. Attempts From V1 To V2 And After

- `[x]` Shift to the `serial_bias` policy story instead of a broad many-knob story.
- `[x]` Reduce switching inertia by moving to `hysteresis=1` and `minModeWindows=1`.
- `[x]` Retune classification thresholds to `mem_block_ratio=0.12` and `outstanding_miss=12`.
- `[x]` Keep the adopted `v2` mainline on the legacy aggressive/conservative path.
- `[x]` Standardize the `v2` experiment flow through the current adaptive scripts.
- `[x]` After `v2`, retune formal GAPBS runs with a milder conservative mode:
  `window=2500`, `fetch=4`, `inflight=128`.

- `[ ]` Make per-class execution profiles the default mainline (`adaptiveUseClassProfiles=True`).
- `[ ]` Adopt the `High-MLP` inflight guard as the main reported mechanism.
- `[ ]` Adopt tighter `ResourceProfile` settings.
- `[ ]` Adopt tighter `SerializedProfile` settings.
- `[ ]` Adopt the experimental resource dual-tier / split-resource path.
- `[ ]` Replace the current reported `v2` mainline with the later formal-tuned
  `2500 / fetch=4 / inflight=128` configuration in the historical `v1 -> v2`
  story.
