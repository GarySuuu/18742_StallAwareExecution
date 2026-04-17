#!/bin/bash
set -euo pipefail

GEM5_DIR="/mnt/c/Users/garsy/Documents/18742project/gem5"
cd "$GEM5_DIR"
source /mnt/c/Users/garsy/Documents/18742project/.venv-gem5/bin/activate

BENCHMARKS="bfs bc pr cc sssp tc"
MAXINSTS=50000000
WINDOW=2500

run_config() {
    local CONFIG=$1
    local TIGHT_FW=$2
    local TIGHT_THRESH=$3

    for bench in $BENCHMARKS; do
        OUTDIR="$GEM5_DIR/runs/v3_multilevel/${CONFIG}/gapbs_${bench}/latest"
        mkdir -p "$OUTDIR"

        WL="$GEM5_DIR/workloads/external/gapbs/${bench}"

        echo "=== Running ${CONFIG} / gapbs_${bench} ==="
        bash scripts/run_adaptive.sh "$OUTDIR" $MAXINSTS $WINDOW \
            --workload "$WL" \
            --workload-args "-g 20 -n 1" \
            --param "system.cpu[0].adaptiveLightConsFetchWidth=6" \
            --param "system.cpu[0].adaptiveLightConsInflightCap=128" \
            --param "system.cpu[0].adaptiveLightConsIQCap=0" \
            --param "system.cpu[0].adaptiveLightConsLSQCap=0" \
            --param "system.cpu[0].adaptiveConservativeFetchWidth=6" \
            --param "system.cpu[0].adaptiveConservativeInflightCap=128" \
            --param "system.cpu[0].adaptiveConservativeIQCap=0" \
            --param "system.cpu[0].adaptiveConservativeLSQCap=0" \
            --param "system.cpu[0].adaptiveSerializedTightFetchWidth=${TIGHT_FW}" \
            --param "system.cpu[0].adaptiveSerializedTightInflightCap=128" \
            --param "system.cpu[0].adaptiveSerializedTightSquashThres=${TIGHT_THRESH}" \
            --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12"

        echo "=== McPAT ${CONFIG} / gapbs_${bench} ==="
        python3 scripts/gem5_to_mcpat.py \
            --config "$OUTDIR/config.json" \
            --stats "$OUTDIR/stats.txt" \
            --output "$OUTDIR/mcpat.xml" \
            --template ext/mcpat/regression/test-0/power_region0.xml \
            --run-mcpat \
            --mcpat-binary build/mcpat/mcpat \
            --mcpat-output "$OUTDIR/mcpat.out"

        echo "=== Done ${CONFIG} / gapbs_${bench} ==="
    done
}

echo "====== CONFIG v3t9a: normal fw=6, tight fw=4, threshold=0.30 ======"
run_config "v3t9a" 4 0.30

echo "====== CONFIG v3t9b: normal fw=6, tight fw=4, threshold=0.25 ======"
run_config "v3t9b" 4 0.25

echo "====== CONFIG v3t9c: normal fw=6, tight fw=3, threshold=0.35 ======"
run_config "v3t9c" 3 0.35

echo "ALL DONE"
