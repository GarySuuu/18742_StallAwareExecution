#!/usr/bin/env bash
set -euo pipefail
#
# Run McPAT on all V3 experiments + baselines to get power/energy data
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"

source "${VENV_DIR}/bin/activate"

run_mcpat() {
    local run_dir="$1"
    local label="$2"

    local stats="${run_dir}/stats.txt"
    local config="${run_dir}/config.json"
    local xml_out="${run_dir}/mcpat.xml"
    local mcpat_out="${run_dir}/mcpat.out"

    if [[ -f "${mcpat_out}" ]] && [[ -s "${mcpat_out}" ]]; then
        echo "  [SKIP] ${label} (mcpat.out exists)"
        return 0
    fi

    if [[ ! -f "${stats}" ]] || [[ ! -f "${config}" ]]; then
        echo "  [MISS] ${label} (stats.txt or config.ini missing)"
        return 0
    fi

    echo "  [RUN]  ${label}"
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
echo "  McPAT Batch: V3 Results"
echo "============================================"

# Microbenchmark baselines (v3 compiled)
echo ""
echo "--- Baselines (v3 compiled) ---"
for wl in balanced_pipeline_stress phase_scan_mix branch_entropy serialized_pointer_chase compute_queue_pressure stream_cluster_reduce; do
    run_mcpat "${ROOT_DIR}/runs/baseline_v3/${wl}/latest" "baseline_v3/${wl}"
done

# Microbenchmark V2/V3
echo ""
echo "--- Microbenchmarks V2/V3 ---"
for wl in balanced_pipeline_stress phase_scan_mix branch_entropy serialized_pointer_chase compute_queue_pressure stream_cluster_reduce; do
    for cfg in v2_ref v3_default v3_no_ema; do
        run_mcpat "${ROOT_DIR}/runs/adaptive/v3_compiled/${wl}_${cfg}/latest" "v3_compiled/${wl}_${cfg}"
    done
done

# GAPBS baselines (original)
echo ""
echo "--- GAPBS Baselines ---"
for bench in bfs bc pr cc sssp tc; do
    run_mcpat "${ROOT_DIR}/runs/baseline/formal_gapbs_${bench}_g20_baseline/latest" "baseline/gapbs_${bench}"
done

# GAPBS V2/V2t/V3
echo ""
echo "--- GAPBS V2/V2t/V3 ---"
for bench in bfs bc pr cc sssp tc; do
    for cfg in v2_ref v2_tuned v3; do
        run_mcpat "${ROOT_DIR}/runs/adaptive/v3_compiled/gapbs_${bench}_g20_${cfg}/latest" "v3_compiled/gapbs_${bench}_${cfg}"
    done
done

echo ""
echo "============================================"
echo "  McPAT Batch Completed"
echo "============================================"
