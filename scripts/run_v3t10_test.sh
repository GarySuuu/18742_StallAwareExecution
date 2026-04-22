#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
BASELINE_SCRIPT="${ROOT_DIR}/scripts/run_baseline.sh"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
OUTBASE="${ROOT_DIR}/runs/v3_multilevel/v3t10"

source "${VENV_DIR}/bin/activate"

run_and_mcpat() {
    local outdir="$1"; local label="$2"; shift 2
    if [[ -f "${outdir}/mcpat.out" ]] && [[ -s "${outdir}/mcpat.out" ]]; then
        echo "  [SKIP] ${label}"; return 0
    fi
    echo "  [RUN]  ${label}"
    "$@" 2>&1 | tail -3
    if [[ -f "${outdir}/config.json" ]]; then
        python3 "${MCPAT_SCRIPT}" --config "${outdir}/config.json" --stats "${outdir}/stats.txt" \
            --output "${outdir}/mcpat.xml" --template "${TEMPLATE}" \
            --run-mcpat --mcpat-binary "${MCPAT_BIN}" --mcpat-output "${outdir}/mcpat.out" 2>/dev/null || true
    fi
}

echo "=== V3t10: Resource congestion sub-level ==="

# Micro (window=5000, conservative params for Serialized windows)
for wl in balanced_pipeline_stress phase_scan_mix branch_entropy serialized_pointer_chase compute_queue_pressure stream_cluster_reduce; do
    path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"
    [[ ! -f "${path}" ]] && continue
    run_and_mcpat "${OUTBASE}/${wl}/latest" "micro ${wl}" \
        bash "${SCRIPT}" "${OUTBASE}/${wl}/latest" 50000000 5000 \
        --workload "${path}" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=6" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=56" \
        --param "system.cpu[0].adaptiveConservativeIQCap=26" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=28" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12"
done

# GAPBS (window=2500, conservative params for Serialized windows)
for bench in bfs bc pr cc sssp tc; do
    path="${ROOT_DIR}/workloads/external/gapbs/${bench}"
    run_and_mcpat "${OUTBASE}/gapbs_${bench}/latest" "gapbs ${bench}" \
        bash "${SCRIPT}" "${OUTBASE}/gapbs_${bench}/latest" 50000000 2500 \
        --workload "${path}" --workload-args "-g 20 -n 1" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=6" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=128" \
        --param "system.cpu[0].adaptiveConservativeIQCap=0" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=0" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12"
done

echo "=== Done ==="
