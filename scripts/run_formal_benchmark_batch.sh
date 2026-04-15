#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MAXINSTS="${MAXINSTS:-50000000}"
WINDOW_CYCLES="${WINDOW_CYCLES:-5000}"
GEM5_BIN="${GEM5_BIN:-${ROOT_DIR}/build/ARM/gem5.opt}"

run_pair() {
  local name="$1"
  local workload="$2"
  local args="${3:-}"

  echo
  echo "=== ${name}: baseline ==="
  if [[ -n "${args}" ]]; then
    GEM5_BIN="${GEM5_BIN}" "${ROOT_DIR}/scripts/run_baseline.sh" "${MAXINSTS}" \
      --workload "${workload}" \
      --workload-args "${args}" \
      --run-tag "${name}_baseline"
  else
    GEM5_BIN="${GEM5_BIN}" "${ROOT_DIR}/scripts/run_baseline.sh" "${MAXINSTS}" \
      --workload "${workload}" \
      --run-tag "${name}_baseline"
  fi

  echo
  echo "=== ${name}: adaptive v2 ==="
  if [[ -n "${args}" ]]; then
    GEM5_BIN="${GEM5_BIN}" "${ROOT_DIR}/scripts/run_adaptive_unique.sh" "${MAXINSTS}" "${WINDOW_CYCLES}" \
      --workload "${workload}" \
      --workload-args "${args}" \
      --run-tag "${name}_v2"
  else
    GEM5_BIN="${GEM5_BIN}" "${ROOT_DIR}/scripts/run_adaptive_unique.sh" "${MAXINSTS}" "${WINDOW_CYCLES}" \
      --workload "${workload}" \
      --run-tag "${name}_v2"
  fi
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "ERROR: missing required binary: $1"
    echo "The build step did not produce the expected binary."
    exit 1
  fi
}

"${ROOT_DIR}/scripts/build_formal_benchmarks.sh"

require_file "${ROOT_DIR}/workloads/external/gapbs/bfs"
require_file "${ROOT_DIR}/workloads/external/gapbs/bc"
require_file "${ROOT_DIR}/workloads/external/gapbs/pr"
require_file "${ROOT_DIR}/workloads/external/polybench-c/build-arm/atax/atax"
require_file "${ROOT_DIR}/workloads/external/polybench-c/build-arm/bicg/bicg"
require_file "${ROOT_DIR}/workloads/external/polybench-c/build-arm/jacobi-2d/jacobi-2d"

run_pair "formal_gapbs_bfs" \
  "${ROOT_DIR}/workloads/external/gapbs/bfs" \
  "-g 20 -n 1"

run_pair "formal_gapbs_bc" \
  "${ROOT_DIR}/workloads/external/gapbs/bc" \
  "-g 20 -n 1"

run_pair "formal_gapbs_pr" \
  "${ROOT_DIR}/workloads/external/gapbs/pr" \
  "-g 20 -n 1 -i 10 -t 1e-4"

run_pair "formal_polybench_atax" \
  "${ROOT_DIR}/workloads/external/polybench-c/build-arm/atax/atax"

run_pair "formal_polybench_bicg" \
  "${ROOT_DIR}/workloads/external/polybench-c/build-arm/bicg/bicg"

run_pair "formal_polybench_jacobi_2d" \
  "${ROOT_DIR}/workloads/external/polybench-c/build-arm/jacobi-2d/jacobi-2d"

echo
echo "All six benchmark pairs completed."
echo "Baseline results are under runs/baseline/*_baseline/latest"
echo "Adaptive results are under runs/adaptive/v2/*_v2/archive/"
