#!/usr/bin/env bash
set -euo pipefail
#
# Parameter Sweep V2 - Dense sweep with non-uniform sampling
#
# Improvements over V1:
# - Width params (fw/rw/dw): full 1-8 sweep
# - IQ Cap: dense around sweet spot (20-28), sparse elsewhere
# - LSQ Cap: dense around sweet spot (20-28), sparse elsewhere
# - Inflight Cap: dense around sweet spot (56-72), sparse elsewhere
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKLOAD="${ROOT_DIR}/workloads/balanced_pipeline_stress/bin/arm/linux/balanced_pipeline_stress"
MAXINSTS="50000000"
WINDOW_CYCLES="5000"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"

FORCE_CONS_1="system.cpu[0].adaptiveMemBlockRatioThres=0.0"
FORCE_CONS_2="system.cpu[0].adaptiveOutstandingMissThres=9999"

run_one() {
    local tag="$1"
    shift

    # Skip if already completed
    local outdir="${ROOT_DIR}/runs/adaptive/v2/sweep_${tag}/latest/stats.txt"
    if [[ -f "${outdir}" ]]; then
        local existing_insts
        existing_insts=$(grep -m1 "simInsts" "${outdir}" | awk '{print $2}')
        if [[ "${existing_insts}" -ge 49000000 ]] 2>/dev/null; then
            echo "  [SKIP] sweep_${tag} already done (simInsts=${existing_insts})"
            return 0
        fi
    fi

    echo ""
    echo "================================================================"
    echo "  SWEEP: ${tag}"
    echo "================================================================"
    bash "${SCRIPT}" "${MAXINSTS}" "${WINDOW_CYCLES}" \
        --workload "${WORKLOAD}" \
        --run-tag "sweep_${tag}" \
        --param "${FORCE_CONS_1}" \
        --param "${FORCE_CONS_2}" \
        "$@" \
        2>&1 | tail -5
    echo "--- Done: ${tag} ---"
}

echo "============================================"
echo "  Parameter Sweep V2 - Dense"
echo "  50M instructions per experiment"
echo "============================================"

# ============================================================
# 1. Fetch Width: full 1-8
#    Disable inflight cap to remove upstream masking
# ============================================================
echo ""
echo ">>> GROUP 1: Fetch Width (1-8, inflight cap disabled) <<<"
for fw in 1 2 3 4 5 6 7 8; do
    run_one "fw${fw}" \
        --conservative-fetch-width "${fw}" \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 2. IQ Cap: dense around sweet spot 24, sparse elsewhere
#    Range: 8,12,16,20,22,24,26,28,30,32,40,48,0(off)
# ============================================================
echo ""
echo ">>> GROUP 2: IQ Cap (dense near sweet spot 24) <<<"
for iqcap in 8 12 16 20 22 24 26 28 30 32 40 48 0; do
    run_one "iqcap${iqcap}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap "${iqcap}" \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 3. LSQ Cap: dense around sweet spot 24, sparse elsewhere
#    Range: 4,8,10,12,14,16,18,20,22,24,26,28,0(off)
# ============================================================
echo ""
echo ">>> GROUP 3: LSQ Cap (dense near sweet spot 24) <<<"
for lsqcap in 4 8 10 12 14 16 18 20 22 24 26 28 0; do
    run_one "lsqcap${lsqcap}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap "${lsqcap}" \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 4. Inflight Cap (ROB): dense around sweet spot 64, sparse elsewhere
#    Range: 24,32,40,48,52,56,60,64,68,72,80,96,112,128,160,0(off)
# ============================================================
echo ""
echo ">>> GROUP 4: Inflight Cap / ROB (dense near sweet spot 64) <<<"
for cap in 24 32 40 48 52 56 60 64 68 72 80 96 112 128 160 0; do
    run_one "robcap${cap}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap "${cap}" \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 5. Rename Width: full 1-8
# ============================================================
echo ""
echo ">>> GROUP 5: Rename Width (1-8, fetch + inflight disabled) <<<"
for rw in 1 2 3 4 5 6 7 8; do
    run_one "rw${rw}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width "${rw}" \
        --conservative-dispatch-width 0
done

# ============================================================
# 6. Dispatch Width: full 1-8
# ============================================================
echo ""
echo ">>> GROUP 6: Dispatch Width (1-8, fetch + inflight disabled) <<<"
for dw in 1 2 3 4 5 6 7 8; do
    run_one "dw${dw}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width "${dw}"
done

echo ""
echo "============================================"
echo "  All dense sweeps completed."
echo "============================================"
