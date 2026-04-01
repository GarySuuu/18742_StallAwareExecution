# Adaptive Mechanism v1 Run Summary

## Run Information
- timestamp: 2026-03-11T22:32:43-04:00
- full command line: /home/rock/project/gem5/build/ARM/gem5.opt --outdir=/home/rock/project/gem5/runs/adaptive/v1/hash_probe_chain/latest /home/rock/project/gem5/configs/deprecated/example/se.py -n 1 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB --maxinsts=50000000 --param system.cpu\[0\].enableStallAdaptive=True --param system.cpu\[0\].adaptiveWindowCycles=5000 --param system.cpu\[0\].adaptiveSwitchHysteresis=2 --param system.cpu\[0\].adaptiveMinModeWindows=2 --param system.cpu\[0\].adaptiveConservativeFetchWidth=2 --param system.cpu\[0\].adaptiveConservativeInflightCap=96 -c workloads/hash_probe_chain/bin/arm/linux/hash_probe_chain --options=131072\ 64\ 1
- output directory: /home/rock/project/gem5/runs/adaptive/v1/hash_probe_chain/latest
- workload path: workloads/hash_probe_chain/bin/arm/linux/hash_probe_chain
- workload options: 131072 64 1
- run tag: hash_probe_chain
- ISA: ARM
- CPU model: DerivO3CPU
- mode: SE
- caches/l2cache: enabled/enabled
- mem-size: 2GB
- maxinsts: 50000000

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
- adaptiveConservativeFetchWidth: 2
- adaptiveConservativeInflightCap: 96
- adaptiveMemBlockRatioThres: 0.15
- adaptiveOutstandingMissThres: 8.0
- adaptiveBranchRecoveryRatioThres: 0.1
- adaptiveSquashRatioThres: 0.2
- adaptiveIQSaturationRatioThres: 0.1
- adaptiveCommitActivityRatioThres: 0.2

## Window-Level Output
- window log: /home/rock/project/gem5/runs/adaptive/v1/hash_probe_chain/latest/adaptive_window_log.csv
