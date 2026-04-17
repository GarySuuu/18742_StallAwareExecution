#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/c/Users/garsy/Documents/18742project/gem5"
MCPAT_SCRIPT="${ROOT}/scripts/gem5_to_mcpat.py"
MCPAT_TEMPLATE="${ROOT}/ext/mcpat/regression/test-0/power_region0.xml"
MCPAT_BIN="${ROOT}/build/mcpat/mcpat"
VENV="${ROOT}/../.venv-gem5"

source "${VENV}/bin/activate"

# GAPBS benchmarks and their binaries
declare -A GAPBS_BINS
GAPBS_BINS[gapbs_bfs]="${ROOT}/workloads/external/gapbs/bfs"
GAPBS_BINS[gapbs_bc]="${ROOT}/workloads/external/gapbs/bc"
GAPBS_BINS[gapbs_pr]="${ROOT}/workloads/external/gapbs/pr"
GAPBS_BINS[gapbs_cc]="${ROOT}/workloads/external/gapbs/cc"
GAPBS_BINS[gapbs_sssp]="${ROOT}/workloads/external/gapbs/sssp"
GAPBS_BINS[gapbs_tc]="${ROOT}/workloads/external/gapbs/tc"

# Candidate 1: fw=3, cap=96, iq=0, lsq=0 (best on tc)
# Candidate 2: fw=4, cap=128, iq=0, lsq=0 (close to V2-tuned)
CANDIDATES=(
  "v3t4_cand1 3 96 0 0"
  "v3t4_cand2 4 128 0 0"
)

for cand in "${CANDIDATES[@]}"; do
  read -r cand_tag fw cap iq lsq <<< "$cand"

  for bench in gapbs_bfs gapbs_bc gapbs_pr gapbs_cc gapbs_sssp gapbs_tc; do
    outdir="${ROOT}/runs/v3_multilevel/${cand_tag}/${bench}/latest"

    if [[ -f "${outdir}/mcpat.out" ]]; then
      echo "SKIP: ${cand_tag}/${bench} (already completed)"
      continue
    fi

    echo "========================================"
    echo "Running: ${cand_tag}/${bench} (fw=${fw}, cap=${cap}, iq=${iq}, lsq=${lsq})"
    echo "========================================"

    bash "${ROOT}/scripts/run_adaptive.sh" \
      "${outdir}" 50000000 2500 \
      --workload "${GAPBS_BINS[${bench}]}" \
      --workload-args "-g 20 -n 1" \
      --param "system.cpu[0].adaptiveLightConsFetchWidth=${fw}" \
      --param "system.cpu[0].adaptiveLightConsInflightCap=${cap}" \
      --param "system.cpu[0].adaptiveLightConsIQCap=${iq}" \
      --param "system.cpu[0].adaptiveLightConsLSQCap=${lsq}" \
      --param "system.cpu[0].adaptiveConservativeFetchWidth=${fw}" \
      --param "system.cpu[0].adaptiveConservativeInflightCap=${cap}" \
      --param "system.cpu[0].adaptiveConservativeIQCap=${iq}" \
      --param "system.cpu[0].adaptiveConservativeLSQCap=${lsq}"

    echo "Running McPAT for ${cand_tag}/${bench}..."
    python3 "${MCPAT_SCRIPT}" \
      --config "${outdir}/config.json" \
      --stats "${outdir}/stats.txt" \
      --output "${outdir}/mcpat.xml" \
      --template "${MCPAT_TEMPLATE}" \
      --run-mcpat \
      --mcpat-binary "${MCPAT_BIN}" \
      --mcpat-output "${outdir}/mcpat.out"

    echo "Completed: ${cand_tag}/${bench}"
    grep -E "simInsts|system.cpu.ipc" "${outdir}/stats.txt" || true
    echo ""
  done
done

echo "All Phase B runs complete!"
