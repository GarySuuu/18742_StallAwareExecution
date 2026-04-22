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

# Common params for both configs
AUTO_WIN="system.cpu[0].adaptiveWindowAutoSize=True"
MEM_BLK="system.cpu[0].adaptiveMemBlockRatioThres=0.12"

# ================================================================
# Config WPE: optimized for WPE (conservative throttle, IPC priority)
# Conservative: fw=6, cap=128 (GAPBS) / cap=56,iq=26,lsq=28 (micro via congestion sub-level)
# Ser-tight: fw=4, threshold=0.30
# ================================================================
echo ""
echo "=== Config WPE-optimal (adaptive window + v3t10 params) ==="
OUTBASE="${ROOT_DIR}/runs/v3_final/wpe_opt"

for wl in ${MICRO_WL}; do
    path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"
    [[ ! -f "${path}" ]] && continue
    run_and_mcpat "${OUTBASE}/${wl}/latest" "wpe ${wl}" \
        bash "${SCRIPT}" "${OUTBASE}/${wl}/latest" 50000000 2500 --workload "${path}" \
        --param "${AUTO_WIN}" --param "${MEM_BLK}" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=6" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=56" \
        --param "system.cpu[0].adaptiveConservativeIQCap=26" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=28"
done

for bench in ${GAPBS_WL}; do
    path="${ROOT_DIR}/workloads/external/gapbs/${bench}"
    run_and_mcpat "${OUTBASE}/gapbs_${bench}/latest" "wpe gapbs_${bench}" \
        bash "${SCRIPT}" "${OUTBASE}/gapbs_${bench}/latest" 50000000 2500 \
        --workload "${path}" --workload-args "-g 20 -n 1" \
        --param "${AUTO_WIN}" --param "${MEM_BLK}" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=6" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=128" \
        --param "system.cpu[0].adaptiveConservativeIQCap=0" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=0"
done

# ================================================================
# Config EDP: optimized for EDP (more aggressive throttle, energy priority)
# Conservative: fw=5, cap=96 (more throttle than WPE config)
# Ser-tight: fw=3, threshold=0.25 (more windows get deep throttle)
# ================================================================
echo ""
echo "=== Config EDP-optimal (adaptive window + aggressive params) ==="
OUTBASE="${ROOT_DIR}/runs/v3_final/edp_opt"

for wl in ${MICRO_WL}; do
    path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"
    [[ ! -f "${path}" ]] && continue
    run_and_mcpat "${OUTBASE}/${wl}/latest" "edp ${wl}" \
        bash "${SCRIPT}" "${OUTBASE}/${wl}/latest" 50000000 2500 --workload "${path}" \
        --param "${AUTO_WIN}" --param "${MEM_BLK}" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=5" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=48" \
        --param "system.cpu[0].adaptiveConservativeIQCap=24" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=24" \
        --param "system.cpu[0].adaptiveSerializedTightFetchWidth=3" \
        --param "system.cpu[0].adaptiveSerializedTightSquashThres=0.25"
done

for bench in ${GAPBS_WL}; do
    path="${ROOT_DIR}/workloads/external/gapbs/${bench}"
    run_and_mcpat "${OUTBASE}/gapbs_${bench}/latest" "edp gapbs_${bench}" \
        bash "${SCRIPT}" "${OUTBASE}/gapbs_${bench}/latest" 50000000 2500 \
        --workload "${path}" --workload-args "-g 20 -n 1" \
        --param "${AUTO_WIN}" --param "${MEM_BLK}" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=5" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=96" \
        --param "system.cpu[0].adaptiveConservativeIQCap=0" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=0" \
        --param "system.cpu[0].adaptiveSerializedTightFetchWidth=3" \
        --param "system.cpu[0].adaptiveSerializedTightSquashThres=0.25"
done

echo ""
echo "=== Both configs done ==="
