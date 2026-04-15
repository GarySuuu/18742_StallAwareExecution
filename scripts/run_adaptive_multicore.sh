#!/usr/bin/env bash
set -euo pipefail
#
# Run adaptive V2 with multiple cores (default 4).
# Each CPU gets its own independent adaptive controller.
# Window logs are per-CPU: adaptive_window_log.csv (cpu0),
# adaptive_window_log_cpu1.csv, adaptive_window_log_cpu2.csv, etc.
#
# Usage:
#   run_adaptive_multicore.sh [MAXINSTS] [WINDOW_CYCLES]
#   run_adaptive_multicore.sh [MAXINSTS] [WINDOW_CYCLES] --workload <path>
#   run_adaptive_multicore.sh [MAXINSTS] [WINDOW_CYCLES] --num-cores <N>
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
ADAPTIVE_VERSION="v2"
OUTDIR=""
MAXINSTS="50000000"
WINDOW_CYCLES="5000"
WORKLOAD_PATH="${ROOT_DIR}/tests/test-progs/hello/bin/arm/linux/hello"
WORKLOAD_ARGS=""
RUN_TAG=""
CUSTOM_OUTDIR="false"
NUM_CORES=4

# V2 defaults
CONSERVATIVE_FETCH_WIDTH="2"
CONSERVATIVE_INFLIGHT_CAP="96"
CONSERVATIVE_IQ_CAP="0"
CONSERVATIVE_LSQ_CAP="0"
CONSERVATIVE_RENAME_WIDTH="0"
CONSERVATIVE_DISPATCH_WIDTH="0"
DEFAULT_SWITCH_HYSTERESIS="1"
DEFAULT_MIN_MODE_WINDOWS="1"
DEFAULT_MEM_BLOCK_RATIO_THRES="0.12"
DEFAULT_OUTSTANDING_MISS_THRES="12"
ADAPTIVE_EXTRA_PARAMS=()

POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workload)                    WORKLOAD_PATH="$2"; shift 2 ;;
    --workload-args)               WORKLOAD_ARGS="$2"; shift 2 ;;
    --run-tag)                     RUN_TAG="$2"; shift 2 ;;
    --num-cores)                   NUM_CORES="$2"; shift 2 ;;
    --conservative-fetch-width)    CONSERVATIVE_FETCH_WIDTH="$2"; shift 2 ;;
    --conservative-inflight-cap)   CONSERVATIVE_INFLIGHT_CAP="$2"; shift 2 ;;
    --conservative-iq-cap)         CONSERVATIVE_IQ_CAP="$2"; shift 2 ;;
    --conservative-lsq-cap)        CONSERVATIVE_LSQ_CAP="$2"; shift 2 ;;
    --conservative-rename-width)   CONSERVATIVE_RENAME_WIDTH="$2"; shift 2 ;;
    --conservative-dispatch-width) CONSERVATIVE_DISPATCH_WIDTH="$2"; shift 2 ;;
    --param)                       ADAPTIVE_EXTRA_PARAMS+=("$2"); shift 2 ;;
    -h|--help)
      echo "Usage: run_adaptive_multicore.sh [MAXINSTS] [WINDOW_CYCLES] --workload <path> [--num-cores N]"
      exit 0 ;;
    *) POSITIONAL_ARGS+=("$1"); shift ;;
  esac
done
set -- "${POSITIONAL_ARGS[@]}"

if [[ $# -ge 1 ]]; then
  if [[ "${1}" =~ ^[0-9]+$ ]]; then
    MAXINSTS="${1}"
    [[ $# -ge 2 ]] && WINDOW_CYCLES="${2}"
  else
    OUTDIR="${1}"; CUSTOM_OUTDIR="true"
    [[ $# -ge 2 ]] && MAXINSTS="${2}"
    [[ $# -ge 3 ]] && WINDOW_CYCLES="${3}"
  fi
fi

derive_run_tag() {
  local tag="${2:-}"
  if [[ -n "${tag}" ]]; then
    printf '%s' "${tag}" | tr -cs 'A-Za-z0-9._-' '_'
    return
  fi
  local base; base="$(basename "$1")"; base="${base%.*}"
  printf '%s' "${base}" | tr -cs 'A-Za-z0-9._-' '_'
}

if [[ "${CUSTOM_OUTDIR}" != "true" ]]; then
  RUN_TAG="$(derive_run_tag "${WORKLOAD_PATH}" "${RUN_TAG}")"
  OUTDIR="${ROOT_DIR}/runs/adaptive/${ADAPTIVE_VERSION}/${RUN_TAG}_mc${NUM_CORES}/latest"
fi

GEM5_BIN="${ROOT_DIR}/build/ARM/gem5.opt"
[[ ! -f "${GEM5_BIN}" ]] && { echo "ERROR: ${GEM5_BIN} not found."; exit 1; }
[[ ! -f "${WORKLOAD_PATH}" ]] && { echo "ERROR: workload not found: ${WORKLOAD_PATH}"; exit 1; }
[[ ! -f "${VENV_DIR}/bin/activate" ]] && { echo "ERROR: ${VENV_DIR} not found."; exit 1; }

source "${VENV_DIR}/bin/activate"
export PYTHON_CONFIG=/usr/bin/python3.12-config
export PKG_CONFIG_PATH="$HOME/.local/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$HOME/.local/lib:${LD_LIBRARY_PATH:-}"
export TMPDIR="/tmp/${USER}-tmp"
mkdir -p "${TMPDIR}"

[[ -L "${OUTDIR}" ]] && rm -f "${OUTDIR}"
mkdir -p "${OUTDIR}"
find "${OUTDIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

chmod +x "${GEM5_BIN}"

GEM5_CMD=(
  "${GEM5_BIN}"
  "--outdir=${OUTDIR}"
  "${ROOT_DIR}/configs/deprecated/example/se.py"
  -n "${NUM_CORES}"
  --cpu-type=DerivO3CPU
  --caches --l2cache
  --mem-size=2GB
  "--maxinsts=${MAXINSTS}"
)

# Apply adaptive params to ALL CPUs
# Note: gem5 --param uses Python object paths, so cpu index must use brackets: system.cpu[N]
for i in $(seq 0 $((NUM_CORES - 1))); do
  GEM5_CMD+=(
    --param "system.cpu[${i}].enableStallAdaptive=True"
    --param "system.cpu[${i}].adaptiveWindowCycles=${WINDOW_CYCLES}"
    --param "system.cpu[${i}].adaptiveSwitchHysteresis=${DEFAULT_SWITCH_HYSTERESIS}"
    --param "system.cpu[${i}].adaptiveMinModeWindows=${DEFAULT_MIN_MODE_WINDOWS}"
    --param "system.cpu[${i}].adaptiveConservativeFetchWidth=${CONSERVATIVE_FETCH_WIDTH}"
    --param "system.cpu[${i}].adaptiveConservativeInflightCap=${CONSERVATIVE_INFLIGHT_CAP}"
    --param "system.cpu[${i}].adaptiveConservativeIQCap=${CONSERVATIVE_IQ_CAP}"
    --param "system.cpu[${i}].adaptiveConservativeLSQCap=${CONSERVATIVE_LSQ_CAP}"
    --param "system.cpu[${i}].adaptiveConservativeRenameWidth=${CONSERVATIVE_RENAME_WIDTH}"
    --param "system.cpu[${i}].adaptiveConservativeDispatchWidth=${CONSERVATIVE_DISPATCH_WIDTH}"
    --param "system.cpu[${i}].adaptiveMemBlockRatioThres=${DEFAULT_MEM_BLOCK_RATIO_THRES}"
    --param "system.cpu[${i}].adaptiveOutstandingMissThres=${DEFAULT_OUTSTANDING_MISS_THRES}"
  )
done

GEM5_CMD+=(-c "${WORKLOAD_PATH}")

if [[ -n "${WORKLOAD_ARGS}" ]]; then
  GEM5_CMD+=(--options="${WORKLOAD_ARGS}")
fi

# Apply extra params (user must specify full cpu index)
for extra_param in "${ADAPTIVE_EXTRA_PARAMS[@]}"; do
  GEM5_CMD+=(--param "${extra_param}")
done

echo "=== Multicore Adaptive V2 (${NUM_CORES} cores) ==="
echo "Workload: ${WORKLOAD_PATH}"
echo "MaxInsts: ${MAXINSTS}"
echo "Window: ${WINDOW_CYCLES} cycles"
echo "Output: ${OUTDIR}"
echo

"${GEM5_CMD[@]}" 2>&1 | tee "${OUTDIR}/run.log"

{
  echo "num_cores=${NUM_CORES}"
  echo "maxinsts=${MAXINSTS}"
  echo "window_cycles=${WINDOW_CYCLES}"
  echo "conservative_fetch_width=${CONSERVATIVE_FETCH_WIDTH}"
  echo "conservative_inflight_cap=${CONSERVATIVE_INFLIGHT_CAP}"
  echo "workload_path=${WORKLOAD_PATH}"
  echo "workload_args=${WORKLOAD_ARGS}"
  echo "run_tag=${RUN_TAG:-custom_outdir}"
  printf 'cmd='
  printf '%q ' "${GEM5_CMD[@]}"
  echo
} > "${OUTDIR}/run_meta.txt"

echo
echo "Multicore adaptive run completed."
echo "Output dir: ${OUTDIR}"
echo "Window logs:"
for i in $(seq 0 $((NUM_CORES - 1))); do
  if [[ $i -eq 0 ]]; then
    log="${OUTDIR}/adaptive_window_log.csv"
  else
    log="${OUTDIR}/adaptive_window_log_cpu${i}.csv"
  fi
  if [[ -f "$log" ]]; then
    echo "  CPU ${i}: ${log}"
  fi
done
echo
echo "Key stats:"
grep -E "simInsts|simTicks|simSeconds" "${OUTDIR}/stats.txt" | head -5 || true
