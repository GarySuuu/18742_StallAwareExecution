#!/usr/bin/env bash
set -euo pipefail

# Week 11: sweep + unique outputs + automatic CSV merge.
# - Never overwrites teammate outputs (timestamped archives per run).
# - Defaults to a smaller maxinsts for quick exploration.
# - Produces a merged results.csv you can plot immediately.
#
# Example:
#   cd /home/rock/project/gem5
#   ./scripts/week11_sweep_and_analyze.sh \
#     --workload workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase \
#     --workload-args "1048576 12 1" \
#     --run-tag serialized_pointer_chase
#
# GAPBS BFS:
#   ./scripts/week11_sweep_and_analyze.sh \
#     --workload workloads/external/gapbs/bfs \
#     --workload-args "-g 20 -n 1" \
#     --run-tag gapbs_bfs

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WORKLOAD_PATH=""
WORKLOAD_ARGS=""
RUN_TAG=""

SWEEP_NAME="${SWEEP_NAME:-week11}"
OUTDIR_BASE="${ROOT_DIR}/runs/adaptive/v1/sweeps/${SWEEP_NAME}"

# Default reduced instruction budget for Week 11 exploration.
MAXINSTS="${MAXINSTS:-5000000}"

# Parameter grids (override via env if you want).
WINDOWS_CYCLES=(${WINDOWS_CYCLES:-2500 5000 10000})
HYSTERESIS=(${HYSTERESIS:-1 2 3})
MIN_HOLD=(${MIN_HOLD:-1 2 3})
INFLIGHT_CAPS=(${INFLIGHT_CAPS:-64 96 128 160})

usage() {
  cat <<'EOF'
Usage:
  week11_sweep_and_analyze.sh --workload <path> [--workload-args "<args>"] [--run-tag <tag>] [options]

Options:
  --outdir-base <dir>     Base directory for sweep outputs
  --maxinsts <n>          Max instructions (default: 5,000,000 for quick sweep)
  --analyze-only          Skip running; only (re)generate merged CSV

Environment overrides (space-separated lists):
  WINDOWS_CYCLES="2500 5000 10000"
  HYSTERESIS="1 2 3"
  MIN_HOLD="1 2 3"
  INFLIGHT_CAPS="64 96 128 160"
  SWEEP_NAME="week11"
EOF
}

ANALYZE_ONLY="false"
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
    --maxinsts)
      MAXINSTS="$2"
      shift 2
      ;;
    --analyze-only)
      ANALYZE_ONLY="true"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ "${ANALYZE_ONLY}" != "true" && -z "${WORKLOAD_PATH}" ]]; then
  echo "ERROR: --workload is required"
  usage
  exit 2
fi

mkdir -p "${OUTDIR_BASE}"

SWEEP_ROOT="${OUTDIR_BASE}/${RUN_TAG:-auto}"
RESULTS_CSV="${SWEEP_ROOT}/results.csv"

echo "Sweep root: ${SWEEP_ROOT}"
echo "Results CSV: ${RESULTS_CSV}"
echo "Maxinsts: ${MAXINSTS}"
echo

run_one() {
  local win="$1"
  local hyst="$2"
  local hold="$3"
  local cap="$4"

  local label="w${win}_h${hyst}_m${hold}_cap${cap}"
  local base="${SWEEP_ROOT}/${label}"
  mkdir -p "${base}"

  echo "==> ${label}"

  local cmd=(
    "${ROOT_DIR}/scripts/run_adaptive_unique.sh"
    "${MAXINSTS}"
    "${win}"
    --outdir-base "${base}"
    --workload "${WORKLOAD_PATH}"
  )
  if [[ -n "${WORKLOAD_ARGS}" ]]; then
    cmd+=(--workload-args "${WORKLOAD_ARGS}")
  fi
  if [[ -n "${RUN_TAG}" ]]; then
    cmd+=(--run-tag "${RUN_TAG}")
  fi

  # Week 11 knobs:
  cmd+=(--conservative-inflight-cap "${cap}")
  cmd+=(--param "system.cpu[0].adaptiveSwitchHysteresis=${hyst}")
  cmd+=(--param "system.cpu[0].adaptiveMinModeWindows=${hold}")

  "${cmd[@]}"
  echo
}

if [[ "${ANALYZE_ONLY}" != "true" ]]; then
  for win in "${WINDOWS_CYCLES[@]}"; do
    for hyst in "${HYSTERESIS[@]}"; do
      for hold in "${MIN_HOLD[@]}"; do
        for cap in "${INFLIGHT_CAPS[@]}"; do
          run_one "${win}" "${hyst}" "${hold}" "${cap}"
        done
      done
    done
  done
fi

echo "Merging results into CSV..."
python3 "${ROOT_DIR}/scripts/analyze_week11.py" --sweep-base "${SWEEP_ROOT}" --out-csv "${RESULTS_CSV}"
echo
echo "Done."
echo "Sweep folder:"
echo "  ${SWEEP_ROOT}"
echo "Merged CSV:"
echo "  ${RESULTS_CSV}"
