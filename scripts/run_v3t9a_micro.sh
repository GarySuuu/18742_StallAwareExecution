#!/bin/bash
set -euo pipefail

GEM5_DIR="/mnt/c/Users/garsy/Documents/18742project/gem5"
cd "$GEM5_DIR"
source /mnt/c/Users/garsy/Documents/18742project/.venv-gem5/bin/activate

MAXINSTS=50000000
WINDOW=5000
CONFIG="v3t9a"

MICROS="balanced_pipeline_stress branch_entropy compute_queue_pressure phase_scan_mix serialized_pointer_chase stream_cluster_reduce"

for wl in $MICROS; do
    OUTDIR="$GEM5_DIR/runs/v3_multilevel/${CONFIG}/${wl}/latest"
    mkdir -p "$OUTDIR"

    WL="$GEM5_DIR/workloads/${wl}/bin/arm/linux/${wl}"

    echo "=== Running ${CONFIG} / ${wl} ==="
    bash scripts/run_adaptive.sh "$OUTDIR" $MAXINSTS $WINDOW \
        --workload "$WL" \
        --param "system.cpu[0].adaptiveLightConsFetchWidth=6" \
        --param "system.cpu[0].adaptiveLightConsInflightCap=56" \
        --param "system.cpu[0].adaptiveLightConsIQCap=26" \
        --param "system.cpu[0].adaptiveLightConsLSQCap=28" \
        --param "system.cpu[0].adaptiveConservativeFetchWidth=6" \
        --param "system.cpu[0].adaptiveConservativeInflightCap=56" \
        --param "system.cpu[0].adaptiveConservativeIQCap=26" \
        --param "system.cpu[0].adaptiveConservativeLSQCap=28" \
        --param "system.cpu[0].adaptiveSerializedTightFetchWidth=4" \
        --param "system.cpu[0].adaptiveSerializedTightInflightCap=128" \
        --param "system.cpu[0].adaptiveSerializedTightSquashThres=0.30" \
        --param "system.cpu[0].adaptiveMemBlockRatioThres=0.12"

    echo "=== McPAT ${CONFIG} / ${wl} ==="
    python3 scripts/gem5_to_mcpat.py \
        --config "$OUTDIR/config.json" \
        --stats "$OUTDIR/stats.txt" \
        --output "$OUTDIR/mcpat.xml" \
        --template ext/mcpat/regression/test-0/power_region0.xml \
        --run-mcpat \
        --mcpat-binary build/mcpat/mcpat \
        --mcpat-output "$OUTDIR/mcpat.out"

    echo "=== Done ${CONFIG} / ${wl} ==="
done

echo "ALL MICRO DONE"
