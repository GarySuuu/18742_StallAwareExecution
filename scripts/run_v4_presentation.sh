#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
GEM5_BIN="${ROOT_DIR}/build/ARM/gem5.opt"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
ADAPTIVE_SCRIPT="${ROOT_DIR}/scripts/run_adaptive.sh"
BASELINE_SCRIPT="${ROOT_DIR}/scripts/run_baseline.sh"

source "${VENV_DIR}/bin/activate"
export PYTHON_CONFIG=/usr/bin/python3.12-config
export TMPDIR="/tmp/${USER}-tmp"
mkdir -p "${TMPDIR}"

OUTBASE="${ROOT_DIR}/runs/v4_presentation"

# V4 unified params (for --param)
V4_PARAMS=(
    "system.cpu[IDX].adaptiveWindowAutoSize=True"
    "system.cpu[IDX].adaptiveMemBlockRatioThres=0.12"
    "system.cpu[IDX].adaptiveConservativeFetchWidth=5"
    "system.cpu[IDX].adaptiveConservativeInflightCap=48"
    "system.cpu[IDX].adaptiveConservativeIQCap=24"
    "system.cpu[IDX].adaptiveConservativeLSQCap=24"
    "system.cpu[IDX].adaptiveSerializedTightFetchWidth=3"
    "system.cpu[IDX].adaptiveSerializedTightSquashThres=0.25"
)

run_mcpat() {
    local outdir="$1"
    if [[ -f "${outdir}/config.json" ]] && [[ -f "${outdir}/stats.txt" ]]; then
        python3 "${MCPAT_SCRIPT}" --config "${outdir}/config.json" --stats "${outdir}/stats.txt" \
            --output "${outdir}/mcpat.xml" --template "${TEMPLATE}" \
            --run-mcpat --mcpat-binary "${MCPAT_BIN}" --mcpat-output "${outdir}/mcpat.out" 2>/dev/null || true
    fi
}

# ================================================================
# Part 1: Showcase workloads (single core, 50M instructions)
# ================================================================
echo "=== Part 1: Showcase Workloads ==="

for wl in adaptive_showcase_best adaptive_showcase_neutral; do
    path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"
    [[ ! -f "${path}" ]] && { echo "MISSING: ${path}"; continue; }

    # Baseline
    outdir="${OUTBASE}/showcase/${wl}_baseline/latest"
    if [[ ! -f "${outdir}/mcpat.out" ]]; then
        echo "  [RUN] baseline ${wl}"
        bash "${BASELINE_SCRIPT}" "${outdir}" 50000000 --workload "${path}" 2>&1 | tail -3
        run_mcpat "${outdir}"
    else
        echo "  [SKIP] baseline ${wl}"
    fi

    # V4 adaptive
    outdir="${OUTBASE}/showcase/${wl}_v4/latest"
    if [[ ! -f "${outdir}/mcpat.out" ]]; then
        echo "  [RUN] v4 ${wl}"
        cmd=(bash "${ADAPTIVE_SCRIPT}" "${outdir}" 50000000 2500 --workload "${path}")
        for p in "${V4_PARAMS[@]}"; do
            cmd+=(--param "${p//IDX/0}")
        done
        "${cmd[@]}" 2>&1 | tail -3
        run_mcpat "${outdir}"
    else
        echo "  [SKIP] v4 ${wl}"
    fi
done

# ================================================================
# Part 2: 4-core multicore experiment
# ================================================================
echo ""
echo "=== Part 2: 4-Core Multicore ==="

# Mixed workload: 4 different workloads on 4 cores
WL0="${ROOT_DIR}/workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase"
WL1="${ROOT_DIR}/workloads/branch_entropy/bin/arm/linux/branch_entropy"
WL2="${ROOT_DIR}/workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix"
WL3="${ROOT_DIR}/workloads/compute_queue_pressure/bin/arm/linux/compute_queue_pressure"
MC_WORKLOAD="${WL0};${WL1};${WL2};${WL3}"

MAXINSTS=50000000

# 4-core Baseline
outdir="${OUTBASE}/multicore/baseline_4core/latest"
if [[ ! -f "${outdir}/mcpat.out" ]]; then
    echo "  [RUN] 4-core baseline"
    [[ -d "${outdir}" ]] && rm -rf "${outdir}"
    mkdir -p "${outdir}"
    chmod +x "${GEM5_BIN}"
    "${GEM5_BIN}" "--outdir=${outdir}" \
        "${ROOT_DIR}/configs/deprecated/example/se.py" \
        -n 4 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB \
        "--maxinsts=${MAXINSTS}" \
        -c "${MC_WORKLOAD}" \
        2>&1 | tail -5
    run_mcpat "${outdir}"
else
    echo "  [SKIP] 4-core baseline"
fi

# 4-core V4 Adaptive
outdir="${OUTBASE}/multicore/v4_4core/latest"
if [[ ! -f "${outdir}/mcpat.out" ]]; then
    echo "  [RUN] 4-core V4 adaptive"
    [[ -d "${outdir}" ]] && rm -rf "${outdir}"
    mkdir -p "${outdir}"

    CMD=("${GEM5_BIN}" "--outdir=${outdir}"
        "${ROOT_DIR}/configs/deprecated/example/se.py"
        -n 4 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB
        "--maxinsts=${MAXINSTS}")

    # Enable adaptive for all 4 CPUs with V4 params
    for i in 0 1 2 3; do
        CMD+=(--param "system.cpu[${i}].enableStallAdaptive=True")
        CMD+=(--param "system.cpu[${i}].adaptiveSwitchHysteresis=1")
        CMD+=(--param "system.cpu[${i}].adaptiveMinModeWindows=1")
        for p in "${V4_PARAMS[@]}"; do
            CMD+=(--param "${p//IDX/${i}}")
        done
    done

    CMD+=(-c "${MC_WORKLOAD}")
    "${CMD[@]}" 2>&1 | tail -5
    run_mcpat "${outdir}"
else
    echo "  [SKIP] 4-core V4 adaptive"
fi

echo ""
echo "=== All presentation experiments done ==="
