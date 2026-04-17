#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
BASELINE_SCRIPT="${ROOT_DIR}/scripts/run_baseline.sh"
MAXINSTS="50000000"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"

source "${VENV_DIR}/bin/activate"

declare -A MICRO_WL=(
    [balanced_pipeline_stress]="${ROOT_DIR}/workloads/balanced_pipeline_stress/bin/arm/linux/balanced_pipeline_stress"
    [phase_scan_mix]="${ROOT_DIR}/workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix"
    [branch_entropy]="${ROOT_DIR}/workloads/branch_entropy/bin/arm/linux/branch_entropy"
    [serialized_pointer_chase]="${ROOT_DIR}/workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase"
    [compute_queue_pressure]="${ROOT_DIR}/workloads/compute_queue_pressure/bin/arm/linux/compute_queue_pressure"
    [stream_cluster_reduce]="${ROOT_DIR}/workloads/stream_cluster_reduce/bin/arm/linux/stream_cluster_reduce"
)

GAPBS_BENCHMARKS=(bfs bc pr cc sssp tc)
GAPBS_DIR="${ROOT_DIR}/workloads/external/gapbs"
GAPBS_ARGS="-g 20 -n 1"

run_and_mcpat() {
    local outdir="$1"
    local label="$2"
    shift 2

    if [[ -f "${outdir}/mcpat.out" ]] && [[ -s "${outdir}/mcpat.out" ]]; then
        echo "  [SKIP] ${label}"
        return 0
    fi

    echo "  [RUN]  ${label}"
    "$@" 2>&1 | tail -3

    # Run McPAT
    if [[ -f "${outdir}/config.json" ]] && [[ -f "${outdir}/stats.txt" ]]; then
        python3 "${MCPAT_SCRIPT}" \
            --config "${outdir}/config.json" \
            --stats "${outdir}/stats.txt" \
            --output "${outdir}/mcpat.xml" \
            --template "${TEMPLATE}" \
            --run-mcpat \
            --mcpat-binary "${MCPAT_BIN}" \
            --mcpat-output "${outdir}/mcpat.out" 2>/dev/null || echo "    [WARN] McPAT failed"
    fi
}

OUTBASE="${ROOT_DIR}/runs/v3_multilevel"

echo "============================================"
echo "  V3 Multi-Level Test Suite"
echo "============================================"

# Microbenchmarks
for wl_name in "${!MICRO_WL[@]}"; do
    wl_path="${MICRO_WL[$wl_name]}"
    [[ ! -f "${wl_path}" ]] && continue

    echo ""
    echo ">>> ${wl_name} <<<"

    # Baseline
    outdir="${OUTBASE}/baseline/${wl_name}/latest"
    run_and_mcpat "${outdir}" "baseline ${wl_name}" \
        bash "${BASELINE_SCRIPT}" "${outdir}" "${MAXINSTS}" --workload "${wl_path}"

    # V3 multi-level (new code defaults: Resource→Light, Serialized/Control→Deep)
    outdir="${OUTBASE}/v3ml/${wl_name}/latest"
    run_and_mcpat "${outdir}" "v3ml ${wl_name}" \
        bash "${SCRIPT}" "${outdir}" "${MAXINSTS}" 5000 --workload "${wl_path}" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.08"
done

# GAPBS
for bench in "${GAPBS_BENCHMARKS[@]}"; do
    echo ""
    echo ">>> GAPBS-${bench} <<<"

    # Baseline
    outdir="${OUTBASE}/baseline/gapbs_${bench}/latest"
    run_and_mcpat "${outdir}" "baseline gapbs_${bench}" \
        bash "${BASELINE_SCRIPT}" "${outdir}" "${MAXINSTS}" \
        --workload "${GAPBS_DIR}/${bench}" --workload-args "${GAPBS_ARGS}"

    # V3 multi-level
    outdir="${OUTBASE}/v3ml/gapbs_${bench}/latest"
    run_and_mcpat "${outdir}" "v3ml gapbs_${bench}" \
        bash "${SCRIPT}" "${outdir}" "${MAXINSTS}" 5000 \
        --workload "${GAPBS_DIR}/${bench}" --workload-args "${GAPBS_ARGS}" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.08"
done

echo ""
echo "============================================"
echo "  All tests + McPAT completed"
echo "============================================"
