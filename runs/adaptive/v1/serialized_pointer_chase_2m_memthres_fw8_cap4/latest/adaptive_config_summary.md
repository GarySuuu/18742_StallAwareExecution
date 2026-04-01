# Adaptive Mechanism v1 Run Summary

## Run Information
- timestamp: 2026-03-26T12:35:17-04:00
- full command line: /home/rock/project/gem5/build/ARM/gem5.opt --outdir=/home/rock/project/gem5/runs/adaptive/v1/serialized_pointer_chase_2m_memthres_fw8_cap4/latest /home/rock/project/gem5/configs/deprecated/example/se.py -n 1 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB --maxinsts=2000000 --param system.cpu\[0\].enableStallAdaptive=True --param system.cpu\[0\].adaptiveWindowCycles=5000 --param system.cpu\[0\].adaptiveSwitchHysteresis=2 --param system.cpu\[0\].adaptiveMinModeWindows=2 --param system.cpu\[0\].adaptiveConservativeFetchWidth=8 --param system.cpu\[0\].adaptiveConservativeInflightCap=4 -c workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase --options=1048576\ 12\ 1 --param system.cpu\[0\].adaptiveMemBlockRatioThres=0.03 --param system.cpu\[0\].adaptiveOutstandingMissThres=40 --param system.cpu\[0\].adaptiveSwitchHysteresis=1 --param system.cpu\[0\].adaptiveMinModeWindows=1
- output directory: /home/rock/project/gem5/runs/adaptive/v1/serialized_pointer_chase_2m_memthres_fw8_cap4/latest
- workload path: workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase
- workload options: 1048576 12 1
- run tag: serialized_pointer_chase_2m_memthres_fw8_cap4
- ISA: ARM
- CPU model: DerivO3CPU
- mode: SE
- caches/l2cache: enabled/enabled
- mem-size: 2GB
- maxinsts: 2000000
- requested conservative fetch width override: 8
- requested conservative inflight cap override: 4
- extra adaptive params: system.cpu[0].adaptiveMemBlockRatioThres=0.03 system.cpu[0].adaptiveOutstandingMissThres=40 system.cpu[0].adaptiveSwitchHysteresis=1 system.cpu[0].adaptiveMinModeWindows=1

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
- adaptiveConservativeFetchWidth: 8
- adaptiveConservativeInflightCap: 4
- adaptiveMemBlockRatioThres: 0.03
- adaptiveOutstandingMissThres: 40.0
- adaptiveBranchRecoveryRatioThres: 0.1
- adaptiveSquashRatioThres: 0.2
- adaptiveIQSaturationRatioThres: 0.1
- adaptiveCommitActivityRatioThres: 0.2

## Window-Level Output
- window log: /home/rock/project/gem5/runs/adaptive/v1/serialized_pointer_chase_2m_memthres_fw8_cap4/latest/adaptive_window_log.csv
