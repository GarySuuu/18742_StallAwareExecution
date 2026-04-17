#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
MAXINSTS="50000000"
GAPBS_DIR="${ROOT_DIR}/workloads/external/gapbs"
GAPBS_ARGS="-g 20 -n 1"

BENCHMARKS=(bfs bc pr cc sssp tc)

run_config() {
    local tag="$1"
    local bench="$2"
    shift 2

    local full_tag="gapbs_${bench}_g20_${tag}"
    local outdir="${ROOT_DIR}/runs/adaptive/v3_compiled/${full_tag}/latest"

    if [[ -f "${outdir}/stats.txt" ]]; then
        local existing_insts
        existing_insts=$(grep -m1 "simInsts" "${outdir}/stats.txt" | awk '{print $2}')
        if [[ "${existing_insts}" -ge 49000000 ]] 2>/dev/null; then
            echo "  [SKIP] ${full_tag} (simInsts=${existing_insts})"
            return 0
        fi
    fi

    echo ""
    echo "================================================================"
    echo "  ${full_tag}"
    echo "================================================================"

    bash "${SCRIPT}" "${outdir}" "${MAXINSTS}" 5000 \
        --workload "${GAPBS_DIR}/${bench}" \
        --workload-args "${GAPBS_ARGS}" \
        "$@" \
        2>&1 | tail -5
    echo "--- Done: ${full_tag} ---"
}

echo "============================================"
echo "  V3 GAPBS Evaluation"
echo "============================================"

for bench in "${BENCHMARKS[@]}"; do
    echo ""
    echo ">>>>>>>>>> ${bench} <<<<<<<<<<"

    # V2 reference
    run_config "v2_ref" "${bench}" \
        --conservative-fetch-width 2 \
        --conservative-inflight-cap 96 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --param "system.cpu[0].adaptiveEmaAlpha=0.0"

    # V3 with EMA
    run_config "v3" "${bench}" \
        --conservative-fetch-width 6 \
        --conservative-inflight-cap 56 \
        --conservative-iq-cap 26 \
        --conservative-lsq-cap 28

    # V2 formal-tuned point (from handoff: window=2500, fw=4, cap=128)
    run_config "v2_tuned" "${bench}" \
        --conservative-fetch-width 4 \
        --conservative-inflight-cap 128 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --param "system.cpu[0].adaptiveEmaAlpha=0.0" \
        --param "system.cpu[0].adaptiveWindowCycles=2500"
done

echo ""
echo "============================================"
echo "  V3 GAPBS Evaluation Completed"
echo "============================================"
