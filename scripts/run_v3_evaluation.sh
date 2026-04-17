#!/usr/bin/env bash
set -euo pipefail
#
# V3 Evaluation: Sweet Spot Conservative Mode
#
# Runs V2 (old) and V3 (sweet spot) on all key workloads,
# then collects baseline/V2/V3 results for comparison.
#
# No recompilation needed - all changes are parameter overrides.
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
MAXINSTS="50000000"

# Workloads to test
declare -A WORKLOADS=(
    [balanced_pipeline_stress]="${ROOT_DIR}/workloads/balanced_pipeline_stress/bin/arm/linux/balanced_pipeline_stress"
    [phase_scan_mix]="${ROOT_DIR}/workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix"
    [branch_entropy]="${ROOT_DIR}/workloads/branch_entropy/bin/arm/linux/branch_entropy"
    [serialized_pointer_chase]="${ROOT_DIR}/workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase"
    [compute_queue_pressure]="${ROOT_DIR}/workloads/compute_queue_pressure/bin/arm/linux/compute_queue_pressure"
    [stream_cluster_reduce]="${ROOT_DIR}/workloads/stream_cluster_reduce/bin/arm/linux/stream_cluster_reduce"
)

# ============================================================
# V2 Configuration (current defaults in run_adaptive.sh)
# ============================================================
# fw=2, cap=96, iqcap=0, lsqcap=0
# hysteresis=1, minModeWindows=1
# memBlockRatioThres=0.12, outstandingMissThres=12

# ============================================================
# V3 Configuration (sweet spot from dense sweep)
# ============================================================
V3_FW=6
V3_CAP=56
V3_IQCAP=26
V3_LSQCAP=28
V3_WINDOW=5000

# Also test a few V3 variants
# V3a: sweet spot but with lower fetch width (more conservative)
V3A_FW=5
V3A_CAP=64
V3A_IQCAP=26
V3A_LSQCAP=28

# V3b: sweet spot with tighter limits (medium throttle)
V3B_FW=4
V3B_CAP=48
V3B_IQCAP=20
V3B_LSQCAP=24

run_config() {
    local tag="$1"
    local workload_name="$2"
    local workload_path="$3"
    shift 3

    local full_tag="${workload_name}_${tag}"
    local outdir="${ROOT_DIR}/runs/adaptive/v3/${full_tag}/latest"

    # Skip if already completed
    if [[ -f "${outdir}/stats.txt" ]]; then
        local existing_insts
        existing_insts=$(grep -m1 "simInsts" "${outdir}/stats.txt" | awk '{print $2}')
        if [[ "${existing_insts}" -ge 49000000 ]] 2>/dev/null; then
            echo "  [SKIP] ${full_tag} already done (simInsts=${existing_insts})"
            return 0
        fi
    fi

    echo ""
    echo "================================================================"
    echo "  ${full_tag}"
    echo "================================================================"

    # Use run_adaptive.sh but override outdir to v3 directory
    bash "${SCRIPT}" "${outdir}" "${MAXINSTS}" "${V3_WINDOW}" \
        --workload "${workload_path}" \
        "$@" \
        2>&1 | tail -5
    echo "--- Done: ${full_tag} ---"
}

echo "============================================"
echo "  V3 Evaluation Suite"
echo "  50M instructions per experiment"
echo "============================================"

for wl_name in "${!WORKLOADS[@]}"; do
    wl_path="${WORKLOADS[$wl_name]}"

    if [[ ! -f "${wl_path}" ]]; then
        echo "  [WARN] Workload not found: ${wl_path}, skipping"
        continue
    fi

    echo ""
    echo ">>>>>>>>>> Workload: ${wl_name} <<<<<<<<<<"

    # --- V2 baseline (current defaults) ---
    run_config "v2" "${wl_name}" "${wl_path}" \
        --conservative-fetch-width 2 \
        --conservative-inflight-cap 96 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0

    # --- V3 sweet spot ---
    run_config "v3" "${wl_name}" "${wl_path}" \
        --conservative-fetch-width ${V3_FW} \
        --conservative-inflight-cap ${V3_CAP} \
        --conservative-iq-cap ${V3_IQCAP} \
        --conservative-lsq-cap ${V3_LSQCAP} \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0

    # --- V3a variant (fw=5, cap=64) ---
    run_config "v3a" "${wl_name}" "${wl_path}" \
        --conservative-fetch-width ${V3A_FW} \
        --conservative-inflight-cap ${V3A_CAP} \
        --conservative-iq-cap ${V3A_IQCAP} \
        --conservative-lsq-cap ${V3A_LSQCAP} \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0

    # --- V3b variant (medium throttle: fw=4, cap=48) ---
    run_config "v3b" "${wl_name}" "${wl_path}" \
        --conservative-fetch-width ${V3B_FW} \
        --conservative-inflight-cap ${V3B_CAP} \
        --conservative-iq-cap ${V3B_IQCAP} \
        --conservative-lsq-cap ${V3B_LSQCAP} \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0

done

echo ""
echo "============================================"
echo "  V3 Evaluation Suite Completed"
echo "============================================"
echo ""
echo "Results in: runs/adaptive/v3/"
echo "Compare with baselines in: runs/baseline/"
echo "Compare with V2 in: runs/adaptive/v2/"
