#!/usr/bin/env bash
set -euo pipefail
#
# V3 multi-level tuning runs.
# Fix: restore mem_block_ratio to 0.12 (0.08 was too aggressive for GAPBS).
# The multi-level code changes (LightCons for Resource) remain.
#

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
echo "  V3ml_t2: Resource=Aggressive, Serialized=Light, Control=Deep (mem_block=0.12)"
echo "============================================"

# Microbenchmarks
for wl_name in "${!MICRO_WL[@]}"; do
    wl_path="${MICRO_WL[$wl_name]}"
    [[ ! -f "${wl_path}" ]] && continue

    echo ""
    echo ">>> ${wl_name} <<<"

    outdir="${OUTBASE}/v3ml_t2/${wl_name}/latest"
    run_and_mcpat "${outdir}" "v3ml_t2 ${wl_name}" \
        bash "${SCRIPT}" "${outdir}" "${MAXINSTS}" 5000 --workload "${wl_path}" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12"
done

# GAPBS
for bench in "${GAPBS_BENCHMARKS[@]}"; do
    echo ""
    echo ">>> GAPBS-${bench} <<<"

    outdir="${OUTBASE}/v3ml_t2/gapbs_${bench}/latest"
    run_and_mcpat "${outdir}" "v3ml_t2 gapbs_${bench}" \
        bash "${SCRIPT}" "${outdir}" "${MAXINSTS}" 5000 \
        --workload "${GAPBS_DIR}/${bench}" --workload-args "${GAPBS_ARGS}" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12"
done

echo ""
echo "  Done."
