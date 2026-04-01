# Microbenchmark Suite Results

This file summarizes the current six-workload microbenchmark suite and the baseline vs adaptive v1 results.

## 1. Microbenchmark Descriptions

### `serialized_pointer_chase`
- Program type: randomized pointer chasing
- Main behavior:
  - each access depends on the previous load result
  - memory-level parallelism is intentionally low
- Real-world situations:
  - linked structures
  - graph traversal
  - pointer-heavy indexes
  - dependency-heavy key-value lookups

### `branch_entropy`
- Program type: branch-heavy control-flow kernel
- Main behavior:
  - executes many pseudo-random branches
  - keeps the data footprint relatively small
- Real-world situations:
  - rule matching
  - request dispatch
  - policy checks
  - state-machine style code

### `hash_probe_chain`
- Program type: hash-table probe with collision chains
- Main behavior:
  - each lookup walks a dependent chain through a bucket
  - mixes serialized memory behavior with branch checks
- Real-world situations:
  - hash map lookups
  - cache directory probe paths
  - key-value store index traversal

### `phase_scan_mix`
- Program type: phase-changing analytics kernel
- Main behavior:
  - one phase is branch/filter heavy
  - one phase is stream/reduce heavy
- Real-world situations:
  - log filtering followed by aggregation
  - scan + summarize pipelines
  - mixed analytics stages with changing bottlenecks

### `stream_cluster_reduce`
- Program type: streaming multi-array reduction
- Main behavior:
  - performs long sequential passes over several arrays
  - keeps the backend busy with regular memory access
- Real-world situations:
  - analytics kernels
  - image processing
  - numerical scan/reduction loops

### `compute_queue_pressure`
- Program type: integer compute kernel with backend pressure
- Main behavior:
  - keeps several arithmetic dependency chains active
  - stresses issue/execute resources more than memory latency
- Real-world situations:
  - checksum-like kernels
  - compression-style integer loops
  - data-plane integer processing

## 2. Results and Brief Interpretation

Notes:
- lower `simTicks` is better
- higher `IPC` is better
- lower `Runtime Dynamic Power` is better
- lower `Total Runtime Energy` is better
- percentage values are adaptive v1 relative to baseline

| Benchmark | Baseline simInsts | Adaptive simInsts | Baseline simTicks | Adaptive simTicks | simTicks change | Baseline IPC | Adaptive IPC | IPC change | Baseline Power (W) | Adaptive Power (W) | Power change | Baseline Energy (J) | Adaptive Energy (J) | Energy change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `serialized_pointer_chase` | 50000001 | 50000000 | 30243344500 | 32036967000 | +5.931% | 0.826628 | 0.780349 | -5.599% | 133.3150 | 110.4900 | -17.121% | 4.322710 | 3.847850 | -10.985% |
| `branch_entropy` | 50000006 | 50000006 | 27463237500 | 27486974000 | +0.086% | 0.910308 | 0.909522 | -0.086% | 210.4070 | 208.4190 | -0.945% | 6.042540 | 5.993120 | -0.818% |
| `hash_probe_chain` | 50000005 | 50000005 | 49106787500 | 49106787500 | 0.000% | 0.509095 | 0.509095 | 0.000% | 83.5635 | 83.5982 | +0.042% | 4.575760 | 4.577460 | +0.037% |
| `phase_scan_mix` | 50000001 | 50000001 | 53578800500 | 53430313500 | -0.277% | 0.466602 | 0.467899 | +0.278% | 102.4640 | 97.7760 | -4.575% | 6.005140 | 5.738000 | -4.449% |
| `stream_cluster_reduce` | 50000004 | 50000004 | 48671767500 | 48671767500 | 0.000% | 0.513645 | 0.513645 | 0.000% | 61.3859 | 61.4161 | +0.049% | 3.455800 | 3.457270 | +0.043% |
| `compute_queue_pressure` | 50000000 | 50000000 | 10439559500 | 10439559500 | 0.000% | 2.394737 | 2.394737 | 0.000% | 247.6480 | 247.6840 | +0.015% | 2.685730 | 2.686100 | +0.014% |

Brief reading:

- `serialized_pointer_chase`
  - adaptive v1 reduces power and energy clearly
  - performance gets worse at the same time
  - this is a clear energy-saving tradeoff case

- `branch_entropy`
  - performance is almost unchanged, slightly worse
  - power and energy improve slightly

- `hash_probe_chain`
  - performance is unchanged
  - power and energy are also basically unchanged, slightly worse

- `phase_scan_mix`
  - performance improves slightly
  - power and energy also improve slightly
  - this is the best balanced result in the current suite

- `stream_cluster_reduce`
  - performance is unchanged
  - power and energy are basically unchanged, slightly worse

- `compute_queue_pressure`
  - performance is unchanged
  - power and energy are basically unchanged, slightly worse

## 3. Assessment

- adaptive v1 is not a universal improvement across all workloads
- it helps some patterns, but not all of them

- the main positive cases in the current suite are:
  - `serialized_pointer_chase`
  - `branch_entropy`
  - `phase_scan_mix`

- among them:
  - `serialized_pointer_chase` gives the strongest power reduction, but it also hurts performance the most
  - `phase_scan_mix` is the strongest overall result because it improves both performance and energy

- the remaining three workloads:
  - `hash_probe_chain`
  - `stream_cluster_reduce`
  - `compute_queue_pressure`
  show little or no benefit in the current setup

- the direct takeaway from this suite is:
  - adaptive v1 can help in some conservative-friendly or phase-changing cases
  - adaptive v1 does not yet show broad benefit across all tested behaviors
