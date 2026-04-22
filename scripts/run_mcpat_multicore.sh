#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/../.venv-gem5/bin/activate"

for cfg in branch_entropy_baseline branch_entropy_v4 phase_scan_mix_baseline phase_scan_mix_v4; do
    d="${ROOT_DIR}/runs/v4_multicore/${cfg}/latest"
    echo "=== ${cfg} ==="
    if [[ ! -f "${d}/config.json" ]]; then
        echo "  SKIP (no config.json)"
        continue
    fi
    python3 "${ROOT_DIR}/scripts/gem5_to_mcpat.py" \
        --config "${d}/config.json" \
        --stats "${d}/stats.txt" \
        --output "${d}/mcpat.xml" \
        --template "${ROOT_DIR}/ext/mcpat/regression/test-0/power_region0.xml" \
        --num-cores 4 \
        --run-mcpat \
        --mcpat-binary "${ROOT_DIR}/build/mcpat/mcpat" \
        --mcpat-output "${d}/mcpat.out" && echo "  OK" || echo "  FAILED"
done
