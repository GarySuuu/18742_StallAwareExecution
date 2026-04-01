# Adaptive Mechanism v1 Run Summary

## Run Information
- timestamp: 2026-03-31T11:43:11-04:00
- full command line: /home/rock/project/gem5/build/ARM/gem5.opt --outdir=/home/rock/project/gem5/runs/adaptive/v1/branch_entropy_10m_serial_bias/latest /home/rock/project/gem5/configs/deprecated/example/se.py -n 1 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB --maxinsts=10000000 --param system.cpu\[0\].enableStallAdaptive=True --param system.cpu\[0\].adaptiveWindowCycles=5000 --param system.cpu\[0\].adaptiveSwitchHysteresis=2 --param system.cpu\[0\].adaptiveMinModeWindows=2 --param system.cpu\[0\].adaptiveConservativeFetchWidth=2 --param system.cpu\[0\].adaptiveConservativeInflightCap=96 --param system.cpu\[0\].adaptiveConservativeIQCap=0 --param system.cpu\[0\].adaptiveConservativeLSQCap=0 --param system.cpu\[0\].adaptiveConservativeRenameWidth=0 --param system.cpu\[0\].adaptiveConservativeDispatchWidth=0 -c workloads/branch_entropy/bin/arm/linux/branch_entropy --options=32768\ 1024\ 1 --param system.cpu\[0\].adaptiveSwitchHysteresis=1 --param system.cpu\[0\].adaptiveMinModeWindows=1 --param system.cpu\[0\].adaptiveMemBlockRatioThres=0.12 --param system.cpu\[0\].adaptiveOutstandingMissThres=12
- output directory: /home/rock/project/gem5/runs/adaptive/v1/branch_entropy_10m_serial_bias/latest
- workload path: workloads/branch_entropy/bin/arm/linux/branch_entropy
- workload options: 32768 1024 1
- run tag: branch_entropy_10m_serial_bias
- ISA: ARM
- CPU model: DerivO3CPU
- mode: SE
- caches/l2cache: enabled/enabled
- mem-size: 2GB
- maxinsts: 10000000
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
- window log: /home/rock/project/gem5/runs/adaptive/v1/branch_entropy_10m_serial_bias/latest/adaptive_window_log.csv
