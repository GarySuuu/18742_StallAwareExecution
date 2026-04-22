#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
source "${VENV_DIR}/bin/activate"

run_and_mcpat() {
    local outdir="$1"; local label="$2"; shift 2
    if [[ -f "${outdir}/mcpat.out" ]] && [[ -s "${outdir}/mcpat.out" ]]; then
        echo "  [SKIP] ${label}"; return 0; fi
    echo "  [RUN]  ${label}"
    "$@" 2>&1 | tail -3
    if [[ -f "${outdir}/config.json" ]]; then
        python3 "${MCPAT_SCRIPT}" --config "${outdir}/config.json" --stats "${outdir}/stats.txt" \
            --output "${outdir}/mcpat.xml" --template "${TEMPLATE}" \
            --run-mcpat --mcpat-binary "${MCPAT_BIN}" --mcpat-output "${outdir}/mcpat.out" 2>/dev/null || true
    fi
}

MICRO_WL="balanced_pipeline_stress phase_scan_mix branch_entropy serialized_pointer_chase compute_queue_pressure stream_cluster_reduce"
GAPBS_WL="bfs bc pr cc sssp tc"

# Common: adaptive window, squash-proportional enabled
COMMON="system.cpu[0].adaptiveWindowAutoSize=True system.cpu[0].adaptiveSquashProportionalFW=1"

run_config() {
    local tag="$1"; shift
    local extra_params=("$@")
    local OUTBASE="${ROOT_DIR}/runs/v3_final/edp_${tag}"

    echo ""
    echo "=== Config ${tag} ==="

    for wl in ${MICRO_WL}; do
        local path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"
        [[ ! -f "${path}" ]] && continue
        local cmd=(bash "${SCRIPT}" "${OUTBASE}/${wl}/latest" 50000000 2500 --workload "${path}")
        for p in ${COMMON}; do cmd+=(--param "${p}"); done
        # Micro conservative params
        cmd+=(--param "system.cpu[0].adaptiveConservativeFetchWidth=5")
        cmd+=(--param "system.cpu[0].adaptiveConservativeInflightCap=48")
        cmd+=(--param "system.cpu[0].adaptiveConservativeIQCap=24")
        cmd+=(--param "system.cpu[0].adaptiveConservativeLSQCap=24")
        for p in "${extra_params[@]}"; do cmd+=(--param "${p}"); done
        run_and_mcpat "${OUTBASE}/${wl}/latest" "${tag} ${wl}" "${cmd[@]}"
    done

    for bench in ${GAPBS_WL}; do
        local path="${ROOT_DIR}/workloads/external/gapbs/${bench}"
        local cmd=(bash "${SCRIPT}" "${OUTBASE}/gapbs_${bench}/latest" 50000000 2500 --workload "${path}" --workload-args "-g 20 -n 1")
        for p in ${COMMON}; do cmd+=(--param "${p}"); done
        # GAPBS conservative params
        cmd+=(--param "system.cpu[0].adaptiveConservativeFetchWidth=5")
        cmd+=(--param "system.cpu[0].adaptiveConservativeInflightCap=96")
        cmd+=(--param "system.cpu[0].adaptiveConservativeIQCap=0")
        cmd+=(--param "system.cpu[0].adaptiveConservativeLSQCap=0")
        for p in "${extra_params[@]}"; do cmd+=(--param "${p}"); done
        run_and_mcpat "${OUTBASE}/gapbs_${bench}/latest" "${tag} gapbs_${bench}" "${cmd[@]}"
    done
}

# A: squash proportional only (mem_block=0.12)
run_config "A" "system.cpu[0].adaptiveMemBlockRatioThres=0.12"

# B: squash proportional + lower mem_block=0.10
run_config "B" "system.cpu[0].adaptiveMemBlockRatioThres=0.10"

# C: squash proportional + aggressive fw=7
run_config "C" "system.cpu[0].adaptiveMemBlockRatioThres=0.12" "system.cpu[0].adaptiveAggressiveFetchLimit=7"

# D: squash proportional + lower mem_block + aggressive fw=7
run_config "D" "system.cpu[0].adaptiveMemBlockRatioThres=0.10" "system.cpu[0].adaptiveAggressiveFetchLimit=7"

echo ""
echo "=== All EDP configs done ==="
