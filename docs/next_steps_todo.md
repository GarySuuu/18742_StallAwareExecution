# Adaptive v1 Next-Step TODO

This file tracks what has already been done and what should happen next.

Status legend:
- `✅` done
- `⬜` not done yet

## 1. Past Project Status

- `✅` baseline reproducible flow is working
- `✅` adaptive v1 flow is working
- `✅` baseline and adaptive outputs are separated by workload
- `✅` config summary generation is working
- `✅` adaptive window log generation is working
- `✅` six microbenchmarks are implemented and runnable
- `✅` McPAT flow is working for baseline and adaptive outputs
- `✅` initial performance and energy comparison has been collected

## 2. Current Project Status

- `✅` adaptive run script now supports conservative-parameter ablation (`fetch width`, `in-flight cap`, extra `--param` overrides)
- `✅` first conservative-parameter ablation pass completed on `serialized_pointer_chase`
- `✅` first medium-length tuning pass completed on `phase_scan_mix`
- `✅` optional `adaptiveConservativeIQCap` parameter has been added in the code and script interface
- `✅` current best-balanced point moved beyond the original default adaptive configuration on `phase_scan_mix`
- `✅` current evidence suggests strong conservative throttling saves power but hurts performance too much for the current goal
- `✅` current evidence suggests `fetch width` is not the main lever on the tested conservative-friendly workloads
- `✅` IQ-cap build-and-test pass completed on `phase_scan_mix`
- `✅` first IQ-cap probe (`phase_scan_mix` 5M, `IQ56` / `IQ48`) showed no measurable change relative to default adaptive
- `✅` next conservative candidate knobs have been wired in: `LSQ cap`, `rename width`, `dispatch width`
- `✅` rebuild and test pass for the new candidate knobs completed
- `✅` first 10M `phase_scan_mix` sweep completed for `fetch8-neutral`, `LSQ12`, `rename4`, and `dispatch4`
- `✅` `rename4` and `dispatch4` improved over baseline, but neither beat the current default adaptive point
- `✅` current default adaptive remains the best-balanced result among the tested conservative knobs
- `✅` combination sweep completed for `default + rename4`, `default + dispatch4`, and `default + rename4 + dispatch4`
- `✅` `default + rename4` gave a very small extra energy/EDP gain over default, but the improvement is marginal and may not justify the added mechanism complexity
- `✅` first switching-policy sweep completed on `phase_scan_mix` 10M for `h1m1`, `h1m2`, `h2m1`, `ctrl_loose`, and `serial_bias`
- `✅` lowering `adaptiveSwitchHysteresis` from `2` to `1` consistently improved energy and EDP without giving up the small performance gain
- `✅` `ctrl_loose` improved over the original default point by keeping performance essentially flat while reducing energy further
- `✅` `serial_bias` is currently the strongest tested point on `phase_scan_mix` 10M: `simTicks -0.467%`, `IPC +0.469%`, `Runtime Dynamic Power -11.931%`, `Total Runtime Energy -11.082%`, `EDP -11.497%`
- `✅` current evidence suggests policy/classification tuning is a much stronger lever than adding more conservative datapath throttles
- `✅` follow-up validation completed for `serial_bias` on `phase_scan_mix` 50M and `branch_entropy` 50M
- `✅` `serial_bias` remained strong on longer and additional runs:
  - `phase_scan_mix` 50M vs baseline: `simTicks -1.051%`, `IPC +1.062%`, `Runtime Dynamic Power -17.065%`, `Total Runtime Energy -16.488%`, `EDP -17.366%`
  - `branch_entropy` 50M vs baseline: `simTicks -0.175%`, `IPC +0.175%`, `Runtime Dynamic Power -11.614%`, `Total Runtime Energy -11.262%`, `EDP -11.417%`
- `✅` `serial_bias` now looks strong enough to be treated as the leading candidate for the next evaluation pass

## 3. Priority TODO List

| Status | Priority | Task | Why it matters | Notes |
|---|---|---|---|---|
| `✅` | P0 | Reconsider which conservative-mode parameters should remain in the main design | This is the main feedback point from the interim report | Conclusion so far: policy/classification tuning matters more than extra datapath throttles |
| `✅` | P0 | Verify whether conservative `fetch width` control is worth keeping | It may require more datapath wiring and may not be the cleanest knob | Current evidence says it is not the main lever |
| `✅` | P0 | Freeze one main adaptive configuration for the next evaluation pass | We now have multiple tested candidates and need one primary point | `serial_bias` is now the leading candidate |
| `✅` | P0 | Check whether `serial_bias` remains strong on at least one additional workload/run length | Needed before making it the main story | Passed on `phase_scan_mix` 50M and `branch_entropy` 50M |
| `⬜` | P1 | Re-analyze the 6 workloads by category | Helps show where the mechanism helps and where it does not | Suggested groups: conservative-friendly, mixed, aggressive-friendly |
| `✅` | P1 | Add EDP to the evaluation summary | Power and performance need one combined metric | Use at least `EDP`, optionally `ED^2P` |
| `⬜` | P1 | Decide the final v1 mechanism scope | Prevents feature creep before final evaluation | Prefer a small policy-focused story centered on `serial_bias` rather than many knobs |
| `⬜` | P2 | Add one or two slightly more realistic workloads beyond the current microbenchmarks | Helps show the mechanism is not only working on toy cases | Keep this lightweight; no huge benchmark framework needed yet |
| `⬜` | P2 | Rewrite the final mechanism narrative around a simple and reproducible tradeoff | This will matter a lot for the final report | The story should be about a simple adaptive throttle, not many knobs |

## 4. Conservative-Mode Parameter Candidates

The project feedback suggests revisiting which architectural parameters are being tuned in conservative mode.

### Current parameters already in the design

| Status | Parameter | Recommendation | Reason |
|---|---|---|---|
| `⬜` | `in-flight instruction cap` | Keep as primary candidate | Simple, easy to explain, directly tied to throttling core pressure |
| `⬜` | `fetch width` | Re-evaluate carefully | Conceptually reasonable, but may be harder to justify as a clean practical knob |

### Additional parameters worth considering

| Status | Parameter | Recommendation | Why it may help |
|---|---|---|---|
| `⬜` | Effective `ROB` cap | Strong candidate | Directly limits total speculative in-flight work and is easy to connect to energy/performance tradeoff |
| `⬜` | Effective `IQ` cap or dispatch throttle | Strong candidate | Can reduce backend pressure without touching full front-end datapath width wiring |
| `⬜` | Effective `LQ/SQ` cap | Medium candidate | Useful if the target workloads are memory-pressure heavy and you want to limit speculative memory footprint |
| `⬜` | Rename / dispatch width throttle | Medium candidate | Similar goal to fetch throttling, but may be cleaner depending on where the control is easiest to implement |
| `⬜` | Commit width throttle | Low-to-medium candidate | Easy to reason about, but it may hurt performance too directly and may be too blunt |
| `⬜` | Branch predictor aggressiveness / speculation gating | Low candidate for v1 | Interesting, but likely too complex for the current stage if the goal is a simple and reproducible knob |
| `⬜` | Memory request issue throttle | Medium candidate | Could help in serialized-memory or speculative-memory-heavy cases, but may be harder to explain cleanly |

### Recommended order to evaluate parameters

1. `in-flight instruction cap`
2. effective `ROB` cap
3. effective `IQ` cap / dispatch throttle
4. `fetch width`
5. `LQ/SQ` cap

Reason:
- The first three are the simplest knobs for controlling speculation and resource pressure.
- `fetch width` is still valid to test, but it should probably not remain the main conservative-mode knob unless ablation proves it is clearly useful.
- `LQ/SQ` and memory-specific throttles are useful follow-up options if the main results remain too weak or too workload-specific.

## 5. Suggested Execution Order

1. Confirm whether `fetch width` should stay in the design.
2. Build an `in-flight-cap-only` version of conservative mode.
3. Run ablation against the current `in-flight + fetch-width` version.
4. Sweep a few conservative cap values.
5. Recompute performance, energy, and EDP across the 6 current workloads.
6. Decide the final v1 parameter set.
7. Only then add one or two more realistic workloads if needed.

## 6. Current Findings From Ablation And Policy Sweeps

- `serialized_pointer_chase` short-run ablation showed that:
  - with the current thresholds, many short runs never entered conservative mode
  - changing `fetch width` from `2` to `8` alone made no difference when the workload stayed aggressive
  - once the classification thresholds were relaxed, the workload did enter conservative mode
  - however, `in-flight cap = 96` was still effectively non-binding for this workload
  - lowering the cap to `8`, `6`, or `4` started to change behavior, but the first observed tradeoff was:
    - lower dynamic power
    - worse performance
    - slightly worse total energy

- This means the current bottleneck is not just “which conservative parameter exists”.
- The more immediate issue is:
  - whether the workload is classified into conservative mode early enough
  - and whether the chosen conservative cap is actually binding in practice

- `phase_scan_mix` 10M conservative-datapath sweep showed:
  - `rename4` and `dispatch4` are both reasonable knobs
  - but neither one beat the original default adaptive point
  - `default + rename4` gave only a very small extra EDP gain over default
  - this suggests extra conservative datapath knobs are second-order tuning knobs, not the main source of improvement

- `phase_scan_mix` 10M switching-policy sweep showed:
  - `h1m1` (`adaptiveSwitchHysteresis=1`, `adaptiveMinModeWindows=1`) beat the original default on power, energy, and EDP while keeping the small performance gain
  - `h1m2` (`adaptiveSwitchHysteresis=1`, `adaptiveMinModeWindows=2`) improved a bit further over `h1m1`
  - `h2m1` (`adaptiveSwitchHysteresis=2`, `adaptiveMinModeWindows=1`) regressed back toward the original default behavior
  - `ctrl_loose` (`h1m1` plus looser control thresholds) improved further and kept performance effectively unchanged
  - `serial_bias` (`h1m1` plus more serialized-memory-biased thresholds) is currently the strongest tested point on this workload

- Longer-run follow-up validation showed:
  - `serial_bias` on `phase_scan_mix` 50M strongly beat the original default point:
    - versus default: `simTicks -0.776%`, `IPC +0.782%`, `Runtime Dynamic Power -13.088%`, `Total Runtime Energy -12.600%`, `EDP -13.278%`
  - `serial_bias` on `branch_entropy` 50M also strongly beat the original default point:
    - versus default: `simTicks -0.261%`, `IPC +0.262%`, `Runtime Dynamic Power -10.771%`, `Total Runtime Energy -10.530%`, `EDP -10.764%`

- This means the strongest current lever is:
  - switching-policy responsiveness
  - followed by classification thresholds
  - not extra conservative datapath throttles
