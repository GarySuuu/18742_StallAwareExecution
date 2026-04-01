# Adaptive Mechanism v1 Run Summary

## Run Information
- timestamp: 2026-03-26T12:54:40-04:00
- full command line: /home/rock/project/gem5/build/ARM/gem5.opt --outdir=/home/rock/project/gem5/runs/adaptive/v1/phase_scan_mix_2m_fw8_cap64/latest /home/rock/project/gem5/configs/deprecated/example/se.py -n 1 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB --maxinsts=2000000 --param system.cpu\[0\].enableStallAdaptive=True --param system.cpu\[0\].adaptiveWindowCycles=5000 --param system.cpu\[0\].adaptiveSwitchHysteresis=2 --param system.cpu\[0\].adaptiveMinModeWindows=2 --param system.cpu\[0\].adaptiveConservativeFetchWidth=8 --param system.cpu\[0\].adaptiveConservativeInflightCap=64 -c workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix --options=524288\ 24\ 1
- output directory: /home/rock/project/gem5/runs/adaptive/v1/phase_scan_mix_2m_fw8_cap64/latest
- workload path: workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix
- workload options: 524288 24 1
- run tag: phase_scan_mix_2m_fw8_cap64
- ISA: ARM
- CPU model: DerivO3CPU
- mode: SE
- caches/l2cache: enabled/enabled
- mem-size: 2GB
- maxinsts: 2000000
- requested conservative fetch width override: 8
- requested conservative inflight cap override: 64
- extra adaptive params: none

## Classification to Mode Mapping (v1)
- Serialized-memory dominated: conservative
- High-MLP memory dominated: aggressive
- Control dominated: conservative
- Resource-contention / compute dominated: aggressive

## Adaptive Parameters (from config.ini)
- enableStallAdaptive: true
- adaptiveWindowCycles: 5000
- adaptiveSwitchHysteresis: 2
- adaptiveMinModeWindows: 2
- adaptiveConservativeFetchWidth: 8
- adaptiveConservativeInflightCap: 64
- adaptiveMemBlockRatioThres: 0.15
- adaptiveOutstandingMissThres: 8.0
- adaptiveBranchRecoveryRatioThres: 0.1
- adaptiveSquashRatioThres: 0.2
- adaptiveIQSaturationRatioThres: 0.1
- adaptiveCommitActivityRatioThres: 0.2

## Window-Level Output
- window log: /home/rock/project/gem5/runs/adaptive/v1/phase_scan_mix_2m_fw8_cap64/latest/adaptive_window_log.csv
