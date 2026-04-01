# Baseline Configuration Summary

## Run Information
- timestamp: 2026-03-12T17:11:09-04:00
- full command line: /home/rock/project/gem5/build/ARM/gem5.opt --outdir=/home/rock/project/gem5/runs/baseline/gapbs_bfs_smoke/latest /home/rock/project/gem5/configs/deprecated/example/se.py -n 1 --cpu-type=DerivO3CPU --caches --l2cache --mem-size=2GB --maxinsts=1000000 -c workloads/external/gapbs/bfs --options=-g\ 8\ -n\ 1
- output directory: /home/rock/project/gem5/runs/baseline/gapbs_bfs_smoke/latest
- workload path: workloads/external/gapbs/bfs
- workload options: -g 8 -n 1
- run tag: gapbs_bfs_smoke
- ISA: ARM
- CPU model: DerivO3CPU
- number of cores: 1
- SE mode / FS mode: SE mode (root.full_system=false)
- caches enabled: true
- l2cache enabled: true
- mem-size: 2GB
- maxinsts: 1000000

## Core Pipeline Widths and Structures (from config.ini)
- fetch width: 8
- decode width: 8
- rename width: 8
- dispatch width: 8
- issue width: 8
- commit width: 8
- ROB size: 192
- IQ size: 64
- LSQ capacity representation: No single unified LSQ size field was directly found in config.ini
- LQ entries: 32
- SQ entries: 32
- number of physical registers: Int=256, Float=256, Vec=256, VecPred=32, CC=1280, Mat=2

## CPU Clock / Voltage Domain
- configured cpu clock override in run script: not explicitly overridden in this run script (uses config/default-derived value)
- config.ini cpu clock field: 500 ticks
- global tick frequency from run.log: 1000000000000 ticks/sec
- effective cpu frequency: 2.000000 GHz (derived from clock=500 ticks and global ticks/sec=1000000000000)
- cpu voltage domain link: system.cpu_voltage_domain
- cpu voltage: 1.0

## Memory System
- system mem_mode: timing
- system mem_ranges (raw): 0:2147483648
- system mem_range (human-readable): 2.00 GB
- dram type: DRAMInterface
- dram device size (raw): 536870912
- dram device size (human-readable): 512.00 MB
- dram tCK: 1250 (unit interpretation should be verified against gem5 field semantics)
- membus width (raw): 16
- membus width (human-readable): 16 bytes (128 bits)

## Cache Hierarchy
- L1I size: 32768
- L1I assoc: 2
- L1I latencies: tag=2, data=2, response=2
- L1D size: 65536
- L1D assoc: 2
- L1D latencies: tag=2, data=2, response=2
- L2 size: 2097152
- L2 assoc: 8
- L2 latencies: tag=20, data=20, response=20

## Pipeline Delay Related Params
- fetchToDecodeDelay: 1
- decodeToRenameDelay: 1
- renameToIEWDelay: 2
- iewToCommitDelay: 1
- commitToFetchDelay: 1
- commitToDecodeDelay: 1
- issueToExecuteDelay: 1
- renameToROBDelay: 1
- trapLatency: 13

### Branch Predictor (system.cpu.branchPred)
```ini
type=TournamentBP
children=indirectBranchPred
BTBEntries=4096
BTBTagSize=16
RASSize=16
choiceCtrBits=2
choicePredictorSize=8192
eventq_index=0
globalCtrBits=2
globalPredictorSize=8192
indirectBranchPred=system.cpu.branchPred.indirectBranchPred
instShiftAmt=2
localCtrBits=2
localHistoryTableSize=2048
localPredictorSize=2048
numThreads=1
```

### Indirect Branch Predictor (system.cpu.branchPred.indirectBranchPred)
```ini
type=SimpleIndirectPredictor
eventq_index=0
indirectGHRBits=13
indirectHashGHR=true
indirectHashTargets=true
indirectPathLength=3
indirectSets=256
indirectTagSize=16
indirectWays=2
instShiftAmt=2
numThreads=1
```
