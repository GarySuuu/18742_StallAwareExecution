#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
ADAPTIVE_VERSION="v2"
GEM5_BIN="${GEM5_BIN:-${ROOT_DIR}/build/ARM/gem5.opt}"

MAXINSTS="50000000"
WINDOW_CYCLES="5000"
WORKLOAD_PATH="${ROOT_DIR}/tests/test-progs/hello/bin/arm/linux/hello"
WORKLOAD_ARGS=""
RUN_TAG=""
RUN_TIMESTAMP="$(date -Iseconds)"
RUN_TIMESTAMP_SAFE=""
OUTDIR_BASE="${ROOT_DIR}/runs/adaptive/${ADAPTIVE_VERSION}"
OUTDIR=""

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
    --workload)
      WORKLOAD_PATH="$2"
      shift 2
      ;;
    --workload-args)
      WORKLOAD_ARGS="$2"
      shift 2
      ;;
    --run-tag)
      RUN_TAG="$2"
      shift 2
      ;;
    --outdir-base)
      OUTDIR_BASE="$2"
      shift 2
      ;;
    --conservative-fetch-width)
      CONSERVATIVE_FETCH_WIDTH="$2"
      shift 2
      ;;
    --conservative-inflight-cap)
      CONSERVATIVE_INFLIGHT_CAP="$2"
      shift 2
      ;;
    --conservative-iq-cap)
      CONSERVATIVE_IQ_CAP="$2"
      shift 2
      ;;
    --conservative-lsq-cap)
      CONSERVATIVE_LSQ_CAP="$2"
      shift 2
      ;;
    --conservative-rename-width)
      CONSERVATIVE_RENAME_WIDTH="$2"
      shift 2
      ;;
    --conservative-dispatch-width)
      CONSERVATIVE_DISPATCH_WIDTH="$2"
      shift 2
      ;;
    --param)
      ADAPTIVE_EXTRA_PARAMS+=("$2")
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage:
  run_adaptive_unique.sh [MAXINSTS] [WINDOW_CYCLES] [options]

Options:
  --workload <path>                 Path to ARM binary (default: hello)
  --workload-args "<args>"          Arguments passed to the binary via gem5 --options
  --run-tag <name>                  Workload/run tag used for output folder naming
  --outdir-base <dir>               Base directory for outputs (default: runs/adaptive/v2)

  Legacy conservative knobs (used by the frozen v2 controller and by
  class-profile experiments only when adaptiveUseClassProfiles=False):
  --conservative-fetch-width <n>
  --conservative-inflight-cap <n>
  --conservative-iq-cap <n>
  --conservative-lsq-cap <n>
  --conservative-rename-width <n>
  --conservative-dispatch-width <n>

  Extra gem5 params:
  --param "system.cpu[0].foo=bar"   Can be repeated

Output layout (never overwrites):
  <outdir-base>/<run-tag>/archive/<timestamp>/
EOF
      exit 0
      ;;
    *)
      POSITIONAL_ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL_ARGS[@]}"

if [[ $# -ge 1 ]]; then
  MAXINSTS="${1}"
  if [[ $# -ge 2 ]]; then
    WINDOW_CYCLES="${2}"
  fi
fi

if [[ ! -f "${GEM5_BIN}" ]]; then
  echo "ERROR: gem5 binary not found: ${GEM5_BIN}"
  echo "Build first: scons build/ARM/gem5.opt -j4"
  exit 1
fi

if [[ ! -f "${WORKLOAD_PATH}" ]]; then
  echo "ERROR: workload not found: ${WORKLOAD_PATH}"
  exit 1
fi

derive_run_tag() {
  local workload_path="$1"
  local tag="${2:-}"
  if [[ -n "${tag}" ]]; then
    printf '%s' "${tag}" | tr -cs 'A-Za-z0-9._-' '_'
    return
  fi
  local base
  base="$(basename "${workload_path}")"
  base="${base%.*}"
  printf '%s' "${base}" | tr -cs 'A-Za-z0-9._-' '_'
}

RUN_TAG="$(derive_run_tag "${WORKLOAD_PATH}" "${RUN_TAG}")"
RUN_TIMESTAMP_SAFE="$(printf '%s' "${RUN_TIMESTAMP}" | tr -cs 'A-Za-z0-9._-' '_')"
OUTDIR="${OUTDIR_BASE}/${RUN_TAG}/archive/${RUN_TIMESTAMP_SAFE}"

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
  echo "ERROR: ${VENV_DIR} not found."
  echo "Create venv at ../.venv-gem5 first."
  exit 1
fi

source "${VENV_DIR}/bin/activate"

export PYTHON_CONFIG=/usr/bin/python3.12-config
export PKG_CONFIG_PATH="$HOME/.local/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$HOME/.local/lib:${LD_LIBRARY_PATH:-}"
export TMPDIR="/tmp/${USER}-tmp"
mkdir -p "${TMPDIR}"

mkdir -p "${OUTDIR}"

chmod +x "${GEM5_BIN}"

GEM5_CMD=(
  "${GEM5_BIN}"
  "--outdir=${OUTDIR}"
  "${ROOT_DIR}/configs/deprecated/example/se.py"
  -n 1
  --cpu-type=DerivO3CPU
  --caches --l2cache
  --mem-size=2GB
  "--maxinsts=${MAXINSTS}"
  --param "system.cpu[0].enableStallAdaptive=True"
  --param "system.cpu[0].adaptiveWindowCycles=${WINDOW_CYCLES}"
  --param "system.cpu[0].adaptiveSwitchHysteresis=${DEFAULT_SWITCH_HYSTERESIS}"
  --param "system.cpu[0].adaptiveMinModeWindows=${DEFAULT_MIN_MODE_WINDOWS}"
  --param "system.cpu[0].adaptiveConservativeFetchWidth=${CONSERVATIVE_FETCH_WIDTH}"
  --param "system.cpu[0].adaptiveConservativeInflightCap=${CONSERVATIVE_INFLIGHT_CAP}"
  --param "system.cpu[0].adaptiveConservativeIQCap=${CONSERVATIVE_IQ_CAP}"
  --param "system.cpu[0].adaptiveConservativeLSQCap=${CONSERVATIVE_LSQ_CAP}"
  --param "system.cpu[0].adaptiveConservativeRenameWidth=${CONSERVATIVE_RENAME_WIDTH}"
  --param "system.cpu[0].adaptiveConservativeDispatchWidth=${CONSERVATIVE_DISPATCH_WIDTH}"
  --param "system.cpu[0].adaptiveMemBlockRatioThres=${DEFAULT_MEM_BLOCK_RATIO_THRES}"
  --param "system.cpu[0].adaptiveOutstandingMissThres=${DEFAULT_OUTSTANDING_MISS_THRES}"
  -c "${WORKLOAD_PATH}"
)
if [[ -n "${WORKLOAD_ARGS}" ]]; then
  GEM5_CMD+=(--options="${WORKLOAD_ARGS}")
fi
for extra_param in "${ADAPTIVE_EXTRA_PARAMS[@]}"; do
  GEM5_CMD+=(--param "${extra_param}")
done

join_cmd() {
  local joined=""
  for token in "${GEM5_CMD[@]}"; do
    joined+=$(printf '%q ' "${token}")
  done
  printf '%s' "${joined% }"
}

emit_kv() {
  local key="$1"
  local value="$2"
  printf -- "- %s: %s\n" "${key}" "${value}"
}

"${GEM5_CMD[@]}" 2>&1 | tee "${OUTDIR}/run.log"

{
  echo "# Adaptive Mechanism ${ADAPTIVE_VERSION} Run Summary (unique outdir)"
  echo
  echo "## Run Information"
  emit_kv "timestamp" "${RUN_TIMESTAMP}"
  emit_kv "output directory" "$(readlink -f "${OUTDIR}" 2>/dev/null || printf '%s' "${OUTDIR}")"
  emit_kv "run tag" "${RUN_TAG}"
  emit_kv "full command line" "$(join_cmd)"
  emit_kv "workload path" "${WORKLOAD_PATH}"
  emit_kv "workload options" "${WORKLOAD_ARGS:-none}"
  emit_kv "ISA" "ARM"
  emit_kv "CPU model" "DerivO3CPU"
  emit_kv "mode" "SE"
  emit_kv "caches/l2cache" "enabled/enabled"
  emit_kv "mem-size" "2GB"
  emit_kv "maxinsts" "${MAXINSTS}"
  echo
  echo "## Adaptive Parameters (explicitly set by script)"
  emit_kv "adaptiveWindowCycles" "${WINDOW_CYCLES}"
  emit_kv "adaptiveSwitchHysteresis" "${DEFAULT_SWITCH_HYSTERESIS}"
  emit_kv "adaptiveMinModeWindows" "${DEFAULT_MIN_MODE_WINDOWS}"
  emit_kv "adaptiveConservativeFetchWidth" "${CONSERVATIVE_FETCH_WIDTH}"
  emit_kv "adaptiveConservativeInflightCap" "${CONSERVATIVE_INFLIGHT_CAP}"
  emit_kv "adaptiveConservativeIQCap" "${CONSERVATIVE_IQ_CAP}"
  emit_kv "adaptiveConservativeLSQCap" "${CONSERVATIVE_LSQ_CAP}"
  emit_kv "adaptiveConservativeRenameWidth" "${CONSERVATIVE_RENAME_WIDTH}"
  emit_kv "adaptiveConservativeDispatchWidth" "${CONSERVATIVE_DISPATCH_WIDTH}"
  emit_kv "adaptiveUseClassProfiles" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveSerializedFetchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveSerializedInflightCap" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveSerializedRenameWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveSerializedDispatchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveHighMLPFetchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveHighMLPInflightCap" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveHighMLPRenameWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveHighMLPDispatchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveControlFetchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveControlInflightCap" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveControlRenameWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveControlDispatchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveResourceFetchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveResourceInflightCap" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveResourceRenameWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveResourceDispatchWidth" "see Extra --param overrides or config.ini"
  emit_kv "adaptiveMemBlockRatioThres" "${DEFAULT_MEM_BLOCK_RATIO_THRES}"
  emit_kv "adaptiveOutstandingMissThres" "${DEFAULT_OUTSTANDING_MISS_THRES}"
  if [[ ${#ADAPTIVE_EXTRA_PARAMS[@]} -gt 0 ]]; then
    echo
    echo "## Extra --param overrides"
    for extra_param in "${ADAPTIVE_EXTRA_PARAMS[@]}"; do
      emit_kv "param" "${extra_param}"
    done
  fi
  echo
  echo "## Window-Level Output"
  if [[ -f "${OUTDIR}/adaptive_window_log.csv" ]]; then
    emit_kv "window log" "${OUTDIR}/adaptive_window_log.csv"
  else
    emit_kv "window log" "not found (run may have exited before first window write)"
  fi
} > "${OUTDIR}/adaptive_config_summary.md"

{
  echo "timestamp=${RUN_TIMESTAMP}"
  echo "outdir=${OUTDIR}"
  echo "outdir_base=${OUTDIR_BASE}"
  echo "maxinsts=${MAXINSTS}"
  echo "window_cycles=${WINDOW_CYCLES}"
  echo "workload_path=${WORKLOAD_PATH}"
  echo "workload_args=${WORKLOAD_ARGS}"
  echo "run_tag=${RUN_TAG}"
  printf 'cmd='
  printf '%q ' "${GEM5_CMD[@]}"
  echo
} > "${OUTDIR}/run_meta.txt"

echo
echo "Adaptive unique run completed."
echo "Output dir: ${OUTDIR}"
echo "Summary file: ${OUTDIR}/adaptive_config_summary.md"
if [[ -f "${OUTDIR}/adaptive_window_log.csv" ]]; then
  echo "Window log: ${OUTDIR}/adaptive_window_log.csv"
fi
echo "Key stats:"
grep -E "simInsts|simTicks|simSeconds|hostSeconds|system.cpu.ipc" "${OUTDIR}/stats.txt" || true
