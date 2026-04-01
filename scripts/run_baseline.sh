#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/../.venv-gem5"
OUTDIR=""
MAXINSTS="50000000"
WORKLOAD_PATH="${ROOT_DIR}/tests/test-progs/hello/bin/arm/linux/hello"
WORKLOAD_ARGS=""
RUN_TAG=""
RUN_TIMESTAMP="$(date -Iseconds)"
SUMMARY_FILE=""
CUSTOM_OUTDIR="false"

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
    -h|--help)
      cat <<'EOF'
Usage:
  run_baseline.sh [MAXINSTS]
  run_baseline.sh [OUTDIR] [MAXINSTS]
  run_baseline.sh [MAXINSTS] --workload <path> [--workload-args "<args>"]
  run_baseline.sh [OUTDIR] [MAXINSTS] --workload <path> [--workload-args "<args>"]
  run_baseline.sh [MAXINSTS] --workload <path> --run-tag <name>
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
  else
    OUTDIR="${1}"
    CUSTOM_OUTDIR="true"
    if [[ $# -ge 2 ]]; then
      MAXINSTS="${2}"
    fi
  fi
fi

if [[ ! -f "${ROOT_DIR}/build/ARM/gem5.opt" ]]; then
  echo "ERROR: ${ROOT_DIR}/build/ARM/gem5.opt not found."
  echo "Build first: scons build/ARM/gem5.opt -j2"
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
  OUTDIR="${ROOT_DIR}/runs/baseline/${RUN_TAG}/latest"
fi

SUMMARY_FILE="${OUTDIR}/baseline_config_summary.md"

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
  --maxinsts="${MAXINSTS}"
  -c "${WORKLOAD_PATH}"
)
if [[ -n "${WORKLOAD_ARGS}" ]]; then
  GEM5_CMD+=(--options="${WORKLOAD_ARGS}")
fi
CPU_MODEL="DerivO3CPU"
ISA_NAME="ARM"
NUM_CORES="1"
MODE_NAME="SE"
CACHES_ENABLED="true"
L2CACHE_ENABLED="true"
MEM_SIZE="2GB"

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

to_human_bytes() {
  local bytes="${1:-}"
  if [[ ! "${bytes}" =~ ^[0-9]+$ ]]; then
    printf 'not directly found in config.ini'
    return
  fi
  awk -v b="${bytes}" '
    BEGIN {
      split("B KB MB GB TB", u, " ");
      i=1;
      while (b >= 1024 && i < 5) { b/=1024; i++; }
      if (i == 1) printf "%.0f %s", b, u[i];
      else printf "%.2f %s", b, u[i];
    }'
}

clock_to_freq_note() {
  local clock_ticks="${1:-}"
  local ticks_per_sec="${2:-}"
  if [[ ! "${clock_ticks}" =~ ^[0-9]+$ ]]; then
    printf 'not directly found in config.ini'
    return
  fi
  if [[ ! "${ticks_per_sec}" =~ ^[0-9]+$ ]]; then
    printf 'not yet confirmed (missing global ticks/sec in run.log)'
    return
  fi
  awk -v c="${clock_ticks}" -v tps="${ticks_per_sec}" '
    BEGIN {
      hz = tps / c;
      ghz = hz / 1e9;
      printf "%.6f GHz (derived from clock=%s ticks and global ticks/sec=%s)", ghz, c, tps;
    }'
}

emit_section_dump() {
  local title="$1"
  local section="$2"
  local ini_file="$3"
  local body
  body="$(awk -v section="[${section}]" '
    $0 == section { in_section=1; next }
    /^\[/ { if (in_section) exit; in_section=0 }
    in_section { print }
  ' "${ini_file}")"
  echo "### ${title}"
  if [[ -z "${body}" ]]; then
    echo "- not directly found in config.ini"
  else
    echo '```ini'
    echo "${body}"
    echo '```'
  fi
  echo
}

generate_summary() {
  local ini_file="$1"
  local summary_file="$2"
  local full_system
  local outdir_abs
  local cmdline
  local global_ticks_per_sec
  local cpu_clock_ticks
  local mem_range_raw
  local mem_range_end
  local dram_device_size_raw
  local membus_width_raw

  full_system="$(ini_get_or_note "root" "full_system" "${ini_file}")"
  outdir_abs="$(readlink -f "${OUTDIR}" 2>/dev/null || printf '%s' "${OUTDIR}")"
  cmdline="$(join_cmd)"
  global_ticks_per_sec="$(awk '/Global frequency set at/ {print $5; exit}' "${OUTDIR}/run.log" 2>/dev/null || true)"
  cpu_clock_ticks="$(ini_get_or_note "system.cpu_clk_domain" "clock" "${ini_file}")"
  mem_range_raw="$(ini_get_or_note "system" "mem_ranges" "${ini_file}")"
  mem_range_end="$(printf '%s' "${mem_range_raw}" | awk -F: 'NF==2 && $2 ~ /^[0-9]+$/ {print $2}')"
  dram_device_size_raw="$(ini_get_or_note "system.mem_ctrls.dram" "device_size" "${ini_file}")"
  membus_width_raw="$(ini_get_or_note "system.membus" "width" "${ini_file}")"

  {
    echo "# Baseline Configuration Summary"
    echo
    echo "## Run Information"
    emit_kv "timestamp" "${RUN_TIMESTAMP}"
    emit_kv "full command line" "${cmdline}"
    emit_kv "output directory" "${outdir_abs}"
    emit_kv "workload path" "${WORKLOAD_PATH}"
    emit_kv "workload options" "${WORKLOAD_ARGS:-none}"
    emit_kv "run tag" "${RUN_TAG:-custom_outdir}"
    emit_kv "ISA" "${ISA_NAME}"
    emit_kv "CPU model" "${CPU_MODEL}"
    emit_kv "number of cores" "${NUM_CORES}"
    emit_kv "SE mode / FS mode" "${MODE_NAME} mode (root.full_system=${full_system})"
    emit_kv "caches enabled" "${CACHES_ENABLED}"
    emit_kv "l2cache enabled" "${L2CACHE_ENABLED}"
    emit_kv "mem-size" "${MEM_SIZE}"
    emit_kv "maxinsts" "${MAXINSTS}"
    echo
    echo "## Core Pipeline Widths and Structures (from config.ini)"
    emit_kv "fetch width" "$(ini_get_or_note "system.cpu" "fetchWidth" "${ini_file}")"
    emit_kv "decode width" "$(ini_get_or_note "system.cpu" "decodeWidth" "${ini_file}")"
    emit_kv "rename width" "$(ini_get_or_note "system.cpu" "renameWidth" "${ini_file}")"
    emit_kv "dispatch width" "$(ini_get_or_note "system.cpu" "dispatchWidth" "${ini_file}")"
    emit_kv "issue width" "$(ini_get_or_note "system.cpu" "issueWidth" "${ini_file}")"
    emit_kv "commit width" "$(ini_get_or_note "system.cpu" "commitWidth" "${ini_file}")"
    emit_kv "ROB size" "$(ini_get_or_note "system.cpu" "numROBEntries" "${ini_file}")"
    emit_kv "IQ size" "$(ini_get_or_note "system.cpu" "numIQEntries" "${ini_file}")"
    emit_kv "LSQ capacity representation" "No single unified LSQ size field was directly found in config.ini"
    emit_kv "LQ entries" "$(ini_get_or_note "system.cpu" "LQEntries" "${ini_file}")"
    emit_kv "SQ entries" "$(ini_get_or_note "system.cpu" "SQEntries" "${ini_file}")"
    emit_kv "number of physical registers" "Int=$(ini_get_or_note "system.cpu" "numPhysIntRegs" "${ini_file}"), Float=$(ini_get_or_note "system.cpu" "numPhysFloatRegs" "${ini_file}"), Vec=$(ini_get_or_note "system.cpu" "numPhysVecRegs" "${ini_file}"), VecPred=$(ini_get_or_note "system.cpu" "numPhysVecPredRegs" "${ini_file}"), CC=$(ini_get_or_note "system.cpu" "numPhysCCRegs" "${ini_file}"), Mat=$(ini_get_or_note "system.cpu" "numPhysMatRegs" "${ini_file}")"
    echo
    echo "## CPU Clock / Voltage Domain"
    emit_kv "configured cpu clock override in run script" "not explicitly overridden in this run script (uses config/default-derived value)"
    emit_kv "config.ini cpu clock field" "${cpu_clock_ticks} ticks"
    emit_kv "global tick frequency from run.log" "${global_ticks_per_sec:-not directly found in run.log} ticks/sec"
    emit_kv "effective cpu frequency" "$(clock_to_freq_note "${cpu_clock_ticks}" "${global_ticks_per_sec}")"
    emit_kv "cpu voltage domain link" "$(ini_get_or_note "system.cpu_clk_domain" "voltage_domain" "${ini_file}")"
    emit_kv "cpu voltage" "$(ini_get_or_note "system.cpu_voltage_domain" "voltage" "${ini_file}")"
    echo
    echo "## Memory System"
    emit_kv "system mem_mode" "$(ini_get_or_note "system" "mem_mode" "${ini_file}")"
    emit_kv "system mem_ranges (raw)" "${mem_range_raw}"
    emit_kv "system mem_range (human-readable)" "$(to_human_bytes "${mem_range_end}")"
    emit_kv "dram type" "$(ini_get_or_note "system.mem_ctrls.dram" "type" "${ini_file}")"
    emit_kv "dram device size (raw)" "${dram_device_size_raw}"
    emit_kv "dram device size (human-readable)" "$(to_human_bytes "${dram_device_size_raw}")"
    emit_kv "dram tCK" "$(ini_get_or_note "system.mem_ctrls.dram" "tCK" "${ini_file}") (unit interpretation should be verified against gem5 field semantics)"
    emit_kv "membus width (raw)" "${membus_width_raw}"
    if [[ "${membus_width_raw}" =~ ^[0-9]+$ ]]; then
      emit_kv "membus width (human-readable)" "${membus_width_raw} bytes ($((${membus_width_raw} * 8)) bits)"
    else
      emit_kv "membus width (human-readable)" "not directly found in config.ini"
    fi
    echo
    echo "## Cache Hierarchy"
    emit_kv "L1I size" "$(ini_get_or_note "system.cpu.icache" "size" "${ini_file}")"
    emit_kv "L1I assoc" "$(ini_get_or_note "system.cpu.icache" "assoc" "${ini_file}")"
    emit_kv "L1I latencies" "tag=$(ini_get_or_note "system.cpu.icache" "tag_latency" "${ini_file}"), data=$(ini_get_or_note "system.cpu.icache" "data_latency" "${ini_file}"), response=$(ini_get_or_note "system.cpu.icache" "response_latency" "${ini_file}")"
    emit_kv "L1D size" "$(ini_get_or_note "system.cpu.dcache" "size" "${ini_file}")"
    emit_kv "L1D assoc" "$(ini_get_or_note "system.cpu.dcache" "assoc" "${ini_file}")"
    emit_kv "L1D latencies" "tag=$(ini_get_or_note "system.cpu.dcache" "tag_latency" "${ini_file}"), data=$(ini_get_or_note "system.cpu.dcache" "data_latency" "${ini_file}"), response=$(ini_get_or_note "system.cpu.dcache" "response_latency" "${ini_file}")"
    emit_kv "L2 size" "$(ini_get_or_note "system.l2" "size" "${ini_file}")"
    emit_kv "L2 assoc" "$(ini_get_or_note "system.l2" "assoc" "${ini_file}")"
    emit_kv "L2 latencies" "tag=$(ini_get_or_note "system.l2" "tag_latency" "${ini_file}"), data=$(ini_get_or_note "system.l2" "data_latency" "${ini_file}"), response=$(ini_get_or_note "system.l2" "response_latency" "${ini_file}")"
    echo
    echo "## Pipeline Delay Related Params"
    emit_kv "fetchToDecodeDelay" "$(ini_get_or_note "system.cpu" "fetchToDecodeDelay" "${ini_file}")"
    emit_kv "decodeToRenameDelay" "$(ini_get_or_note "system.cpu" "decodeToRenameDelay" "${ini_file}")"
    emit_kv "renameToIEWDelay" "$(ini_get_or_note "system.cpu" "renameToIEWDelay" "${ini_file}")"
    emit_kv "iewToCommitDelay" "$(ini_get_or_note "system.cpu" "iewToCommitDelay" "${ini_file}")"
    emit_kv "commitToFetchDelay" "$(ini_get_or_note "system.cpu" "commitToFetchDelay" "${ini_file}")"
    emit_kv "commitToDecodeDelay" "$(ini_get_or_note "system.cpu" "commitToDecodeDelay" "${ini_file}")"
    emit_kv "issueToExecuteDelay" "$(ini_get_or_note "system.cpu" "issueToExecuteDelay" "${ini_file}")"
    emit_kv "renameToROBDelay" "$(ini_get_or_note "system.cpu" "renameToROBDelay" "${ini_file}")"
    emit_kv "trapLatency" "$(ini_get_or_note "system.cpu" "trapLatency" "${ini_file}")"
    echo
    emit_section_dump "Branch Predictor (system.cpu.branchPred)" "system.cpu.branchPred" "${ini_file}"
    emit_section_dump "Indirect Branch Predictor (system.cpu.branchPred.indirectBranchPred)" "system.cpu.branchPred.indirectBranchPred" "${ini_file}"
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
  echo "workload_path=${WORKLOAD_PATH}"
  echo "workload_args=${WORKLOAD_ARGS}"
  echo "run_tag=${RUN_TAG:-custom_outdir}"
  echo "summary_file=${SUMMARY_FILE}"
  printf 'cmd='
  printf '%q ' "${GEM5_CMD[@]}"
  echo
} > "${OUTDIR}/run_meta.txt"

echo
echo "Baseline completed."
echo "Output dir: ${OUTDIR}"
echo "Summary file: ${SUMMARY_FILE}"
echo "Key stats:"
grep -E "simInsts|simTicks|simSeconds|hostSeconds|system.cpu.ipc" "${OUTDIR}/stats.txt" || true
