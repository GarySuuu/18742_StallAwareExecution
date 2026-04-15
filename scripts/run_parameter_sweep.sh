#!/usr/bin/env bash
set -euo pipefail
#
# Parameter Sweep for Adaptive O3 CPU
#
# Sweeps key architectural parameters one at a time, with upstream masking
# parameters disabled to isolate each parameter's independent effect.
#
# Masking hierarchy (must understand before sweeping):
#   Inflight Cap  -->  IQ Cap
#                 -->  LSQ Cap
#                 -->  Fetch Width (indirect)
#   Fetch Width   -->  Rename Width
#                 -->  Dispatch Width
#   Branch mispredict rate  -->  all width params (high squash = low effective throughput)
#
# Strategy: when sweeping a downstream parameter, set upstream masking params to 0 (disabled).
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKLOAD="${ROOT_DIR}/workloads/balanced_pipeline_stress/bin/arm/linux/balanced_pipeline_stress"
MAXINSTS="50000000"
WINDOW_CYCLES="5000"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"

# Force ALL windows into conservative mode:
#   adaptiveMemBlockRatioThres=0.0  -> all windows pass step 1 (memory blocked)
#   adaptiveOutstandingMissThres=9999 -> outstanding misses never reach this,
#                                        so all windows fall to Serialized (not HighMLP)
#   Serialized -> Conservative in legacy 2-mode path
FORCE_CONS_1="system.cpu[0].adaptiveMemBlockRatioThres=0.0"
FORCE_CONS_2="system.cpu[0].adaptiveOutstandingMissThres=9999"

run_one() {
    local tag="$1"
    shift
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
    echo ""
}

echo "============================================"
echo "  Parameter Sweep - balanced_pipeline_stress"
echo "  50M instructions per experiment"
echo "============================================"

# ============================================================
# 1. Fetch Width sweep: 1, 2, 4, 8(baseline)
#    Disable inflight cap (=0) to remove upstream masking
# ============================================================
echo ""
echo ">>> SWEEP GROUP 1: Fetch Width (inflight cap disabled) <<<"
for fw in 1 2 4 8; do
    run_one "fw${fw}" \
        --conservative-fetch-width "${fw}" \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 2. IQ Cap sweep: 16, 24, 32, 48, 0(disabled)
#    Disable inflight cap (=0) to remove upstream masking
# ============================================================
echo ""
echo ">>> SWEEP GROUP 2: IQ Cap (inflight cap disabled) <<<"
for iqcap in 16 24 32 48 0; do
    run_one "iqcap${iqcap}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap "${iqcap}" \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 3. LSQ Cap sweep: 8, 12, 16, 24, 0(disabled)
#    Disable inflight cap (=0) to remove upstream masking
# ============================================================
echo ""
echo ">>> SWEEP GROUP 3: LSQ Cap (inflight cap disabled) <<<"
for lsqcap in 8 12 16 24 0; do
    run_one "lsqcap${lsqcap}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap "${lsqcap}" \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 4. Inflight Cap (ROB) sweep: 32, 48, 64, 96, 128, 0(disabled)
#    This is the top-level masking param -- no need to disable others
# ============================================================
echo ""
echo ">>> SWEEP GROUP 4: Inflight Cap / ROB <<<"
for cap in 32 48 64 96 128 0; do
    run_one "robcap${cap}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap "${cap}" \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width 0
done

# ============================================================
# 5. Rename Width sweep: 1, 2, 4, 8(baseline)
#    Disable inflight cap and fetch width to remove upstream masking
# ============================================================
echo ""
echo ">>> SWEEP GROUP 5: Rename Width (fetch width + inflight cap disabled) <<<"
for rw in 1 2 4 8; do
    run_one "rw${rw}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width "${rw}" \
        --conservative-dispatch-width 0
done

# ============================================================
# 6. Dispatch Width sweep: 1, 2, 4, 8(baseline)
#    Disable inflight cap and fetch width to remove upstream masking
# ============================================================
echo ""
echo ">>> SWEEP GROUP 6: Dispatch Width (fetch width + inflight cap disabled) <<<"
for dw in 1 2 4 8; do
    run_one "dw${dw}" \
        --conservative-fetch-width 0 \
        --conservative-inflight-cap 0 \
        --conservative-iq-cap 0 \
        --conservative-lsq-cap 0 \
        --conservative-rename-width 0 \
        --conservative-dispatch-width "${dw}"
done

# ============================================================
# 7. Combined: Fetch Width + Inflight Cap (practical operating points)
#    These are the two params actually used in V2 conservative mode
# ============================================================
echo ""
echo ">>> SWEEP GROUP 7: Combined Fetch Width + Inflight Cap <<<"
for fw in 2 4; do
    for cap in 64 96 128; do
        run_one "fw${fw}_cap${cap}" \
            --conservative-fetch-width "${fw}" \
            --conservative-inflight-cap "${cap}" \
            --conservative-iq-cap 0 \
            --conservative-lsq-cap 0 \
            --conservative-rename-width 0 \
            --conservative-dispatch-width 0
    done
done

echo ""
echo "============================================"
echo "  All sweeps completed."
echo "============================================"
