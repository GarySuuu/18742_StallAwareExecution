#!/usr/bin/env bash
set -euo pipefail
#
# Parameter Sensitivity Sweep
#
# For each new sensitivity benchmark, runs:
#   1. Baseline (no adaptive)
#   2. Adaptive V2 with all defaults
#   3. Adaptive V2 with only the target parameter changed
#
# This isolates the effect of individual parameters.
#
# Usage:
#   ./scripts/run_sensitivity_sweep.sh [MAXINSTS]
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAXINSTS="${1:-5000000}"
WINDOW_CYCLES="5000"

echo "=== Parameter Sensitivity Sweep ==="
echo "MAXINSTS=${MAXINSTS}"
echo "ROOT_DIR=${ROOT_DIR}"
echo

# Benchmark definitions: name, binary path, args, target parameter, test value
declare -A BENCHMARKS
declare -A BENCH_ARGS
declare -A BENCH_TARGET_PARAM
declare -A BENCH_TARGET_VALUE

BENCHMARKS[fetch_bandwidth_stress]="workloads/fetch_bandwidth_stress/bin/arm/linux/fetch_bandwidth_stress"
BENCH_ARGS[fetch_bandwidth_stress]="100000 1"
BENCH_TARGET_PARAM[fetch_bandwidth_stress]="system.cpu[0].adaptiveConservativeFetchWidth"
BENCH_TARGET_VALUE[fetch_bandwidth_stress]="2"

BENCHMARKS[iq_pressure_stress]="workloads/iq_pressure_stress/bin/arm/linux/iq_pressure_stress"
BENCH_ARGS[iq_pressure_stress]="50000 1"
BENCH_TARGET_PARAM[iq_pressure_stress]="system.cpu[0].adaptiveConservativeIQCap"
BENCH_TARGET_VALUE[iq_pressure_stress]="32"

BENCHMARKS[lsq_pressure_stress]="workloads/lsq_pressure_stress/bin/arm/linux/lsq_pressure_stress"
BENCH_ARGS[lsq_pressure_stress]="20000 3 1"
BENCH_TARGET_PARAM[lsq_pressure_stress]="system.cpu[0].adaptiveConservativeLSQCap"
BENCH_TARGET_VALUE[lsq_pressure_stress]="16"

BENCHMARKS[rename_dispatch_stress]="workloads/rename_dispatch_stress/bin/arm/linux/rename_dispatch_stress"
BENCH_ARGS[rename_dispatch_stress]="200000 1"
BENCH_TARGET_PARAM[rename_dispatch_stress]="system.cpu[0].adaptiveConservativeRenameWidth"
BENCH_TARGET_VALUE[rename_dispatch_stress]="2"

for bench in fetch_bandwidth_stress iq_pressure_stress lsq_pressure_stress rename_dispatch_stress; do
    workload="${ROOT_DIR}/${BENCHMARKS[$bench]}"
    args="${BENCH_ARGS[$bench]}"
    target_param="${BENCH_TARGET_PARAM[$bench]}"
    target_value="${BENCH_TARGET_VALUE[$bench]}"

    if [[ ! -f "${workload}" ]]; then
        echo "SKIP: ${bench} -- binary not found at ${workload}"
        echo "  Build with: cd workloads/${bench} && make"
        echo
        continue
    fi

    echo "========================================"
    echo "Benchmark: ${bench}"
    echo "Target parameter: ${target_param}=${target_value}"
    echo "========================================"
    echo

    # --- Run 1: Baseline ---
    echo "--- ${bench}: Baseline ---"
    "${ROOT_DIR}/scripts/run_baseline.sh" "${MAXINSTS}" \
        --workload "${workload}" \
        --workload-args "${args}" \
        --run-tag "${bench}"
    echo

    # --- Run 2: Adaptive V2 defaults ---
    echo "--- ${bench}: Adaptive V2 (defaults) ---"
    "${ROOT_DIR}/scripts/run_adaptive.sh" "${MAXINSTS}" "${WINDOW_CYCLES}" \
        --workload "${workload}" \
        --workload-args "${args}" \
        --run-tag "${bench}_adaptive_default"
    echo

    # --- Run 3: Adaptive V2 with target parameter active ---
    echo "--- ${bench}: Adaptive V2 (${target_param}=${target_value}) ---"
    "${ROOT_DIR}/scripts/run_adaptive.sh" "${MAXINSTS}" "${WINDOW_CYCLES}" \
        --workload "${workload}" \
        --workload-args "${args}" \
        --run-tag "${bench}_param_test" \
        --param "${target_param}=${target_value}"
    echo

    echo "${bench}: all 3 runs complete"
    echo
done

echo "=== Sensitivity sweep complete ==="
echo
echo "Compare results:"
echo "  python scripts/extract_all_results.py"
echo "  python scripts/generate_comparison_tables.py"
