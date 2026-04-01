# External Free Benchmark Resources

This file documents the two free external benchmark suites currently recommended
for this project beyond the in-tree six-workload microbenchmark suite:

- `PolyBench/C`
- `GAPBS`

These suites are not vendored into this repository. They should be cloned under
`gem5/workloads/external/` or another local path, then run through the existing
`scripts/run_baseline.sh` and `scripts/run_adaptive.sh` wrappers with
`--workload`, `--workload-args`, and optionally `--run-tag`.

## Why these two suites

### `PolyBench/C`

Official repo:

- `https://github.com/ferrandi/PolyBenchC`

Why it is a good fit:

- small kernels with straightforward ARM SE-mode bring-up
- easy to cross-compile into standalone user binaries
- useful for compute-heavy and streaming-memory comparisons
- fast enough for iterative baseline vs adaptive tuning

Recommended starting kernels:

- `atax`
- `bicg`
- `gemm`
- `jacobi-2d`

### `GAPBS`

Official repo:

- `https://github.com/sbeamer/gapbs`

Why it is a good fit:

- graph workloads with irregular memory access
- better proxy for pointer-heavy and traversal-heavy behavior than dense kernels
- useful complement to the in-tree serialized-memory and mixed-phase tests

Recommended starting kernels:

- `bfs`
- `bc`
- `pr`

## Expected local layout

Suggested directory layout under this repository:

```text
gem5/workloads/
  external/
    polybench-c/
    gapbs/
```

Example clone commands:

```bash
cd /home/rock/project/gem5/workloads
mkdir -p external
cd external

git clone https://github.com/ferrandi/PolyBenchC.git polybench-c
git clone https://github.com/sbeamer/gapbs.git gapbs
```

You can also keep these suites elsewhere and pass absolute paths to
`--workload`.

## Build guidance for ARM + gem5 SE mode

For this project, prefer:

- ARM Linux user binaries
- single-thread or otherwise simple user-space execution
- static linking when practical
- smaller inputs first, then scale up once the run path is validated

### `PolyBench/C` build example

The exact kernel set is upstream-defined. A practical example for `atax` is:

```bash
cd /home/rock/project/gem5/workloads/external/polybench-c
mkdir -p build-arm/atax

arm-none-linux-gnueabihf-gcc -O3 -static \
  utilities/polybench.c \
  linear-algebra/kernels/atax/atax.c \
  -I utilities \
  -I linear-algebra/kernels/atax \
  -o build-arm/atax/atax
```

For other kernels, reuse the same pattern with that kernel's source directory.

### `GAPBS` build example

Upstream supports selecting the compiler through `make`. For this project, use
an ARM cross C++ compiler, disable OpenMP, and prefer a static binary. A
practical starting point is:

```bash
cd /home/rock/project/gem5/workloads/external/gapbs
make clean
make SERIAL=1 \
  CXX=arm-none-linux-gnueabihf-g++ \
  CXX_FLAGS="-std=c++11 -O3 -Wall -static"
```

This keeps the binary away from the ARM dynamic loader path and avoids the
OpenMP runtime dependency, both of which make gem5 SE bring-up harder than it
needs to be for first-pass experiments.

## How to run through the existing scripts

The existing scripts already support arbitrary user binaries:

- `scripts/run_baseline.sh`
- `scripts/run_adaptive.sh`

### `PolyBench/C` example run

```bash
cd /home/rock/project/gem5

./scripts/run_baseline.sh 50000000 \
  --workload workloads/external/polybench-c/build-arm/atax/atax \
  --run-tag polybench_atax

./scripts/run_adaptive.sh 50000000 5000 \
  --workload workloads/external/polybench-c/build-arm/atax/atax \
  --run-tag polybench_atax
```

### `GAPBS` example run

```bash
cd /home/rock/project/gem5

./scripts/run_baseline.sh 50000000 \
  --workload workloads/external/gapbs/bfs \
  --workload-args "-g 20 -n 1" \
  --run-tag gapbs_bfs

./scripts/run_adaptive.sh 50000000 5000 \
  --workload workloads/external/gapbs/bfs \
  --workload-args "-g 20 -n 1" \
  --run-tag gapbs_bfs
```

## Which should you use first

Suggested order for this project:

1. Start with the in-tree six-workload suite for mechanism bring-up.
2. Add `PolyBench/C` for clean compute and streaming-memory kernels.
3. Add `GAPBS` for irregular-memory and graph-traversal behavior.

## Interpretation notes

- Keep ISA, CPU type, cache hierarchy, memory size, workload input, and
  `maxinsts` fixed within a comparison batch.
- Treat `PolyBench/C` as a clean extension of the current local suite, not a
  replacement for the current phase- and stall-oriented microbenchmarks.
- Treat `GAPBS` as a stress test for irregular access behavior; it is often
  more sensitive to build/runtime environment details than the local suite or
  many `PolyBench/C` kernels.
