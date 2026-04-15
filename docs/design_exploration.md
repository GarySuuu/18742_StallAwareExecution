# Design Exploration: What More Can We Add?

This document evaluates potential extensions to the adaptive O3 CPU mechanism,
ranked by expected impact and implementation feasibility.

---

## 1. DVFS Integration (Recommended -- High Impact, Medium Effort)

**Idea**: Dynamically scale CPU voltage/frequency based on workload class.

**Rationale**: When the classifier detects Serialized-memory phases, the CPU
spends most cycles stalling on cache misses. Reducing frequency during these
phases saves power with minimal performance impact (the CPU is waiting anyway).
Conversely, Resource/compute-bound phases should keep high frequency.

**Mapping**:
- Serialized-memory -> lower frequency (e.g., 0.5x-0.75x)
- Control-dominated  -> moderate reduction (e.g., 0.8x)
- HighMLP            -> keep high (memory parallelism benefits from fast issue)
- Resource/compute   -> keep max frequency

**gem5 Support**: gem5 has `DVFSHandler` and `SrcClockDomain` with runtime
frequency change support. The adaptive controller would call
`clk_domain->signalNewFrequency()` when mode switches occur.

**Implementation**:
1. Add parameters to `BaseO3CPU.py`:
   - `adaptiveDVFSEnabled` (Bool, default False)
   - `adaptiveSerializedFreqDivisor` (Unsigned, default 2)
   - `adaptiveControlFreqDivisor` (Unsigned, default 1)
2. In `adaptiveMaybeSwitch()`, after mode change, request DVFS transition
3. Wire up `SrcClockDomain` reference in CPU constructor
4. McPAT power model already accounts for frequency -- results would
   automatically reflect DVFS savings

**Expected Impact**: 15-30% additional power savings on memory-bound phases
with <2% extra performance loss. Combined with existing throttling, this
could push total energy savings past 25% on suitable workloads.

**Effort**: ~2-3 days. Requires understanding gem5's DVFS subsystem and
testing frequency transition latency behavior.

---

## 2. Shared-Resource-Aware Adaptation for Multicore (High Impact, Medium Effort)

**Idea**: Extend the per-CPU classifier to also consider shared resource
contention (L2 cache, memory bandwidth) in multicore configurations.

**Rationale**: The current classifier uses only per-CPU local signals. In a
4-core system with shared L2, one CPU's aggressive execution can pollute the
shared cache and degrade other CPUs. A contention-aware controller could
reduce all CPUs' aggressiveness when shared resources are saturated.

**Design**:
- Add a `SharedAdaptiveState` SimObject that monitors:
  - L2 miss rate (sampled from cache stats)
  - Memory bandwidth utilization (from memory controller stats)
  - Number of CPUs in aggressive vs conservative mode
- Each per-CPU `adaptiveClassifyWindow()` reads the shared state as an
  additional input signal
- When shared contention is high, bias classification toward conservative

**New Parameters**:
- `adaptiveSharedContentionEnabled` (Bool)
- `adaptiveL2MissRateThreshold` (Float) -- above this, bias toward conservative
- `adaptiveMemBWThreshold` (Float) -- memory bandwidth saturation threshold

**Expected Impact**: Prevents cache thrashing in multicore, potentially
5-10% energy improvement on top of per-CPU adaptation. Most impactful on
workloads with irregular memory access (GAPBS).

**Effort**: ~3-4 days. Requires adding a new SimObject and wiring it to
both the cache hierarchy and the per-CPU controllers.

---

## 3. Prefetcher Control (Medium Impact, Low Effort)

**Idea**: Toggle prefetcher behavior based on workload class.

**Rationale**: Hardware prefetching is wasteful for pointer-chasing
(Serialized class) because the access pattern is unpredictable. But
prefetching helps streaming workloads (HighMLP class). Disabling the
prefetcher during serialized phases saves cache bandwidth and power.

**Mapping**:
- Serialized -> disable prefetcher
- HighMLP    -> enable aggressive stride prefetcher
- Control    -> keep default
- Resource   -> keep default

**Implementation**:
1. Obtain reference to the L1D prefetcher from the CPU's cache port
2. In `adaptiveMaybeSwitch()`, call prefetcher enable/disable
3. gem5 prefetchers have an `enable` parameter that can be toggled

**Expected Impact**: 3-8% power savings on mixed workloads where
serialized and streaming phases alternate. Small performance improvement
from reduced cache pollution.

**Effort**: ~1 day. Simple if gem5 supports runtime prefetcher toggling;
otherwise need to check the prefetcher API.

---

## 4. Cache Way Partitioning for Multicore (Medium Impact, Medium Effort)

**Idea**: Dynamically partition shared L2 cache ways based on each CPU's
workload class.

**Rationale**: Serialized/HighMLP workloads have high cache sensitivity
(they benefit from more cache). Resource/compute workloads have low cache
sensitivity (they don't need much cache). Giving more L2 ways to
cache-sensitive CPUs improves overall system throughput.

**Design**:
- Serialized/HighMLP CPUs get 60-70% of L2 ways
- Resource/compute CPUs get 30-40%
- Dynamic reallocation when classifications change

**gem5 Support**: Cache way partitioning is possible through `CacheBlk` tag
policies and way-based partitioning schemes.

**Expected Impact**: 5-15% throughput improvement in heterogeneous
multicore workloads. Most impactful when mixing memory-bound and
compute-bound workloads across cores.

**Effort**: ~3-4 days. Requires implementing a partitioning controller
and connecting it to the adaptive classifier.

---

## 5. ML-Based Classification (Low-Med Impact, High Effort)

**Idea**: Replace the hand-tuned threshold decision tree with a trained
machine learning model.

**Rationale**: The current classifier uses 7 thresholds in a fixed decision
tree. Edge cases near threshold boundaries may be misclassified. A trained
model could capture nonlinear interactions between signals.

**Training Data**: The 154 existing V2 experiments provide window-level
classification data with labeled outcomes (IPC improvement or degradation
after mode switches).

**Options**:
- Decision tree (simple, C-embeddable, ~same complexity as current)
- Small lookup table (discretize 7 signals into bins, index a table)
- Tiny neural network (2 hidden layers of 8 nodes -- feasible in C++)

**Expected Impact**: 5-10% improvement in classification accuracy for
borderline windows. May not translate to large energy savings since
most windows are already correctly classified.

**Effort**: ~5-7 days. Training is straightforward; embedding the model
in gem5 C++ and ensuring no simulation overhead is the challenge.

---

## 6. Sub-Profile Refinement (Low-Med Impact, Low Effort)

**Idea**: Add more granular sub-modes within existing classes.

**Examples**:
- **Serialized**: Distinguish L1-miss-bound (moderate inflight, short
  latency) from L2-miss-bound (minimal inflight, long latency). The
  former benefits from moderate throttling; the latter from aggressive
  throttling plus potential DVFS.
- **Control**: Distinguish tight loops with rare mispredictions from
  chaotic branching. Only the latter needs throttling.

**Implementation**: Add additional threshold checks within each class
branch of `adaptiveClassifyWindow()`. Similar to the existing Resource
tight sub-profile mechanism.

**Expected Impact**: 3-5% improvement on specific workloads where the
current 4-class granularity is too coarse.

**Effort**: ~1-2 days per sub-profile. Low risk since it's extending
an existing pattern.

---

## Recommendation

For the most impactful next steps, I recommend this order:

1. **DVFS Integration** -- The highest energy-saving potential with
   well-understood implementation path in gem5.
2. **Shared-Resource-Aware Adaptation** -- Critical for making multicore
   results meaningful. Without this, 4-core runs are just 4 independent
   single-core controllers.
3. **Prefetcher Control** -- Quick win, low effort, measurable impact.

These three extensions together would transform the project from a
single-core pipeline throttling mechanism into a comprehensive
multicore power management system.
