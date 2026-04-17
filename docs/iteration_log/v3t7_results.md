# v3t7 Results

## Config: fw=5, cap=128, iq=0, lsq=0, mem_block=0.12, window=2500

Both LightConservative and Conservative modes use identical parameters:
- FetchWidth = 5
- InflightCap = 128
- IQCap = 0 (unlimited)
- LSQCap = 0 (unlimited)

## 1. Full Results Table

| Bench | BL IPC | v3t7 IPC | dIPC% | dPower% | dEnergy% | WPE% |
|-------|--------|----------|-------|---------|----------|------|
| bfs | 1.409910 | 1.360963 | -3.47% | -17.71% | -14.00% | +0.19% |
| bc | 1.396511 | 1.344862 | -3.70% | -16.98% | -13.07% | -0.21% |
| pr | 1.406315 | 1.367210 | -2.78% | -11.98% | -8.96% | -0.38% |
| cc | 1.410674 | 1.372390 | -2.71% | -6.91% | -4.01% | -1.37% |
| sssp | 1.391411 | 1.369287 | -1.59% | -10.61% | -8.70% | +0.54% |
| tc | 1.345860 | 1.371393 | +1.90% | -11.09% | -12.39% | +4.24% |
| **AVG** | | | **-2.06%** | **-12.55%** | **-10.19%** | **+0.50%** |

## 2. Comparison: V2 vs v3t4 vs v3t7

| Bench | V2 dIPC% | V2 WPE% | v3t4 dIPC% | v3t4 WPE% | v3t7 dIPC% | v3t7 WPE% | Best WPE |
|-------|----------|---------|------------|-----------|------------|-----------|----------|
| bfs | -2.76% | +0.11% | -4.23% | +0.26% | -3.47% | +0.19% | v3t4 |
| bc | -2.79% | -0.22% | -4.07% | -0.26% | -3.70% | -0.21% | v3t7 |
| pr | -2.50% | -0.10% | -5.00% | +0.04% | -2.78% | -0.38% | v3t4 |
| cc | -2.40% | -0.57% | -4.90% | -1.08% | -2.71% | -1.37% | V2 |
| sssp | -2.03% | +0.14% | -3.12% | +0.23% | -1.59% | +0.54% | v3t7 |
| tc | +3.34% | +7.38% | +4.11% | +9.39% | +1.90% | +4.24% | v3t4 |
| **AVG** | | **+1.12%** | | **+1.43%** | | **+0.50%** | **v3t4** |

## 3. IPC Loss Check (target: dIPC > -3%)

| Bench | dIPC% | Within -3%? |
|-------|-------|-------------|
| bfs | -3.47% | NO |
| bc | -3.70% | NO |
| pr | -2.78% | YES |
| cc | -2.71% | YES |
| sssp | -1.59% | YES |
| tc | +1.90% | YES |

**4 of 6 benchmarks** have dIPC > -3%. bfs and bc still exceed the -3% threshold.

## 4. GAPBS Average WPE

- v3t7 GAPBS avg WPE: **+0.50%**
- v3t4 GAPBS avg WPE: +1.43%
- V2 GAPBS avg WPE: +1.12%

## 5. Overall Average WPE (v3t7 GAPBS + v3t3 Micro)

- GAPBS avg WPE (v3t7): +0.50%
- Micro avg WPE (v3t3): +2.39%
- **Overall avg WPE (12 benchmarks): +1.45%**

For reference:
- v3t4 GAPBS + v3t3 Micro overall: +1.91%
- V2 GAPBS + v3t3 Micro overall: +1.76%

## 6. Key Observations

- v3t7 (fw=5, cap=128) improves IPC loss vs v3t4 (fw=4, cap=128): avg dIPC went from -2.87% to -2.06%
- pr, cc, sssp, tc all moved within the -3% IPC loss target; bfs and bc still slightly exceed it
- However, the reduced throttling also reduces energy savings, hurting WPE
- tc lost the most WPE: from +9.39% (v3t4) to +4.24% (v3t7), because the wider fetch width reduces the power savings on the benchmark that benefited most from throttling
- Overall WPE dropped from +1.91% (v3t4) to +1.45% (v3t7)
