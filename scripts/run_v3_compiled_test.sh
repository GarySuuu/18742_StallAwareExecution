#!/usr/bin/env bash
set -euo pipefail
#
# V3 Compiled Test Suite
#
# Runs after gem5 recompile with V3 code changes (EMA smoothing + updated defaults).
# Tests the compiled V3 defaults (no --param overrides needed for conservative params).
#
# Also runs V2 config (explicit old params) for comparison.
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
BASELINE_SCRIPT="${ROOT_DIR}/scripts/run_baseline.sh"
MAXINSTS="50000000"

declare -A WORKLOADS=(
    [balanced_pipeline_stress]="${ROOT_DIR}/workloads/balanced_pipeline_stress/bin/arm/linux/balanced_pipeline_stress"
    [phase_scan_mix]="${ROOT_DIR}/workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix"
    [branch_entropy]="${ROOT_DIR}/workloads/branch_entropy/bin/arm/linux/branch_entropy"
    [serialized_pointer_chase]="${ROOT_DIR}/workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase"
    [compute_queue_pressure]="${ROOT_DIR}/workloads/compute_queue_pressure/bin/arm/linux/compute_queue_pressure"
    [stream_cluster_reduce]="${ROOT_DIR}/workloads/stream_cluster_reduce/bin/arm/linux/stream_cluster_reduce"
)

run_config() {
    local tag="$1"
    local workload_name="$2"
    local workload_path="$3"
    shift 3

    local full_tag="${workload_name}_${tag}"
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
        --workload "${workload_path}" \
        "$@" \
        2>&1 | tail -5
    echo "--- Done: ${full_tag} ---"
}

run_baseline() {
    local workload_name="$1"
    local workload_path="$2"

    local outdir="${ROOT_DIR}/runs/baseline_v3/${workload_name}/latest"

    if [[ -f "${outdir}/stats.txt" ]]; then
        local existing_insts
        existing_insts=$(grep -m1 "simInsts" "${outdir}/stats.txt" | awk '{print $2}')
        if [[ "${existing_insts}" -ge 49000000 ]] 2>/dev/null; then
            echo "  [SKIP] baseline_v3 ${workload_name} (simInsts=${existing_insts})"
            return 0
        fi
    fi

    echo ""
    echo "================================================================"
    echo "  baseline_v3: ${workload_name}"
    echo "================================================================"

    bash "${BASELINE_SCRIPT}" "${outdir}" "${MAXINSTS}" \
        --workload "${workload_path}" \
        2>&1 | tail -5
    echo "--- Done: baseline_v3 ${workload_name} ---"
}

echo "============================================"
echo "  V3 Compiled Test Suite"
echo "  50M instructions per experiment"
echo "============================================"

for wl_name in "${!WORKLOADS[@]}"; do
    wl_path="${WORKLOADS[$wl_name]}"

    if [[ ! -f "${wl_path}" ]]; then
        echo "  [WARN] Missing: ${wl_path}"
        continue
    fi

    echo ""
    echo ">>>>>>>>>> ${wl_name} <<<<<<<<<<"

    # New baseline (with recompiled gem5, no adaptive)
    run_baseline "${wl_name}" "${wl_path}"

    # V3 compiled defaults (fw=6, cap=56, iqcap=26, lsqcap=28, EMA alpha=0.3)
    # No overrides needed - these are now the code defaults
    run_config "v3_default" "${wl_name}" "${wl_path}" \
        --conservative-fetch-width 6 \
        --conservative-inflight-cap 56 \
        --conservative-iq-cap 26 \
        --conservative-lsq-cap 28

    # V3 with EMA disabled (alpha=0) to isolate EMA effect
    run_config "v3_no_ema" "${wl_name}" "${wl_path}" \
        --conservative-fetch-width 6 \
        --conservative-inflight-cap 56 \
        --conservative-iq-cap 26 \
        --conservative-lsq-cap 28 \
        --param "system.cpu[0].adaptiveEmaAlpha=0.0"

    # V2 config for comparison (old params, EMA disabled)
    run_config "v2_ref" "${wl_name}" "${wl_path}" \
        --conservative-fetch-width 2 \
        --conservative-inflight-cap 96 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --param "system.cpu[0].adaptiveEmaAlpha=0.0"

done

echo ""
echo "============================================"
echo "  V3 Compiled Test Suite Completed"
echo "============================================"
