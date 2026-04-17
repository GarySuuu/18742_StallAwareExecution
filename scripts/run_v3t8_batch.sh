#!/usr/bin/env bash
set -euo pipefail
#
# V3t8 batch: Run all 12 workloads with serialized-tight sub-level
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"

source "${VENV_DIR}/bin/activate"

V3T8="${ROOT_DIR}/runs/v3_multilevel/v3t8"

run_mcpat() {
    local run_dir="$1"
    local label="$2"
    local stats="${run_dir}/stats.txt"
    local config="${run_dir}/config.json"
    local xml_out="${run_dir}/mcpat.xml"
    local mcpat_out="${run_dir}/mcpat.out"
    if [[ -f "${mcpat_out}" ]] && [[ -s "${mcpat_out}" ]]; then
        echo "  [SKIP] McPAT ${label}"
        return 0
    fi
    if [[ ! -f "${stats}" ]] || [[ ! -f "${config}" ]]; then
        echo "  [MISS] ${label}"
        return 0
    fi
    echo "  [MCPAT] ${label}"
    python3 "${MCPAT_SCRIPT}" \
        --config "${config}" \
        --stats "${stats}" \
        --output "${xml_out}" \
        --template "${TEMPLATE}" \
        --run-mcpat \
        --mcpat-binary "${MCPAT_BIN}" \
        --mcpat-output "${mcpat_out}" 2>/dev/null || echo "    [WARN] McPAT failed for ${label}"
}

echo "============================================"
echo "  V3t8 Batch: Serialized-Tight Sub-Level"
echo "============================================"

# --- GAPBS benchmarks (window=2500) ---
echo ""
echo "--- GAPBS (window=2500, LightCons fw=5/cap=128, SerTight fw=4/cap=128) ---"
for bench in bfs bc cc pr sssp tc; do
    OUTDIR="${V3T8}/gapbs_${bench}/latest"
    echo "[RUN] gapbs_${bench}"
    bash "${SCRIPT}" "${OUTDIR}" 50000000 2500 \
        --workload "${ROOT_DIR}/workloads/external/gapbs/${bench}" \
        --workload-args "-g 20 -n 1" \
        --param "system.cpu[0].adaptiveLightConsFetchWidth=5" \
        --param "system.cpu[0].adaptiveLightConsInflightCap=128" \
        --param "system.cpu[0].adaptiveLightConsIQCap=0" \
        --param "system.cpu[0].adaptiveLightConsLSQCap=0" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=5" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=128" \
        --param "system.cpu[0].adaptiveConservativeIQCap=0" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=0" \
        --param "system.cpu[0].adaptiveSerializedTightFetchWidth=4" \
        --param "system.cpu[0].adaptiveSerializedTightInflightCap=128" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12" \
        2>&1 | tail -5
    run_mcpat "${OUTDIR}" "gapbs_${bench}"
    echo ""
done

# --- Micro benchmarks (window=5000, v3t3 params) ---
echo ""
echo "--- Micro benchmarks (window=5000, v3t3 params) ---"
MICRO_WORKLOADS=(
    "balanced_pipeline_stress"
    "phase_scan_mix"
    "branch_entropy"
    "serialized_pointer_chase"
    "compute_queue_pressure"
    "stream_cluster_reduce"
)
MICRO_PATHS=(
    "workloads/balanced_pipeline_stress/bin/arm/linux/balanced_pipeline_stress"
    "workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix"
    "workloads/branch_entropy/bin/arm/linux/branch_entropy"
    "workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase"
    "workloads/compute_queue_pressure/bin/arm/linux/compute_queue_pressure"
    "workloads/stream_cluster_reduce/bin/arm/linux/stream_cluster_reduce"
)

for i in "${!MICRO_WORKLOADS[@]}"; do
    wl="${MICRO_WORKLOADS[$i]}"
    wl_path="${ROOT_DIR}/${MICRO_PATHS[$i]}"
    OUTDIR="${V3T8}/${wl}/latest"
    echo "[RUN] ${wl}"
    bash "${SCRIPT}" "${OUTDIR}" 50000000 5000 \
        --workload "${wl_path}" \
        --conservative-fetch-width 6 \
        --conservative-inflight-cap 56 \
        --conservative-iq-cap 26 \
        --conservative-lsq-cap 28 \
        --param "system.cpu[0].adaptiveLightConsFetchWidth=6" \
        --param "system.cpu[0].adaptiveLightConsInflightCap=56" \
        --param "system.cpu[0].adaptiveLightConsIQCap=26" \
        --param "system.cpu[0].adaptiveLightConsLSQCap=28" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=6" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=56" \
        --param "system.cpu[0].adaptiveConservativeIQCap=26" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=28" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12" \
        2>&1 | tail -5
    run_mcpat "${OUTDIR}" "${wl}"
    echo ""
done

echo "============================================"
echo "  V3t8 Batch Completed"
echo "============================================"
