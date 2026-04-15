#!/usr/bin/env bash
set -euo pipefail
#
# Run baseline (no adaptive) with 4 cores.
#
# Usage:
#   run_baseline_multicore.sh [MAXINSTS] --workload <path> [--workload-args "<args>"]
#   run_baseline_multicore.sh [MAXINSTS] --workload <path> --run-tag <name>
#   run_baseline_multicore.sh [MAXINSTS] --num-cores <N>
#

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
OUTDIR=""
MAXINSTS="50000000"
WORKLOAD_PATH="${ROOT_DIR}/tests/test-progs/hello/bin/arm/linux/hello"
WORKLOAD_ARGS=""
RUN_TAG=""
CUSTOM_OUTDIR="false"
NUM_CORES=4
GEM5_BIN="${ROOT_DIR}/build/ARM/gem5.opt"

POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workload)      WORKLOAD_PATH="$2"; shift 2 ;;
    --workload-args) WORKLOAD_ARGS="$2"; shift 2 ;;
    --run-tag)       RUN_TAG="$2"; shift 2 ;;
    --num-cores)     NUM_CORES="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: run_baseline_multicore.sh [MAXINSTS] --workload <path> [--num-cores N]"
      exit 0 ;;
    *) POSITIONAL_ARGS+=("$1"); shift ;;
  esac
done
set -- "${POSITIONAL_ARGS[@]}"

if [[ $# -ge 1 ]]; then
  if [[ "${1}" =~ ^[0-9]+$ ]]; then
    MAXINSTS="${1}"
  else
    OUTDIR="${1}"; CUSTOM_OUTDIR="true"
    [[ $# -ge 2 ]] && MAXINSTS="${2}"
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
  OUTDIR="${ROOT_DIR}/runs/baseline/${RUN_TAG}_mc${NUM_CORES}/latest"
fi

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
  -c "${WORKLOAD_PATH}"
)
if [[ -n "${WORKLOAD_ARGS}" ]]; then
  GEM5_CMD+=(--options="${WORKLOAD_ARGS}")
fi

echo "=== Multicore Baseline (${NUM_CORES} cores) ==="
echo "Workload: ${WORKLOAD_PATH}"
echo "MaxInsts: ${MAXINSTS}"
echo "Output: ${OUTDIR}"
echo

"${GEM5_CMD[@]}" 2>&1 | tee "${OUTDIR}/run.log"

{
  echo "num_cores=${NUM_CORES}"
  echo "maxinsts=${MAXINSTS}"
  echo "workload_path=${WORKLOAD_PATH}"
  echo "workload_args=${WORKLOAD_ARGS}"
  echo "run_tag=${RUN_TAG:-custom_outdir}"
  printf 'cmd='
  printf '%q ' "${GEM5_CMD[@]}"
  echo
} > "${OUTDIR}/run_meta.txt"

echo
echo "Multicore baseline run completed."
echo "Output dir: ${OUTDIR}"
echo "Key stats:"
for i in $(seq 0 $((NUM_CORES - 1))); do
  echo "--- CPU $i ---"
  grep -E "system.cpu${i}\.(ipc|cpi)" "${OUTDIR}/stats.txt" 2>/dev/null || \
  grep -E "system.cpu\.(ipc|cpi)" "${OUTDIR}/stats.txt" 2>/dev/null || true
done
