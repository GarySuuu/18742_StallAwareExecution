#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
ADAPTIVE_VERSION="v2"
OUTDIR=""
MAXINSTS="50000000"
WINDOW_CYCLES="5000"
WORKLOAD_PATH="${ROOT_DIR}/tests/test-progs/hello/bin/arm/linux/hello"
WORKLOAD_ARGS=""
RUN_TAG=""
RUN_TIMESTAMP="$(date -Iseconds)"
SUMMARY_FILE=""
CUSTOM_OUTDIR="false"
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
  run_adaptive.sh [MAXINSTS] [WINDOW_CYCLES]
  run_adaptive.sh [OUTDIR] [MAXINSTS] [WINDOW_CYCLES]
  run_adaptive.sh [MAXINSTS] [WINDOW_CYCLES] --workload <path> [--workload-args "<args>"]
  run_adaptive.sh [OUTDIR] [MAXINSTS] [WINDOW_CYCLES] --workload <path> [--workload-args "<args>"]
  run_adaptive.sh [MAXINSTS] [WINDOW_CYCLES] --workload <path> --run-tag <name>
  run_adaptive.sh [MAXINSTS] [WINDOW_CYCLES] --conservative-fetch-width <n> --conservative-inflight-cap <n> --conservative-iq-cap <n>
  run_adaptive.sh [MAXINSTS] [WINDOW_CYCLES] --conservative-lsq-cap <n> --conservative-rename-width <n> --conservative-dispatch-width <n>
  run_adaptive.sh [MAXINSTS] [WINDOW_CYCLES] --param "system.cpu[0].foo=bar"
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
  if [[ "${1}" =~ ^[0-9]+$ ]]; then
    MAXINSTS="${1}"
    if [[ $# -ge 2 ]]; then
      WINDOW_CYCLES="${2}"
    fi
  else
    OUTDIR="${1}"
    CUSTOM_OUTDIR="true"
    if [[ $# -ge 2 ]]; then
      MAXINSTS="${2}"
    fi
    if [[ $# -ge 3 ]]; then
      WINDOW_CYCLES="${3}"
    fi
  fi
fi

if [[ ! -f "${ROOT_DIR}/build/ARM/gem5.opt" ]]; then
  echo "ERROR: ${ROOT_DIR}/build/ARM/gem5.opt not found."
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

if [[ "${CUSTOM_OUTDIR}" != "true" ]]; then
  RUN_TAG="$(derive_run_tag "${WORKLOAD_PATH}" "${RUN_TAG}")"
  OUTDIR="${ROOT_DIR}/runs/adaptive/${ADAPTIVE_VERSION}/${RUN_TAG}/latest"
fi

SUMMARY_FILE="${OUTDIR}/adaptive_config_summary.md"

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

if [[ -L "${OUTDIR}" ]]; then
  rm -f "${OUTDIR}"
fi
mkdir -p "${OUTDIR}"
find "${OUTDIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

chmod +x "${ROOT_DIR}/build/ARM/gem5.opt"

GEM5_CMD=(
  "${ROOT_DIR}/build/ARM/gem5.opt"
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

ini_get() {
  local section="$1"
  local key="$2"
  local ini_file="$3"
  awk -F= -v section="[${section}]" -v key="${key}" '
    $0 == section { in_section=1; next }
    /^\[/ { if (in_section) exit; in_section=0 }
    in_section && $1 == key {
      sub(/^[[:space:]]+/, "", $2)
      sub(/[[:space:]]+$/, "", $2)
      print $2
      found=1
      exit
    }
    END { if (!found) print "__NOT_FOUND__" }
  ' "${ini_file}"
}

ini_get_or_note() {
  local section="$1"
  local key="$2"
  local ini_file="$3"
  local value
  value="$(ini_get "${section}" "${key}" "${ini_file}")"
  if [[ "${value}" == "__NOT_FOUND__" ]]; then
    printf 'not directly found in config.ini'
  else
    printf '%s' "${value}"
  fi
}

emit_kv() {
  local key="$1"
  local value="$2"
  printf -- "- %s: %s\n" "${key}" "${value}"
}

generate_summary() {
  local ini_file="$1"
  local summary_file="$2"

  {
    echo "# Adaptive Mechanism ${ADAPTIVE_VERSION} Run Summary"
    echo
    echo "## Run Information"
    emit_kv "timestamp" "${RUN_TIMESTAMP}"
    emit_kv "full command line" "$(join_cmd)"
    emit_kv "output directory" "$(readlink -f "${OUTDIR}" 2>/dev/null || printf '%s' "${OUTDIR}")"
    emit_kv "workload path" "${WORKLOAD_PATH}"
    emit_kv "workload options" "${WORKLOAD_ARGS:-none}"
    emit_kv "run tag" "${RUN_TAG:-custom_outdir}"
    emit_kv "ISA" "ARM"
    emit_kv "CPU model" "DerivO3CPU"
    emit_kv "mode" "SE"
    emit_kv "caches/l2cache" "enabled/enabled"
    emit_kv "mem-size" "2GB"
    emit_kv "maxinsts" "${MAXINSTS}"
    emit_kv "requested conservative fetch width override" "${CONSERVATIVE_FETCH_WIDTH}"
    emit_kv "requested conservative inflight cap override" "${CONSERVATIVE_INFLIGHT_CAP}"
    emit_kv "requested conservative IQ cap override" "${CONSERVATIVE_IQ_CAP}"
    emit_kv "requested conservative LSQ cap override" "${CONSERVATIVE_LSQ_CAP}"
    emit_kv "requested conservative rename width override" "${CONSERVATIVE_RENAME_WIDTH}"
    emit_kv "requested conservative dispatch width override" "${CONSERVATIVE_DISPATCH_WIDTH}"
    if [[ ${#ADAPTIVE_EXTRA_PARAMS[@]} -gt 0 ]]; then
      emit_kv "extra adaptive params" "${ADAPTIVE_EXTRA_PARAMS[*]}"
    else
      emit_kv "extra adaptive params" "none"
    fi
    echo
    echo "## Classification to Mode Mapping (${ADAPTIVE_VERSION})"
    emit_kv "legacy note" "When adaptiveUseClassProfiles=False, serialized/control map to conservative and high-MLP/resource map to aggressive"
    emit_kv "profile note" "When adaptiveUseClassProfiles=True, target/applied mode names in the window log reflect the per-class execution profile"
    echo
    echo "## Adaptive Parameters (from config.ini)"
    emit_kv "enableStallAdaptive" "$(ini_get_or_note "system.cpu" "enableStallAdaptive" "${ini_file}")"
    emit_kv "adaptiveWindowCycles" "$(ini_get_or_note "system.cpu" "adaptiveWindowCycles" "${ini_file}")"
    emit_kv "adaptiveSwitchHysteresis" "$(ini_get_or_note "system.cpu" "adaptiveSwitchHysteresis" "${ini_file}")"
    emit_kv "adaptiveMinModeWindows" "$(ini_get_or_note "system.cpu" "adaptiveMinModeWindows" "${ini_file}")"
    emit_kv "adaptiveConservativeFetchWidth" "$(ini_get_or_note "system.cpu" "adaptiveConservativeFetchWidth" "${ini_file}")"
    emit_kv "adaptiveConservativeInflightCap" "$(ini_get_or_note "system.cpu" "adaptiveConservativeInflightCap" "${ini_file}")"
    emit_kv "adaptiveConservativeIQCap" "$(ini_get_or_note "system.cpu" "adaptiveConservativeIQCap" "${ini_file}")"
    emit_kv "adaptiveConservativeLSQCap" "$(ini_get_or_note "system.cpu" "adaptiveConservativeLSQCap" "${ini_file}")"
    emit_kv "adaptiveConservativeRenameWidth" "$(ini_get_or_note "system.cpu" "adaptiveConservativeRenameWidth" "${ini_file}")"
    emit_kv "adaptiveConservativeDispatchWidth" "$(ini_get_or_note "system.cpu" "adaptiveConservativeDispatchWidth" "${ini_file}")"
    emit_kv "adaptiveUseClassProfiles" "$(ini_get_or_note "system.cpu" "adaptiveUseClassProfiles" "${ini_file}")"
    emit_kv "adaptiveSerializedFetchWidth" "$(ini_get_or_note "system.cpu" "adaptiveSerializedFetchWidth" "${ini_file}")"
    emit_kv "adaptiveSerializedInflightCap" "$(ini_get_or_note "system.cpu" "adaptiveSerializedInflightCap" "${ini_file}")"
    emit_kv "adaptiveSerializedRenameWidth" "$(ini_get_or_note "system.cpu" "adaptiveSerializedRenameWidth" "${ini_file}")"
    emit_kv "adaptiveSerializedDispatchWidth" "$(ini_get_or_note "system.cpu" "adaptiveSerializedDispatchWidth" "${ini_file}")"
    emit_kv "adaptiveHighMLPFetchWidth" "$(ini_get_or_note "system.cpu" "adaptiveHighMLPFetchWidth" "${ini_file}")"
    emit_kv "adaptiveHighMLPInflightCap" "$(ini_get_or_note "system.cpu" "adaptiveHighMLPInflightCap" "${ini_file}")"
    emit_kv "adaptiveHighMLPRenameWidth" "$(ini_get_or_note "system.cpu" "adaptiveHighMLPRenameWidth" "${ini_file}")"
    emit_kv "adaptiveHighMLPDispatchWidth" "$(ini_get_or_note "system.cpu" "adaptiveHighMLPDispatchWidth" "${ini_file}")"
    emit_kv "adaptiveControlFetchWidth" "$(ini_get_or_note "system.cpu" "adaptiveControlFetchWidth" "${ini_file}")"
    emit_kv "adaptiveControlInflightCap" "$(ini_get_or_note "system.cpu" "adaptiveControlInflightCap" "${ini_file}")"
    emit_kv "adaptiveControlRenameWidth" "$(ini_get_or_note "system.cpu" "adaptiveControlRenameWidth" "${ini_file}")"
    emit_kv "adaptiveControlDispatchWidth" "$(ini_get_or_note "system.cpu" "adaptiveControlDispatchWidth" "${ini_file}")"
    emit_kv "adaptiveResourceFetchWidth" "$(ini_get_or_note "system.cpu" "adaptiveResourceFetchWidth" "${ini_file}")"
    emit_kv "adaptiveResourceInflightCap" "$(ini_get_or_note "system.cpu" "adaptiveResourceInflightCap" "${ini_file}")"
    emit_kv "adaptiveResourceRenameWidth" "$(ini_get_or_note "system.cpu" "adaptiveResourceRenameWidth" "${ini_file}")"
    emit_kv "adaptiveResourceDispatchWidth" "$(ini_get_or_note "system.cpu" "adaptiveResourceDispatchWidth" "${ini_file}")"
    emit_kv "adaptiveMemBlockRatioThres" "$(ini_get_or_note "system.cpu" "adaptiveMemBlockRatioThres" "${ini_file}")"
    emit_kv "adaptiveOutstandingMissThres" "$(ini_get_or_note "system.cpu" "adaptiveOutstandingMissThres" "${ini_file}")"
    emit_kv "adaptiveBranchRecoveryRatioThres" "$(ini_get_or_note "system.cpu" "adaptiveBranchRecoveryRatioThres" "${ini_file}")"
    emit_kv "adaptiveSquashRatioThres" "$(ini_get_or_note "system.cpu" "adaptiveSquashRatioThres" "${ini_file}")"
    emit_kv "adaptiveIQSaturationRatioThres" "$(ini_get_or_note "system.cpu" "adaptiveIQSaturationRatioThres" "${ini_file}")"
    emit_kv "adaptiveCommitActivityRatioThres" "$(ini_get_or_note "system.cpu" "adaptiveCommitActivityRatioThres" "${ini_file}")"
    echo
    echo "## Window-Level Output"
    if [[ -f "${OUTDIR}/adaptive_window_log.csv" ]]; then
      emit_kv "window log" "${OUTDIR}/adaptive_window_log.csv"
    else
      emit_kv "window log" "not found (run may have exited before first window write)"
    fi
  } > "${summary_file}"
}

"${GEM5_CMD[@]}" \
  2>&1 | tee "${OUTDIR}/run.log"

if [[ -f "${OUTDIR}/config.ini" ]]; then
  generate_summary "${OUTDIR}/config.ini" "${SUMMARY_FILE}"
fi

{
  echo "timestamp=${RUN_TIMESTAMP}"
  echo "outdir=${OUTDIR}"
  echo "maxinsts=${MAXINSTS}"
  echo "window_cycles=${WINDOW_CYCLES}"
  echo "conservative_fetch_width=${CONSERVATIVE_FETCH_WIDTH}"
  echo "conservative_inflight_cap=${CONSERVATIVE_INFLIGHT_CAP}"
  echo "conservative_iq_cap=${CONSERVATIVE_IQ_CAP}"
  echo "conservative_lsq_cap=${CONSERVATIVE_LSQ_CAP}"
  echo "conservative_rename_width=${CONSERVATIVE_RENAME_WIDTH}"
  echo "conservative_dispatch_width=${CONSERVATIVE_DISPATCH_WIDTH}"
  echo "workload_path=${WORKLOAD_PATH}"
  echo "workload_args=${WORKLOAD_ARGS}"
  echo "run_tag=${RUN_TAG:-custom_outdir}"
  if [[ ${#ADAPTIVE_EXTRA_PARAMS[@]} -gt 0 ]]; then
    echo "extra_params=${ADAPTIVE_EXTRA_PARAMS[*]}"
  fi
  echo "summary_file=${SUMMARY_FILE}"
  printf 'cmd='
  printf '%q ' "${GEM5_CMD[@]}"
  echo
} > "${OUTDIR}/run_meta.txt"

echo
echo "Adaptive run completed."
echo "Output dir: ${OUTDIR}"
echo "Summary file: ${SUMMARY_FILE}"
if [[ -f "${OUTDIR}/adaptive_window_log.csv" ]]; then
  echo "Window log: ${OUTDIR}/adaptive_window_log.csv"
fi
echo "Key stats:"
grep -E "simInsts|simTicks|simSeconds|hostSeconds|system.cpu.ipc" "${OUTDIR}/stats.txt" || true
