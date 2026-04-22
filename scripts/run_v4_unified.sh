#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
source "${VENV_DIR}/bin/activate"

OUTBASE="${ROOT_DIR}/runs/v4_unified"

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

# Unified config — same params for ALL workloads
# Conservative: fw=5, cap=48, iq=24, lsq=24
# Deep: fw=3, squash>=0.25
# Adaptive window enabled
# Resource congestion: auto (code default)
PARAMS=(
    "system.cpu[0].adaptiveWindowAutoSize=True"
    "system.cpu[0].adaptiveMemBlockRatioThres=0.12"
    "system.cpu[0].adaptiveConservativeFetchWidth=5"
    "system.cpu[0].adaptiveConservativeInflightCap=48"
    "system.cpu[0].adaptiveConservativeIQCap=24"
    "system.cpu[0].adaptiveConservativeLSQCap=24"
    "system.cpu[0].adaptiveSerializedTightFetchWidth=3"
    "system.cpu[0].adaptiveSerializedTightSquashThres=0.25"
)

echo "=== V4 Unified Config (same params for all workloads) ==="

for wl in balanced_pipeline_stress phase_scan_mix branch_entropy serialized_pointer_chase compute_queue_pressure stream_cluster_reduce; do
    path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"
    [[ ! -f "${path}" ]] && continue
    cmd=(bash "${SCRIPT}" "${OUTBASE}/${wl}/latest" 50000000 2500 --workload "${path}")
    for p in "${PARAMS[@]}"; do cmd+=(--param "${p}"); done
    run_and_mcpat "${OUTBASE}/${wl}/latest" "${wl}" "${cmd[@]}"
done

for bench in bfs bc pr cc sssp tc; do
    path="${ROOT_DIR}/workloads/external/gapbs/${bench}"
    cmd=(bash "${SCRIPT}" "${OUTBASE}/gapbs_${bench}/latest" 50000000 2500 --workload "${path}" --workload-args "-g 20 -n 1")
    for p in "${PARAMS[@]}"; do cmd+=(--param "${p}"); done
    run_and_mcpat "${OUTBASE}/gapbs_${bench}/latest" "gapbs_${bench}" "${cmd[@]}"
done

echo "=== Done ==="
