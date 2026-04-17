#!/usr/bin/env bash
set -uo pipefail

BASE="/mnt/c/Users/garsy/Documents/18742project/gem5/runs/v3_multilevel"
V2_MICRO="/mnt/c/Users/garsy/Documents/18742project/gem5/runs/adaptive/v3_compiled"
V2_GAPBS="/mnt/c/Users/garsy/Documents/18742project/gem5/runs/adaptive/v3_compiled"
BL_MICRO="/mnt/c/Users/garsy/Documents/18742project/gem5/runs/baseline_v3"
BL_GAPBS="/mnt/c/Users/garsy/Documents/18742project/gem5/runs/baseline/formal_gapbs"

get_ipc() {
    local dir="$1"
    local val
    val=$(grep "system.cpu.ipc" "$dir/stats.txt" 2>/dev/null | head -1 | awk '{print $2}') || true
    echo "${val:-N/A}"
}

get_energy() {
    local dir="$1"
    if [[ ! -f "$dir/mcpat.out" ]]; then
        echo "N/A"
        return
    fi
    local val
    val=$(grep "Total Runtime Energy" "$dir/mcpat.out" 2>/dev/null | head -1 | sed 's/.*= //' | awk '{print $1}') || true
    echo "${val:-N/A}"
}

get_total_power() {
    local dir="$1"
    if [[ ! -f "$dir/mcpat.out" ]]; then
        echo "N/A"
        return
    fi
    local val
    val=$(grep "Runtime Dynamic Power" "$dir/mcpat.out" 2>/dev/null | head -1 | sed 's/.*= //' | awk '{print $1}') || true
    echo "${val:-N/A}"
}

MICRO_WL="balanced_pipeline_stress phase_scan_mix branch_entropy serialized_pointer_chase compute_queue_pressure stream_cluster_reduce"
GAPBS_WL="bfs bc pr cc sssp tc"

echo "========================================"
echo "  DATA COLLECTION"
echo "========================================"

echo ""
echo "=== V3ML BASELINE (from v3_multilevel/baseline) ==="
for wl in $MICRO_WL; do
    dir="$BASE/baseline/$wl/latest"
    ipc=$(get_ipc "$dir")
    energy=$(get_energy "$dir")
    power=$(get_total_power "$dir")
    echo "BL $wl: IPC=$ipc Energy=$energy Power=$power"
done
for bench in $GAPBS_WL; do
    dir="$BASE/baseline/gapbs_$bench/latest"
    ipc=$(get_ipc "$dir")
    energy=$(get_energy "$dir")
    power=$(get_total_power "$dir")
    echo "BL gapbs_$bench: IPC=$ipc Energy=$energy Power=$power"
done

echo ""
echo "=== V3ML_T2 ==="
for wl in $MICRO_WL; do
    dir="$BASE/v3ml_t2/$wl/latest"
    ipc=$(get_ipc "$dir")
    energy=$(get_energy "$dir")
    power=$(get_total_power "$dir")
    echo "T2 $wl: IPC=$ipc Energy=$energy Power=$power"
done
for bench in $GAPBS_WL; do
    dir="$BASE/v3ml_t2/gapbs_$bench/latest"
    ipc=$(get_ipc "$dir")
    energy=$(get_energy "$dir")
    power=$(get_total_power "$dir")
    echo "T2 gapbs_$bench: IPC=$ipc Energy=$energy Power=$power"
done

echo ""
echo "=== V2 REFERENCE (micro) ==="
for wl in $MICRO_WL; do
    v2dir="$V2_MICRO/${wl}_v2_ref/latest"
    if [[ -d "$v2dir" ]]; then
        ipc=$(get_ipc "$v2dir")
        energy=$(get_energy "$v2dir")
        power=$(get_total_power "$v2dir")
        echo "V2 $wl: IPC=$ipc Energy=$energy Power=$power"
    else
        echo "V2 $wl: NOT FOUND at $v2dir"
    fi
done

echo ""
echo "=== V2 REFERENCE (GAPBS) ==="
for bench in $GAPBS_WL; do
    v2dir="$V2_GAPBS/gapbs_${bench}_g20_v2_tuned/latest"
    if [[ -d "$v2dir" ]]; then
        ipc=$(get_ipc "$v2dir")
        energy=$(get_energy "$v2dir")
        power=$(get_total_power "$v2dir")
        echo "V2 gapbs_$bench: IPC=$ipc Energy=$energy Power=$power"
    else
        echo "V2 gapbs_$bench: NOT FOUND at $v2dir"
    fi
done

echo ""
echo "=== V2 BASELINE for micro (from baseline_v3) ==="
for wl in $MICRO_WL; do
    bldir="$BL_MICRO/$wl/latest"
    if [[ -d "$bldir" ]]; then
        ipc=$(get_ipc "$bldir")
        energy=$(get_energy "$bldir")
        echo "V2BL $wl: IPC=$ipc Energy=$energy"
    else
        echo "V2BL $wl: NOT FOUND"
    fi
done

echo ""
echo "=== V2 BASELINE for GAPBS ==="
for bench in $GAPBS_WL; do
    bldir="/mnt/c/Users/garsy/Documents/18742project/gem5/runs/baseline/formal_gapbs_${bench}_g20_baseline/latest"
    if [[ -d "$bldir" ]]; then
        ipc=$(get_ipc "$bldir")
        energy=$(get_energy "$bldir")
        echo "V2BL gapbs_$bench: IPC=$ipc Energy=$energy"
    else
        echo "V2BL gapbs_$bench: NOT FOUND at $bldir"
    fi
done

echo ""
echo "=== MODE DISTRIBUTIONS (v3ml_t2) ==="
for wl in $MICRO_WL; do
    logfile="$BASE/v3ml_t2/$wl/latest/adaptive_window_log.csv"
    if [[ -f "$logfile" ]]; then
        echo "MODE_DIST $wl:"
        tail -n +2 "$logfile" | awk -F',' '{print $4}' | sort | uniq -c | sort -rn
    fi
done
for bench in $GAPBS_WL; do
    logfile="$BASE/v3ml_t2/gapbs_$bench/latest/adaptive_window_log.csv"
    if [[ -f "$logfile" ]]; then
        echo "MODE_DIST gapbs_$bench:"
        tail -n +2 "$logfile" | awk -F',' '{print $4}' | sort | uniq -c | sort -rn
    fi
done

echo ""
echo "=== CLASSIFICATION DISTRIBUTIONS (v3ml_t2) ==="
for wl in $MICRO_WL; do
    logfile="$BASE/v3ml_t2/$wl/latest/adaptive_window_log.csv"
    if [[ -f "$logfile" ]]; then
        echo "CLASS_DIST $wl:"
        tail -n +2 "$logfile" | awk -F',' '{print $3}' | sort | uniq -c | sort -rn
    fi
done
for bench in $GAPBS_WL; do
    logfile="$BASE/v3ml_t2/gapbs_$bench/latest/adaptive_window_log.csv"
    if [[ -f "$logfile" ]]; then
        echo "CLASS_DIST gapbs_$bench:"
        tail -n +2 "$logfile" | awk -F',' '{print $3}' | sort | uniq -c | sort -rn
    fi
done
