# Adaptive Mechanism v1 Run Summary

## Run Information
- timestamp: 2026-03-31T11:04:33-04:00
- full command line: /home/rock/project/gem5/build/ARM/gem5.opt --outdir=/home/rock/project/gem5/runs/adaptive/v1/phase_scan_mix_serial_bias_50m/latest /home/rock/project/gem5/configs/deprecated/example/se.py -n 1 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB --maxinsts=50000000 --param system.cpu\[0\].enableStallAdaptive=True --param system.cpu\[0\].adaptiveWindowCycles=5000 --param system.cpu\[0\].adaptiveSwitchHysteresis=2 --param system.cpu\[0\].adaptiveMinModeWindows=2 --param system.cpu\[0\].adaptiveConservativeFetchWidth=2 --param system.cpu\[0\].adaptiveConservativeInflightCap=96 --param system.cpu\[0\].adaptiveConservativeIQCap=0 --param system.cpu\[0\].adaptiveConservativeLSQCap=0 --param system.cpu\[0\].adaptiveConservativeRenameWidth=0 --param system.cpu\[0\].adaptiveConservativeDispatchWidth=0 -c workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix --options=524288\ 24\ 1 --param system.cpu\[0\].adaptiveSwitchHysteresis=1 --param system.cpu\[0\].adaptiveMinModeWindows=1 --param system.cpu\[0\].adaptiveMemBlockRatioThres=0.12 --param system.cpu\[0\].adaptiveOutstandingMissThres=12
- output directory: /home/rock/project/gem5/runs/adaptive/v1/phase_scan_mix_serial_bias_50m/latest
- workload path: workloads/phase_scan_mix/bin/arm/linux/phase_scan_mix
- workload options: 524288 24 1
- run tag: phase_scan_mix_serial_bias_50m
- ISA: ARM
- CPU model: DerivO3CPU
- mode: SE
- caches/l2cache: enabled/enabled
- mem-size: 2GB
- maxinsts: 50000000
- requested conservative fetch width override: 2
- requested conservative inflight cap override: 96
- requested conservative IQ cap override: 0
- requested conservative LSQ cap override: 0
- requested conservative rename width override: 0
- requested conservative dispatch width override: 0
- extra adaptive params: system.cpu[0].adaptiveSwitchHysteresis=1 system.cpu[0].adaptiveMinModeWindows=1 system.cpu[0].adaptiveMemBlockRatioThres=0.12 system.cpu[0].adaptiveOutstandingMissThres=12

## Classification to Mode Mapping (v1)
- Serialized-memory dominated: conservative
- High-MLP memory dominated: aggressive
- Control dominated: conservative
- Resource-contention / compute dominated: aggressive

## Adaptive Parameters (from config.ini)
- enableStallAdaptive: true
- adaptiveWindowCycles: 5000
- adaptiveSwitchHysteresis: 1
- adaptiveMinModeWindows: 1
- adaptiveConservativeFetchWidth: 2
- adaptiveConservativeInflightCap: 96
- adaptiveConservativeIQCap: 0
- adaptiveConservativeLSQCap: 0
- adaptiveConservativeRenameWidth: 0
- adaptiveConservativeDispatchWidth: 0
- adaptiveMemBlockRatioThres: 0.12
- adaptiveOutstandingMissThres: 12.0
- adaptiveBranchRecoveryRatioThres: 0.1
- adaptiveSquashRatioThres: 0.2
- adaptiveIQSaturationRatioThres: 0.1
- adaptiveCommitActivityRatioThres: 0.2

## Window-Level Output
- window log: /home/rock/project/gem5/runs/adaptive/v1/phase_scan_mix_serial_bias_50m/latest/adaptive_window_log.csv
