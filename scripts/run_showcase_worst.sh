#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/../.venv-gem5/bin/activate"
MCPAT="${ROOT_DIR}/scripts/gem5_to_mcpat.py"
MCPAT_BIN="${ROOT_DIR}/build/mcpat/mcpat"
TPL="${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml"
OUTBASE="${ROOT_DIR}/runs/v4_presentation/showcase"
wl="adaptive_showcase_worst"
path="${ROOT_DIR}/workloads/${wl}/bin/arm/linux/${wl}"

echo "=== ${wl} baseline ==="
d="${OUTBASE}/${wl}_baseline/latest"
bash "${ROOT_DIR}/scripts/run_baseline.sh" "${d}" 50000000 --workload "${path}" 2>&1 | tail -3
python3 "${MCPAT}" --config "${d}/config.json" --stats "${d}/stats.txt" \
    --output "${d}/mcpat.xml" --template "${TPL}" \
    --run-mcpat --mcpat-binary "${MCPAT_BIN}" --mcpat-output "${d}/mcpat.out" 2>/dev/null

echo "=== ${wl} v4 ==="
d="${OUTBASE}/${wl}_v4/latest"
bash "${ROOT_DIR}/scripts/run_adaptive.sh" "${d}" 50000000 2500 --workload "${path}" \
    --param "system.cpu[0].adaptiveWindowAutoSize=True" \
    --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12" \
    --param "system.cpu[0].adaptiveConservativeFetchWidth=5" \
    --param "system.cpu[0].adaptiveConservativeInflightCap=48" \
    --param "system.cpu[0].adaptiveConservativeIQCap=24" \
    --param "system.cpu[0].adaptiveConservativeLSQCap=24" \
    --param "system.cpu[0].adaptiveSerializedTightFetchWidth=3" \
    --param "system.cpu[0].adaptiveSerializedTightSquashThres=0.25" \
    2>&1 | tail -3
python3 "${MCPAT}" --config "${d}/config.json" --stats "${d}/stats.txt" \
    --output "${d}/mcpat.xml" --template "${TPL}" \
    --run-mcpat --mcpat-binary "${MCPAT_BIN}" --mcpat-output "${d}/mcpat.out" 2>/dev/null
echo "=== Done ==="
