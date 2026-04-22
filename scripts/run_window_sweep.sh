#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
OUTBASE="${ROOT_DIR}/runs/v3_multilevel/win_sweep"

source "${VENV_DIR}/bin/activate"

WINDOWS=(1000 1500 2000 2500 3000 4000 5000 7500 10000)

# Representative workloads: 1 micro (phase_scan_mix has phases) + 2 GAPBS (tc + bfs)
declare -A WL_PATHS=(
    [phase_scan_mix]="${ROOT_DIR}/workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix"
    [branch_entropy]="${ROOT_DIR}/workloads/branch_entropy/bin/arm/linux/branch_entropy"
    [balanced_pipeline_stress]="${ROOT_DIR}/workloads/balanced_pipeline_stress/bin/arm/linux/balanced_pipeline_stress"
)
declare -A WL_ARGS=()  # no args for micro

declare -A GAPBS_PATHS=(
    [gapbs_tc]="${ROOT_DIR}/workloads/external/gapbs/tc"
    [gapbs_bfs]="${ROOT_DIR}/workloads/external/gapbs/bfs"
    [gapbs_sssp]="${ROOT_DIR}/workloads/external/gapbs/sssp"
)

run_one() {
    local tag="$1" wl="$2" path="$3" win="$4" args="${5:-}"
    local outdir="${OUTBASE}/${wl}_win${win}/latest"

    if [[ -f "${outdir}/mcpat.out" ]] && [[ -s "${outdir}/mcpat.out" ]]; then
        echo "  [SKIP] ${wl}_win${win}"
        return 0
    fi

    echo "  [RUN]  ${wl}_win${win}"
    local cmd=(bash "${SCRIPT}" "${outdir}" 50000000 "${win}" --workload "${path}")
    [[ -n "${args}" ]] && cmd+=(--workload-args "${args}")
    # Use v3t10 conservative params
    cmd+=(--param "system.cpu[0].adaptiveConservativeFetchWidth=6")
    cmd+=(--param "system.cpu[0].adaptiveConservativeInflightCap=128")
    cmd+=(--param "system.cpu[0].adaptiveConservativeIQCap=0")
    cmd+=(--param "system.cpu[0].adaptiveConservativeLSQCap=0")
    cmd+=(--param "system.cpu[0].adaptiveMemBlockRatioThres=0.12")
    "${cmd[@]}" 2>&1 | tail -3

    if [[ -f "${outdir}/config.json" ]]; then
        python3 "${MCPAT_SCRIPT}" --config "${outdir}/config.json" --stats "${outdir}/stats.txt" \
            --output "${outdir}/mcpat.xml" --template "${TEMPLATE}" \
            --run-mcpat --mcpat-binary "${MCPAT_BIN}" --mcpat-output "${outdir}/mcpat.out" 2>/dev/null || true
    fi
}

echo "=== Window Size Sweep ==="

for win in "${WINDOWS[@]}"; do
    echo ""
    echo "--- Window = ${win} ---"
    for wl in "${!WL_PATHS[@]}"; do
        run_one "" "${wl}" "${WL_PATHS[$wl]}" "${win}"
    done
    for wl in "${!GAPBS_PATHS[@]}"; do
        run_one "" "${wl}" "${GAPBS_PATHS[$wl]}" "${win}" "-g 20 -n 1"
    done
done

echo ""
echo "=== Window Sweep Done ==="
