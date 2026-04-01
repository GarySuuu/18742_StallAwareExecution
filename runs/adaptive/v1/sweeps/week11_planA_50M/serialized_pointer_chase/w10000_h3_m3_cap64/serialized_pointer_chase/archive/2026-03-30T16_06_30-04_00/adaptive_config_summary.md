# Adaptive Mechanism v1 Run Summary (unique outdir)

## Run Information
- timestamp: 2026-03-30T16:06:30-04:00
- output directory: /home/rock/project/gem5/runs/adaptive/v1/sweeps/week11_planA_50M/serialized_pointer_chase/w10000_h3_m3_cap64/serialized_pointer_chase/archive/2026-03-30T16_06_30-04_00
- run tag: serialized_pointer_chase
- full command line: /home/rock/project/gem5/build/ARM/gem5.opt --outdir=/home/rock/project/gem5/runs/adaptive/v1/sweeps/week11_planA_50M/serialized_pointer_chase/w10000_h3_m3_cap64/serialized_pointer_chase/archive/2026-03-30T16_06_30-04_00 /home/rock/project/gem5/configs/deprecated/example/se.py -n 1 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB --maxinsts=50000000 --param system.cpu\[0\].enableStallAdaptive=True --param system.cpu\[0\].adaptiveWindowCycles=10000 --param system.cpu\[0\].adaptiveConservativeFetchWidth=2 --param system.cpu\[0\].adaptiveConservativeInflightCap=64 --param system.cpu\[0\].adaptiveConservativeIQCap=0 --param system.cpu\[0\].adaptiveConservativeLSQCap=0 --param system.cpu\[0\].adaptiveConservativeRenameWidth=0 --param system.cpu\[0\].adaptiveConservativeDispatchWidth=0 -c workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase --options=1048576\ 12\ 1 --param system.cpu\[0\].adaptiveSwitchHysteresis=3 --param system.cpu\[0\].adaptiveMinModeWindows=3
- workload path: workloads/serialized_pointer_chase/bin/arm/linux/serialized_pointer_chase
- workload options: 1048576 12 1
- ISA: ARM
- CPU model: DerivO3CPU
- mode: SE
- caches/l2cache: enabled/enabled
- mem-size: 2GB
- maxinsts: 50000000

## Adaptive Parameters (explicitly set by script)
- adaptiveWindowCycles: 10000
- adaptiveConservativeFetchWidth: 2
- adaptiveConservativeInflightCap: 64
- adaptiveConservativeIQCap: 0
- adaptiveConservativeLSQCap: 0
- adaptiveConservativeRenameWidth: 0
- adaptiveConservativeDispatchWidth: 0

## Extra --param overrides
- param: system.cpu[0].adaptiveSwitchHysteresis=3
- param: system.cpu[0].adaptiveMinModeWindows=3

## Window-Level Output
- window log: /home/rock/project/gem5/runs/adaptive/v1/sweeps/week11_planA_50M/serialized_pointer_chase/w10000_h3_m3_cap64/serialized_pointer_chase/archive/2026-03-30T16_06_30-04_00/adaptive_window_log.csv
