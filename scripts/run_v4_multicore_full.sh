#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GEM5_BIN="${ROOT_DIR}/build/ARM/gem5.opt"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
MCPAT_SCRIPT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TEMPLATE="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
OUTBASE="${ROOT_DIR}/runs/v4_multicore"
MAXINSTS=50000000

source "${VENV_DIR}/bin/activate"
export PYTHON_CONFIG=/usr/bin/python3.12-config
export TMPDIR="/tmp/${USER}-tmp"; mkdir -p "${TMPDIR}"
chmod +x "${GEM5_BIN}"

V4_PARAMS=(
    "enableStallAdaptive=True"
    "adaptiveSwitchHysteresis=1"
    "adaptiveMinModeWindows=1"
    "adaptiveWindowAutoSize=True"
    "adaptiveMemBlockRatioThres=0.12"
    "adaptiveConservativeFetchWidth=5"
    "adaptiveConservativeInflightCap=48"
    "adaptiveConservativeIQCap=24"
    "adaptiveConservativeLSQCap=24"
    "adaptiveSerializedTightFetchWidth=3"
    "adaptiveSerializedTightSquashThres=0.25"
)

run_4core() {
    local wl_name="$1" wl_path="$2" wl_args="${3:-}" tag="$4"
    local mc_wl="${wl_path};${wl_path};${wl_path};${wl_path}"
    local outdir="${OUTBASE}/${wl_name}_${tag}/latest"

    if [[ -f "${outdir}/mcpat.out" ]] && [[ -s "${outdir}/mcpat.out" ]]; then
        echo "  [SKIP] ${wl_name}_${tag}"; return 0; fi

    echo "  [RUN] ${wl_name}_${tag}"
    [[ -d "${outdir}" ]] && rm -rf "${outdir}"
    mkdir -p "${outdir}"

    local CMD=("${GEM5_BIN}" "--outdir=${outdir}"
        "${ROOT_DIR}/configs/deprecated/example/se.py"
        -n 4 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB
        "--maxinsts=${MAXINSTS}")

    if [[ "${tag}" == "v4" ]]; then
        for i in 0 1 2 3; do
            for p in "${V4_PARAMS[@]}"; do
                CMD+=(--param "system.cpu[${i}].${p}")
            done
        done
    fi

    CMD+=(-c "${mc_wl}")
    [[ -n "${wl_args}" ]] && CMD+=(--options="${wl_args}")

    "${CMD[@]}" 2>&1 | tail -3

    # McPAT (per-core, using cpu0 stats)
    python3 "${MCPAT_SCRIPT}" --config "${outdir}/config.json" --stats "${outdir}/stats.txt" \
        --output "${outdir}/mcpat.xml" --template "${TEMPLATE}" \
        --num-cores 4 --run-mcpat --mcpat-binary "${MCPAT_BIN}" --mcpat-output "${outdir}/mcpat.out" 2>/dev/null \
        && echo "  McPAT OK" || echo "  McPAT FAILED"
}

echo "=== V4 4-Core Full Suite ==="

# Microbenchmarks
for wl in balanced_pipeline_stress phase_scan_mix branch_entropy serialized_pointer_chase compute_queue_pressure stream_cluster_reduce; do
    path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"
    [[ ! -f "${path}" ]] && { echo "MISSING: ${wl}"; continue; }
    run_4core "${wl}" "${path}" "" "baseline"
    run_4core "${wl}" "${path}" "" "v4"
done

# GAPBS - note: some may fail due to unimplemented syscalls in multicore SE mode
for bench in bfs bc pr cc sssp tc; do
    path="${ROOT_DIR}/workloads/external/gapbs/${bench}"
    [[ ! -f "${path}" ]] && continue
    run_4core "gapbs_${bench}" "${path}" "-g 20 -n 1" "baseline" || true
    run_4core "gapbs_${bench}" "${path}" "-g 20 -n 1" "v4" || true
done

echo "=== Done ==="
