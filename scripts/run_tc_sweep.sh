#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/c/Users/garsy/Documents/18742project/gem5"
SWEEP_DIR="${ROOT}/runs/v3_multilevel/gapbs_tc_sweep"
TC_BIN="${ROOT}/workloads/external/gapbs/tc"
MCPAT_SCRIPT="${ROOT}/scripts/gem5_to_mcpat.py"
MCPAT_TEMPLATE="${ROOT}/ext/mcpat/regression/test-0/power_region0.xml"
MCPAT_BIN="${ROOT}/build/mcpat/mcpat"
VENV="${ROOT}/../.venv-gem5"

source "${VENV}/bin/activate"

# tc is classified as Serialized -> LightConservative mode
# We need to override adaptiveLightCons* params, NOT adaptiveConservative* params
# Also force all windows to LightConservative by setting mem_block=0.0 + outstanding_miss=9999

# Define sweep configs: tag fw cap iq lsq
CONFIGS=(
  "fw3_cap64_iq0_lsq0 3 64 0 0"
  "fw4_cap64_iq0_lsq0 4 64 0 0"
  "fw4_cap96_iq0_lsq0 4 96 0 0"
  "fw4_cap128_iq0_lsq0 4 128 0 0"
  "fw5_cap64_iq0_lsq0 5 64 0 0"
  "fw5_cap96_iq0_lsq0 5 96 0 0"
  "fw5_cap96_iq26_lsq28 5 96 26 28"
  "fw4_cap64_iq20_lsq24 4 64 20 24"
  "fw4_cap96_iq26_lsq28 4 96 26 28"
  "fw5_cap64_iq26_lsq28 5 64 26 28"
  "fw6_cap56_iq26_lsq28 6 56 26 28"
  "fw3_cap96_iq0_lsq0 3 96 0 0"
)

for config in "${CONFIGS[@]}"; do
  read -r tag fw cap iq lsq <<< "$config"
  outdir="${SWEEP_DIR}/${tag}/latest"

  if [[ -f "${outdir}/mcpat.out" ]]; then
    # Check if it has the RIGHT params (not the old broken ones)
    actual_fw=$(grep "adaptiveLightConsFetchWidth" "${outdir}/config.ini" 2>/dev/null | awk -F= '{print $2}')
    if [[ "${actual_fw}" == "${fw}" ]]; then
      echo "SKIP: ${tag} (already completed with correct params)"
      continue
    else
      echo "RE-RUN: ${tag} (old run had wrong LightCons params)"
    fi
  fi

  echo "========================================"
  echo "Running: ${tag} (fw=${fw}, cap=${cap}, iq=${iq}, lsq=${lsq})"
  echo "========================================"

  bash "${ROOT}/scripts/run_adaptive.sh" \
    "${outdir}" 50000000 2500 \
    --workload "${TC_BIN}" \
    --workload-args "-g 20 -n 1" \
    --param "system.cpu[0].adaptiveLightConsFetchWidth=${fw}" \
    --param "system.cpu[0].adaptiveLightConsInflightCap=${cap}" \
    --param "system.cpu[0].adaptiveLightConsIQCap=${iq}" \
    --param "system.cpu[0].adaptiveLightConsLSQCap=${lsq}" \
    --param "system.cpu[0].adaptiveMemBlockRatioThres=0.0" \
    --param "system.cpu[0].adaptiveOutstandingMissThres=9999"

  echo "Running McPAT for ${tag}..."
  python3 "${MCPAT_SCRIPT}" \
    --config "${outdir}/config.json" \
    --stats "${outdir}/stats.txt" \
    --output "${outdir}/mcpat.xml" \
    --template "${MCPAT_TEMPLATE}" \
    --run-mcpat \
    --mcpat-binary "${MCPAT_BIN}" \
    --mcpat-output "${outdir}/mcpat.out"

  echo "Completed: ${tag}"
  grep -E "simInsts|system.cpu.ipc" "${outdir}/stats.txt" || true
  echo ""
done

echo "All sweep runs complete!"
