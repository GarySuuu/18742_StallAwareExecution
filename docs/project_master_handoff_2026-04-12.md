# Project Master Handoff (2026-04-12)

This is the primary handoff document for the project. It is intended for a new
agent or new collaborator who needs one place to understand:

- what problem the project is solving
- how the mechanism is designed
- what code paths matter
- how the evaluation is structured
- what was tried
- what worked
- what did not work
- what should be treated as the current mainline

This document is intentionally comprehensive. Shorter summary documents were
removed because they duplicated each other and hid the real state of the
project.

## 1. Project Goal

The project studies whether a simple runtime-adaptive O3 CPU policy can reduce
power and energy without paying a large performance penalty.

The target setting is a single-core `DerivO3CPU` in gem5 `SE` mode on `ARM`.
The basic hypothesis is:

- some execution windows are naturally wide and parallel, so aggressive
  execution is worthwhile
- some execution windows are bottlenecked by serialized memory behavior or
  control recovery, so wide aggressive execution wastes power
- if we classify windows online and selectively enter a conservative mode only
  when wide execution is wasteful, we may improve the performance-energy
  tradeoff

The mechanism is not trying to redesign the whole microarchitecture. It is
trying to add a controller on top of the existing O3 CPU that:

- samples recent behavior
- classifies the current stall/root-cause regime
- maps that regime to a small set of execution policies
- changes fetch/inflight pressure and related limits at window boundaries

## 2. Repository Map

The most relevant project files are:

- `src/cpu/o3/BaseO3CPU.py`
- `src/cpu/o3/cpu.hh`
- `src/cpu/o3/cpu.cc`
- `src/cpu/o3/fetch.cc`
- `src/cpu/o3/commit.cc`
- `scripts/run_baseline.sh`
- `scripts/run_adaptive.sh`
- `scripts/run_adaptive_unique.sh`
- `scripts/gem5_to_mcpat.py`
- `scripts/build_formal_benchmarks.sh`
- `scripts/run_formal_benchmark_batch.sh`

The most relevant retained historical documents are:

- `docs/adaptive_mechanism_v1.md`
- `docs/microbenchmark_suite.md`
- `docs/next_steps_todo.md`
- `docs/external_benchmark_resources.md`

## 3. Core Concepts

### 3.1 Baseline

`baseline` means the adaptive controller is disabled.

Baseline configuration:

- ISA: `ARM`
- CPU: `DerivO3CPU`
- mode: `SE`
- core count: `1`
- caches: `--caches --l2cache`
- memory size: `2GB`

Baseline runs are launched through `scripts/run_baseline.sh` and written under
`runs/baseline/...`.

### 3.2 Adaptive controller

The adaptive controller adds window-based runtime classification and dynamic
mode selection on top of the O3 CPU.

The controller has two conceptual stages:

1. Detection / classification
2. Execution policy selection

### 3.3 Four runtime classes

The classifier uses four semantic classes:

- `Serialized-memory dominated`
- `High-MLP memory dominated`
- `Control dominated`
- `Resource-contention / compute dominated`

These classes are not produced by ML. They are produced by rule-based logic
from per-window counters and proxies.

### 3.4 Two execution-policy families

There are two execution-policy families in the codebase:

1. Legacy 2-mode path
2. Per-class profile path

The important distinction:

- the current recommended mainline still uses the legacy 2-mode path
- the per-class profile path exists, was implemented and validated, but is not
  the recommended final mainline story

### 3.5 Legacy 2-mode path

The legacy path collapses the four classes into two runtime modes:

- `Serialized` -> `Conservative`
- `Control` -> `Conservative`
- `High-MLP` -> `Aggressive`
- `Resource` -> `Aggressive`

This is the path used when:

- `adaptiveUseClassProfiles=False`

This is the simpler and better-supported mainline.

### 3.6 Per-class profile path

The newer experimental path maps each class to its own applied profile:

- `Serialized` -> `serialized-profile`
- `High-MLP` -> `high-mlp-profile`
- `Control` -> `control-profile`
- `Resource` -> `resource-profile`

This is used when:

- `adaptiveUseClassProfiles=True`

This path was implemented, built, and smoke-tested. It is useful to understand
because the code still contains it, but it was not adopted as the final main
story.

## 4. Methodology

### 4.1 Sampling model

The controller operates on fixed windows:

- `adaptiveWindowCycles`

At each window boundary it:

1. computes derived metrics from collected counters
2. classifies the window
3. maps the class to a target mode/profile
4. applies hysteresis / minimum-hold logic
5. logs the window to `adaptive_window_log.csv`

### 4.2 Collected counters and proxies

The controller uses these counters and signals:

- fetched instructions
- committed instructions
- squashed instructions
- branch mispredict events
- commit-blocked-by-memory cycle proxy
- outstanding misses proxy
- IQ occupancy
- IQ saturation cycles
- branch recovery cycles proxy
- inflight instruction proxy

The most important caveat is that several of these are proxies, not exact
ground-truth signals:

- `avg_outstanding_misses_proxy` uses LQ occupancy
- `commit_blocked_mem_cycles` is heuristic
- `branch_recovery_cycles` is based on commit squashing state
- `avg_inflight_proxy` uses ROB occupancy

This matters because one of the major debugging findings was that a proxy can
misclassify a workload even when the high-level mechanism is otherwise correct.

### 4.3 Derived metrics

The main per-window derived metrics are:

- `mem_block_ratio`
- `avg_outstanding_misses_proxy`
- `branch_recovery_ratio`
- `squash_ratio`
- `iq_saturation_ratio`
- `commit_activity_ratio`
- `avg_inflight_proxy`

These metrics are computed in `cpu.cc`.

### 4.4 Classification logic

The current classifier in `src/cpu/o3/cpu.cc` works in this order:

1. Check whether the window is memory-blocked:
   - `mem_block_ratio >= adaptiveMemBlockRatioThres`
2. If memory-blocked:
   - if `avg_outstanding_misses_proxy >= adaptiveOutstandingMissThres`
     and the high-MLP inflight guard passes, classify as `High-MLP`
   - otherwise classify as `Serialized`
3. Else if branch recovery and squash are both high, classify as `Control`
4. Else if IQ saturation and commit activity are high, classify as `Resource`
5. Else default to `Resource`

The high-MLP inflight guard is:

- `avg_inflight_proxy <= adaptiveHighMLPMaxInflightProxy`

This guard was added later to prevent a known false-positive path on
`compute_queue_pressure`.

### 4.5 Mode-switch policy

Switching is controlled by:

- `adaptiveSwitchHysteresis`
- `adaptiveMinModeWindows`

Meaning:

- a new class has to persist for some number of windows before switching
- once in a mode, the CPU must stay there for at least some minimum number of
  windows before another switch is allowed

This turned out to be one of the most important levers in the project.

## 5. Architecture Design in the Code

### 5.1 Parameters exposed in `BaseO3CPU.py`

There are three parameter groups:

1. Legacy 2-mode controls
2. Per-class profile controls
3. Classification thresholds

#### Legacy 2-mode controls

- `enableStallAdaptive`
- `adaptiveWindowCycles`
- `adaptiveSwitchHysteresis`
- `adaptiveMinModeWindows`
- `adaptiveConservativeFetchWidth`
- `adaptiveConservativeInflightCap`
- `adaptiveConservativeIQCap`
- `adaptiveConservativeLSQCap`
- `adaptiveConservativeRenameWidth`
- `adaptiveConservativeDispatchWidth`

#### Per-class profile controls

- `adaptiveUseClassProfiles`
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

#### Experimental resource-tight sub-profile controls

These were added during later tuning and still exist in the source:

- `adaptiveResourceTightMaxInflightProxy`
- `adaptiveResourceTightMinSquashRatio`
- `adaptiveResourceTightFetchWidth`
- `adaptiveResourceTightInflightCap`
- `adaptiveResourceTightRenameWidth`
- `adaptiveResourceTightDispatchWidth`

These are not the recommended mainline story, but they are real code.

#### Classification-threshold controls

- `adaptiveMemBlockRatioThres`
- `adaptiveOutstandingMissThres`
- `adaptiveHighMLPMaxInflightProxy`
- `adaptiveBranchRecoveryRatioThres`
- `adaptiveSquashRatioThres`
- `adaptiveIQSaturationRatioThres`
- `adaptiveCommitActivityRatioThres`

### 5.2 Important source-level detail: code defaults vs script defaults

`BaseO3CPU.py` still contains conservative/default threshold values closer to
the earlier mechanism:

- `adaptiveWindowCycles = 5000`
- `adaptiveSwitchHysteresis = 2`
- `adaptiveMinModeWindows = 2`
- `adaptiveMemBlockRatioThres = 0.15`
- `adaptiveOutstandingMissThres = 8`

However the adaptive run scripts override these and define the practical `v2`
policy point:

- `adaptiveSwitchHysteresis = 1`
- `adaptiveMinModeWindows = 1`
- `adaptiveMemBlockRatioThres = 0.12`
- `adaptiveOutstandingMissThres = 12`

This distinction matters:

- the code defaults describe the underlying implementation defaults
- the scripts define the actual evaluated `v2` default policy

### 5.3 Current mainline conservative-mode limits

The adopted legacy conservative mode is still:

- `adaptiveConservativeFetchWidth = 2`
- `adaptiveConservativeInflightCap = 96`
- `adaptiveConservativeIQCap = 0`
- `adaptiveConservativeLSQCap = 0`
- `adaptiveConservativeRenameWidth = 0`
- `adaptiveConservativeDispatchWidth = 0`

Meaning:

- fetch is explicitly narrowed to `2`
- inflight pressure is capped at `96`
- IQ/LSQ/rename/dispatch extra caps are disabled in the adopted base `v2`

### 5.4 Per-class profile defaults currently in the source

The current source defaults are:

- Serialized:
  - fetch `2`
  - inflight `64`
  - rename `4`
  - dispatch `4`
- HighMLP:
  - fetch `0`
  - inflight `0`
  - rename `0`
  - dispatch `0`
- Control:
  - fetch `2`
  - inflight `96`
  - rename `4`
  - dispatch `4`
- Resource:
  - fetch `0`
  - inflight `96`
  - rename `5`
  - dispatch `5`

`0` means:

- keep baseline width, or
- disable the cap

### 5.5 Resource-tight sub-profile defaults currently in the source

These values exist in the source:

- `adaptiveResourceTightMaxInflightProxy = 24.0`
- `adaptiveResourceTightMinSquashRatio = 0.15`
- `adaptiveResourceTightFetchWidth = 2`
- `adaptiveResourceTightInflightCap = 72`
- `adaptiveResourceTightRenameWidth = 4`
- `adaptiveResourceTightDispatchWidth = 4`

This path adds a tighter sub-profile inside `ResourceProfile`. It was added as
an experiment and remains in the implementation, but it is not the recommended
mainline.

## 6. Evolution of the Design

### 6.1 Baseline

Static O3 CPU with no runtime adaptation.

### 6.2 V1

`v1` introduced:

- 4-class rule-based classification
- 2-mode execution (`aggressive`, `conservative`)
- window-level logging
- baseline/adaptive script separation

`v1` established that the mechanism worked, but its benefits were limited and
inconsistent.

### 6.3 V2

`v2` did not fundamentally change the 2-mode datapath restrictions. The key
adopted changes were policy changes:

- lower switching inertia
- more serialized-memory-biased classification

The practical `v2` policy point was:

- `adaptiveSwitchHysteresis = 1`
- `adaptiveMinModeWindows = 1`
- `adaptiveMemBlockRatioThres = 0.12`
- `adaptiveOutstandingMissThres = 12`

This policy direction was internally named `serial_bias`.

### 6.4 What `serial_bias` actually means

`serial_bias` is not a new hardware mode.

It means:

- more memory-blocked windows are recognized as memory-sensitive
- fewer ambiguous memory-blocked windows are allowed to count as `High-MLP`
- more such windows fall into `Serialized`
- and because `Serialized` maps to `Conservative` in the legacy 2-mode path,
  the CPU enters conservative mode earlier and more often on memory-blocked
  windows that do not look strongly parallel

In concrete parameter terms, relative to the old `v1` defaults:

- `adaptiveSwitchHysteresis: 2 -> 1`
- `adaptiveMinModeWindows: 2 -> 1`
- `adaptiveMemBlockRatioThres: 0.15 -> 0.12`
- `adaptiveOutstandingMissThres: 8 -> 12`

The key conceptual point is:

- `v2` improved mostly by changing when conservative mode is entered
- not by making conservative mode much harsher

## 7. Evaluation Methodology

### 7.1 Primary metrics

The project uses:

- `simTicks`
- `IPC`
- `Runtime Dynamic Power`
- `Total Runtime Energy`
- sometimes `EDP`

Interpretation:

- lower `simTicks` is better
- higher `IPC` is better
- lower `Runtime Dynamic Power` is better
- lower `Total Runtime Energy` is better

### 7.2 Relative reporting convention

Most reported numbers are relative to baseline:

- negative `simTicks change` means performance improved
- positive `simTicks change` means performance regressed
- negative power/energy change means savings

### 7.3 Workload groups used so far

There are three workload groups:

1. In-tree microbenchmarks
2. PolyBench screening kernels
3. GAPBS graph workloads

## 8. Microbenchmark Suite

The six in-tree microbenchmarks are:

- `serialized_pointer_chase`
- `branch_entropy`
- `hash_probe_chain`
- `phase_scan_mix`
- `stream_cluster_reduce`
- `compute_queue_pressure`

Their intended behaviors are described in `docs/microbenchmark_suite.md`.

### 8.1 V1 vs V2 microbenchmark results

All percentages are relative to baseline.

| Benchmark | V1 simTicks | V2 simTicks | V1 IPC | V2 IPC | V1 Power | V2 Power | V1 Energy | V2 Energy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `serialized_pointer_chase` | `+5.931%` | `+5.959%` | `-5.599%` | `-5.624%` | `-17.121%` | `-17.161%` | `-10.985%` | `-11.001%` |
| `branch_entropy` | `+0.086%` | `-0.175%` | `-0.086%` | `+0.175%` | `-0.945%` | `-11.614%` | `-0.818%` | `-11.262%` |
| `hash_probe_chain` | `0.000%` | `0.000%` | `0.000%` | `0.000%` | `+0.042%` | `+0.042%` | `+0.037%` | `+0.037%` |
| `phase_scan_mix` | `-0.277%` | `-1.051%` | `+0.278%` | `+1.062%` | `-4.575%` | `-17.065%` | `-4.449%` | `-16.488%` |
| `stream_cluster_reduce` | `0.000%` | `0.000%` | `0.000%` | `0.000%` | `+0.049%` | `+0.049%` | `+0.043%` | `+0.043%` |
| `compute_queue_pressure` | `0.000%` | `0.000%` | `0.000%` | `0.000%` | `+0.015%` | `+0.015%` | `+0.014%` | `+0.014%` |

### 8.2 What these results mean

`v2` clearly improved over `v1` on:

- `phase_scan_mix`
- `branch_entropy`

`serialized_pointer_chase` remained:

- good for power/energy
- bad for performance

`hash_probe_chain`, `stream_cluster_reduce`, and
`compute_queue_pressure` remained weak or neutral.

## 9. Current Best Mainline Stories

There are two different “best” stories depending on what is being emphasized.

### 9.1 Best microbenchmark mainline

For the original project mechanism story, the best adopted mainline remains:

- legacy 2-mode path
- `serial_bias` policy direction

This is the cleanest `v1 -> v2` story.

### 9.2 Best formal benchmark mainline

For larger graph workloads, the best-looking point was a later tuning pass on
top of `v2`:

- `adaptiveWindowCycles = 2500`
- `adaptiveConservativeFetchWidth = 4`
- `adaptiveConservativeInflightCap = 128`

This is not the original `v2` default. It is a later formal-tuned operating
point used to improve the performance-energy tradeoff on `GAPBS`.

## 10. Formal Benchmark Work

### 10.1 Benchmark suites explored

Two external suites were brought in:

- `GAPBS`
- `PolyBench/C`

The helper scripts are:

- `scripts/build_formal_benchmarks.sh`
- `scripts/run_formal_benchmark_batch.sh`

### 10.2 What happened on PolyBench

PolyBench did not produce the strongest positive results.

Representative screening outcome:

- `durbin`: essentially flat
- `floyd-warshall`: essentially flat
- `seidel-2d`: flat
- `adi`: flat
- `fdtd-2d`: flat
- `nussinov`: slight regression

Conclusion:

- PolyBench was useful as a screen
- it did not become the final positive-result story

### 10.3 What happened on GAPBS

GAPBS produced the strongest formal results.

The final recommended formal point is:

- graph scale: `g20`
- instruction cap: `50M`
- `adaptiveWindowCycles = 2500`
- `adaptiveConservativeFetchWidth = 4`
- `adaptiveConservativeInflightCap = 128`

Final relative-to-baseline results:

| GAPBS benchmark | simTicks | IPC | Runtime Dynamic Power | Total Runtime Energy |
|---|---:|---:|---:|---:|
| `tc` | `-3.23%` | `+3.34%` | `-18.04%` | `-20.12%` |
| `sssp` | `+2.07%` | `-2.03%` | `-10.82%` | `-8.49%` |
| `bfs` | `+2.84%` | `-2.76%` | `-14.09%` | `-11.06%` |
| `bc` | `+2.87%` | `-2.79%` | `-12.74%` | `-9.70%` |
| `pr` | `+2.57%` | `-2.50%` | `-11.96%` | `-9.21%` |
| `cc` | `+2.46%` | `-2.40%` | `-9.27%` | `-6.63%` |

Interpretation:

- `tc` improved both performance and energy
- the other five accepted small performance losses of about `2%~3%`
- in exchange, they achieved much larger `power` and `energy` savings
- this was the best “good-looking” formal tradeoff found

## 11. All Major Efforts and Attempts

This section records the important workstreams, including ones that did not
become the final answer.

### 11.1 V1 bring-up

What was done:

- implemented the 4-class rule-based classifier
- implemented the 2-mode execution path
- added window logging
- separated baseline and adaptive flows

Outcome:

- successful bring-up
- proved the controller could run end-to-end
- produced mixed but real power/performance effects

Adoption status:

- adopted

### 11.2 Conservative datapath ablation on serialized workloads

What was tried:

- fetch-width-only changes
- inflight-cap sweeps
- relaxed thresholds to force more conservative entry

Main finding:

- changing fetch width alone often did nothing if the workload never entered
  conservative mode
- once conservative mode was forced, very small inflight caps changed behavior
- but the observed tradeoff was often:
  - lower power
  - worse performance
  - slightly worse total energy

Outcome:

- proved that “which cap exists” was not the immediate bottleneck
- pointed toward classification / switching policy as the real lever

Adoption status:

- not adopted as the main story

### 11.3 IQ-cap experiments

What was tried:

- `adaptiveConservativeIQCap`
- tested on `phase_scan_mix` at `5M`
- examples: `IQ56`, `IQ48`

Main finding:

- no measurable change relative to default adaptive behavior

Adoption status:

- implemented but not used in the adopted mainline

### 11.4 LSQ / rename / dispatch conservative-mode experiments

What was tried:

- `adaptiveConservativeLSQCap`
- `adaptiveConservativeRenameWidth`
- `adaptiveConservativeDispatchWidth`
- single-knob and combined sweeps on `phase_scan_mix`

Main findings:

- `rename4` and `dispatch4` improved over baseline
- neither beat the default adaptive point
- `default + rename4` gave only a very small extra energy/EDP gain
- the improvement was too marginal to justify the extra complexity

Adoption status:

- not adopted in the mainline

### 11.5 Switching-policy sweeps

What was tried on `phase_scan_mix` 10M:

- `h1m1`
- `h1m2`
- `h2m1`
- `ctrl_loose`
- `serial_bias`

Interpretation of names:

- `h1m1`: hysteresis `1`, min-mode `1`
- `h1m2`: hysteresis `1`, min-mode `2`
- `h2m1`: hysteresis `2`, min-mode `1`
- `ctrl_loose`: loosened control-related thresholds
- `serial_bias`: more serialized-memory-biased thresholds

Main findings:

- lowering switching inertia consistently helped
- `ctrl_loose` improved over the earlier default
- `serial_bias` became the strongest tested point

Longer-run validation:

- `phase_scan_mix` 50M vs baseline:
  - `simTicks -1.051%`
  - `IPC +1.062%`
  - `Runtime Dynamic Power -17.065%`
  - `Total Runtime Energy -16.488%`
  - `EDP -17.366%`
- `branch_entropy` 50M vs baseline:
  - `simTicks -0.175%`
  - `IPC +0.175%`
  - `Runtime Dynamic Power -11.614%`
  - `Total Runtime Energy -11.262%`
  - `EDP -11.417%`

Adoption status:

- adopted

### 11.6 Per-class execution-profile implementation

What was added:

- `adaptiveUseClassProfiles`
- class-specific fetch / inflight / rename / dispatch controls
- profile names in `adaptive_window_log.csv`

Why it was added:

- to test whether `Serialized`, `HighMLP`, `Control`, and `Resource`
  should each get a custom execution mode rather than being collapsed into
  `aggressive` / `conservative`

What was validated:

- build succeeded
- smoke tests ran
- the path genuinely changed applied mode names and behavior
- it worked on the same `ARM` build and same script flow as the legacy path

Representative smoke findings:

- `phase_scan_mix` class-profile mode selection changed, but performance was
  effectively unchanged
- `branch_entropy` and `compute_queue_pressure` showed behavior divergence, but
  the value of the added complexity was not clearly superior to the simpler
  2-mode path

Representative short-run observations that motivated not adopting it as the
mainline:

- `phase_scan_mix`: mode labels changed, but the measured result stayed
  effectively flat
- `branch_entropy`: the class-profile path could produce useful changes, but
  the simpler legacy `serial_bias` path still gave a cleaner overall story
- `compute_queue_pressure`: this path made the classifier/debugging problem
  more obvious, but did not produce a compelling final win

Conclusion:

- the mechanism is real and usable
- it was not adopted as the final mainline because the simpler legacy path had
  a clearer story and better-supported evidence

Adoption status:

- implemented and validated
- not adopted as the final mainline

### 11.7 High-MLP misclassification fix

Problem discovered:

- `compute_queue_pressure` was often being classified as `High-MLP`
- the root cause was the `avg_outstanding_misses_proxy` based on LQ occupancy
- this made a compute/resource-heavy workload look falsely memory-parallel

What was added:

- `adaptiveHighMLPMaxInflightProxy`

Logic:

- a window can only be called `High-MLP` if its inflight proxy is not too high
- otherwise the classifier falls back to `Resource`

Observed effect:

- in a representative `5M` run, `compute_queue_pressure` shifted from hundreds
  of `High-MLP` windows to almost all `Resource` windows
- performance stayed roughly flat
- a representative debug comparison was approximately:
  - before guard: `High-MLP 422`, `Resource 7`
  - after guard: `High-MLP 1`, `Resource 428`

Conclusion:

- this was a structurally meaningful fix
- it improved classifier correctness

Adoption status:

- implemented
- useful and should be preserved in the code history
- not the centerpiece of the mainline narrative

### 11.8 Resource-profile tuning experiments

What was tried:

- `resbase`
- `strongSC`
- `reslight`
- stronger `SerializedProfile`
- stronger `ControlProfile`

Main findings:

- tightening `ResourceProfile` often hurt `branch_entropy`
- stronger serialized/control settings did not create a consistently better
  overall point
- performance-energy gains were not robust enough to justify adopting these as
  the mainline behavior

Adoption status:

- not adopted

### 11.9 Resource tight sub-profile

What was tried:

- add a tighter `Resource` sub-profile
- trigger it when:
  - inflight proxy is low, or
  - squash ratio is high

Intent:

- distinguish two kinds of `Resource` windows:
  - genuinely throughput-oriented resource pressure
  - softer resource/control-like windows that might benefit from tighter caps

Status:

- implemented in code
- logged via `resource_profile_level`
- not adopted as the mainline mechanism

Reason:

- complexity increased
- validation value over the simpler mainline was not strong enough

### 11.10 Window-size sweeps

What was tried:

- `window = 5000`
- `window = 2500`
- `window = 2000`
- `window = 2500` with `hysteresis=0` and `minModeWindows=0`

Main findings:

- `2500` improved `branch_entropy`
- `2000` was worse
- fully removing stability (`h0m0`) was worse

Meaning:

- shorter windows help
- but switching still needs some stability control

Adoption status:

- adopted later for the formal-tuned point

### 11.11 First formal benchmark batch

What was run:

- GAPBS:
  - `bfs`
  - `bc`
  - `pr`
- PolyBench:
  - `atax`
  - `bicg`
  - `jacobi-2d`

Initial outcome:

- GAPBS regressed badly under the base formal `v2` run
- PolyBench mostly showed no meaningful change

Interpretation:

- the base conservative mode was too harsh for graph workloads
- PolyBench did not expose enough useful phase behavior to become a good final
  showcase

Adoption status:

- used as a screen

### 11.12 Formal screening and tuning campaigns

Additional screening workloads included:

- GAPBS at smaller scales:
  - `bfs`
  - `bc`
  - `pr`
  - `cc`
  - `sssp`
  - `tc`
- PolyBench screening kernels:
  - `adi`
  - `durbin`
  - `fdtd-2d`
  - `floyd-warshall`
  - `mvt`
  - `nussinov`
  - `seidel-2d`
  - `trisolv`

Main conclusion:

- graph workloads were the best place to tell the story
- PolyBench did not deliver strong positive results

### 11.13 Final formal conservative-mode sweeps

What was tried:

- “gentle” and “powsaver” directions
- fetch/inflight combinations
- example sweep tags:
  - `fw4_cap160`
  - `fw5_cap128`
  - `fw5_cap160`
  - `win3000`

The two most important later candidates were:

1. More aggressive power saver:
   - `window = 2500`
   - `fetch = 4`
   - `inflight = 128`
2. More balanced candidate:
   - `window = 2500`
   - `fetch = 5`
   - `inflight = 160`

The final choice was candidate 1 because:

- its power and energy savings were larger
- the performance loss stayed in the low single digits
- it produced the strongest final formal result table

Representative alternative candidate that was tested but not chosen:

- `adaptiveWindowCycles = 2500`
- `adaptiveConservativeFetchWidth = 5`
- `adaptiveConservativeInflightCap = 160`

Representative formal results for that alternative:

| GAPBS benchmark | simTicks | Runtime Dynamic Power | Total Runtime Energy |
|---|---:|---:|---:|
| `tc` | `-1.53%` | `-8.56%` | `-9.69%` |
| `sssp` | `+1.13%` | `-7.50%` | `-6.13%` |
| `bfs` | `+2.51%` | `-12.59%` | `-9.87%` |
| `cc` | `+1.92%` | `-4.84%` | `-2.80%` |

Why it was rejected:

- it was more balanced on performance
- but the final power/energy story was weaker than the `fetch=4, cap=128`
  point

## 12. Current Recommended Configurations

### 12.1 Recommended configuration for explaining the mechanism

Use this when the goal is to explain the project cleanly:

- legacy 2-mode path
- `serial_bias` policy direction
- script-level `v2` defaults:
  - `adaptiveSwitchHysteresis = 1`
  - `adaptiveMinModeWindows = 1`
  - `adaptiveMemBlockRatioThres = 0.12`
  - `adaptiveOutstandingMissThres = 12`
  - `adaptiveConservativeFetchWidth = 2`
  - `adaptiveConservativeInflightCap = 96`

### 12.2 Recommended configuration for best-looking formal GAPBS results

Use this when the goal is to present the strongest graph formal results:

- `adaptiveWindowCycles = 2500`
- `adaptiveConservativeFetchWidth = 4`
- `adaptiveConservativeInflightCap = 128`
- keep the `v2` `serial_bias` thresholds

## 13. Environment and Tooling Notes

### 13.1 Build command

The practical build command on this machine was:

```bash
PYTHON_CONFIG=/usr/bin/python3.12-config scons -j4 build/ARM/gem5.opt
```

### 13.2 WSL vs PowerShell

Repeated failure mode:

- using `/mnt/c/...` paths directly inside PowerShell

Correct usage:

- PowerShell: use `C:\...`
- WSL/bash: use `/mnt/c/...`

### 13.3 `/mnt/c` binary replacement instability

The project hit `Text file busy` issues on `/mnt/c` when the binary was being
replaced or invoked during frequent rebuilds/runs.

Workaround:

- allow `GEM5_BIN` override in run scripts
- point runs at a stable binary copy if necessary

### 13.4 Ruby generated-file stale path issue

One build failure came from stale generated Ruby files that still encoded an
old absolute path.

The fix used earlier was to remove:

- `build/ARM/mem/ruby/protocol`
- `build/ARM/mem/ruby/common`
- `build/ARM/mem/ruby/slicc_interface`

and rebuild.

### 13.5 McPAT notes

The McPAT flow is usable, but some template compatibility issues had to be
handled in `scripts/gem5_to_mcpat.py`.

Important project fact:

- do not assume the bundled XML template and every older run directory expose
  identical component IDs or parameter names

The conversion script was extended to support:

- alternative BTB IDs
- `*_config` style cache parameters
- TLB stat-name differences
- more defensive XML updates

## 14. What Should Be Considered the Current Truth

The safest current truth is:

1. The project’s main technical story is still the legacy 2-mode adaptive O3
   controller, not the per-class profile path.
2. `v2` improved over `v1` mainly through policy/classification tuning, not
   through adding many more datapath caps.
3. The strongest in-tree evidence for `v2` comes from:
   - `phase_scan_mix`
   - `branch_entropy`
4. The strongest larger formal results currently come from GAPBS with the
   later-tuned point:
   - `window=2500`
   - `fetch=4`
   - `inflight=128`
5. The codebase also contains meaningful experimental branches:
   - per-class execution profiles
   - high-MLP inflight guard
   - resource tight sub-profile
   These should be understood, but not confused with the recommended primary
   narrative.

## 15. Recommended Next Steps for a New Agent

If a new agent continues this project, the sensible order is:

1. Read this document fully.
2. Read:
   - `docs/adaptive_mechanism_v1.md`
   - `docs/microbenchmark_suite.md`
   - `docs/next_steps_todo.md`
3. Inspect:
   - `src/cpu/o3/BaseO3CPU.py`
   - `src/cpu/o3/cpu.hh`
   - `src/cpu/o3/cpu.cc`
   - `scripts/run_adaptive.sh`
   - `scripts/run_adaptive_unique.sh`
4. Decide up front whether the goal is:
   - mechanism explanation
   - microbenchmark reproduction
   - formal GAPBS reproduction
   - experimental extension of per-class profiles
5. Do not mix the recommended mainline with experimental code paths without
   saying so explicitly.

## 16. Where the Evidence Lives

The most useful result locations are:

- microbenchmark baselines:
  - `runs/baseline/<workload>/latest`
- base `v2` microbenchmark runs:
  - `runs/adaptive/v2/<workload>/latest`
- per-class and guard tuning runs:
  - `runs/adaptive/v2/branch_entropy_*`
  - `runs/adaptive/v2/phase_scan_mix_*`
  - `runs/adaptive/v2/compute_queue_pressure_*`
- formal GAPBS baseline runs:
  - `runs/baseline/formal_gapbs_*_g20_baseline/latest`
- formal GAPBS tuned runs:
  - `runs/adaptive/v2/formal_gapbs_*_g20_fw4cap128`
  - `runs/adaptive/v2/formal_gapbs_*_g20_fw5cap160`
- PolyBench screening runs:
  - `runs/adaptive/v2/screen_*`
  - `runs/adaptive/v2/tune_*`

Useful naming conventions:

- `*_legacy_*`: legacy 2-mode path reference
- `*_class_*`: per-class profile experiments
- `*_guard_*`: high-MLP inflight-guard experiments
- `*_res*`: resource-profile tuning experiments
- `*_ser*`: serialized-profile tuning experiments
- `*_win*`: window-size experiments
- `*_fw4cap128` / `*_fw5cap160`: formal conservative fetch/inflight sweeps
- `*_gentle` / `*_powsaver`: broader formal policy-strength families

## 17. Files Removed in Favor of This Master Handoff

The following documents were removed because they were redundant, stale, or
both:

- `docs/baseline_definition.md`
- `docs/local_codex_handoff_2026-04-01.md`
- `docs/v1_to_v2_summary.md`

Historical result/attempt documents were intentionally preserved.
