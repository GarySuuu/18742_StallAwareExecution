# Classification Quality Report: branch_entropy

**Log**: `runs/adaptive/v2/branch_entropy/latest/adaptive_window_log.csv`

**Total windows**: 10965


## Switch Quality (3283 switches analyzed)

- Beneficial switches (IPC improved): 1674 (51.0%)
- Harmful switches (IPC degraded): 1609 (49.0%)
- Average IPC delta after switch: 0.000412

| Window | Old Mode | New Mode | Before IPC | After IPC | Delta | Beneficial? |
|--------|----------|----------|------------|-----------|-------|-------------|
| 60 | aggressive | conservative | 1.9584 | 1.0395 | -0.9189 | No |
| 62 | conservative | aggressive | 1.3746 | 1.0289 | -0.3457 | No |
| 90 | aggressive | conservative | 0.9897 | 1.0461 | +0.0564 | Yes |
| 92 | conservative | aggressive | 1.0026 | 1.0230 | +0.0204 | Yes |
| 97 | aggressive | conservative | 1.0221 | 1.0650 | +0.0429 | Yes |
| 99 | conservative | aggressive | 1.0363 | 1.0183 | -0.0179 | No |
| 102 | aggressive | conservative | 1.0377 | 1.0251 | -0.0126 | No |
| 104 | conservative | aggressive | 1.0029 | 1.0377 | +0.0347 | Yes |
| 109 | aggressive | conservative | 1.0469 | 1.0056 | -0.0413 | No |
| 111 | conservative | aggressive | 1.0524 | 1.0281 | -0.0243 | No |
| 118 | aggressive | conservative | 0.9931 | 0.9965 | +0.0033 | Yes |
| 120 | conservative | aggressive | 1.0054 | 1.0264 | +0.0210 | Yes |
| 136 | aggressive | conservative | 0.9971 | 1.0535 | +0.0565 | Yes |
| 138 | conservative | aggressive | 1.0156 | 1.0543 | +0.0387 | Yes |
| 140 | aggressive | conservative | 1.0535 | 1.0291 | -0.0244 | No |
| 142 | conservative | aggressive | 1.0543 | 0.9951 | -0.0591 | No |
| 149 | aggressive | conservative | 1.0059 | 0.9963 | -0.0096 | No |
| 151 | conservative | aggressive | 0.9930 | 1.0019 | +0.0089 | Yes |
| 165 | aggressive | conservative | 1.0008 | 1.0516 | +0.0508 | Yes |
| 167 | conservative | aggressive | 1.0376 | 1.0597 | +0.0221 | Yes |
| 170 | aggressive | conservative | 1.0451 | 1.0481 | +0.0030 | Yes |
| 172 | conservative | aggressive | 1.0522 | 1.0371 | -0.0151 | No |
| 181 | aggressive | conservative | 0.9825 | 0.9911 | +0.0086 | Yes |
| 183 | conservative | aggressive | 0.9875 | 1.0275 | +0.0399 | Yes |
| 188 | aggressive | conservative | 1.0336 | 1.0421 | +0.0085 | Yes |
| 190 | conservative | aggressive | 0.9979 | 1.0399 | +0.0421 | Yes |
| 197 | aggressive | conservative | 1.0163 | 1.0040 | -0.0123 | No |
| 199 | conservative | aggressive | 1.0174 | 1.0259 | +0.0085 | Yes |
| 208 | aggressive | conservative | 1.0284 | 1.0393 | +0.0109 | Yes |
| 210 | conservative | aggressive | 1.0186 | 1.0474 | +0.0288 | Yes |

## Oscillation Detection

- Rapid re-switches (within 3 windows): 2498
- Oscillation windows: [62, 92, 99, 102, 104, 111, 120, 138, 140, 142, 151, 167, 170, 172, 183, 190, 199, 210, 216, 218]...

## Class Stability

- Class changes: 5104 / 10965 windows (46.5%)

## IPC by Mode

| Mode | Windows | Mean IPC | Min IPC | Max IPC |
|------|---------|----------|---------|---------|
| aggressive | 7681 | 1.0267 | 0.8926 | 2.0006 |
| conservative | 3284 | 1.0189 | 0.9074 | 1.2246 |

## Class -> Mode Mapping (observed)

| Class | Mode | Count |
|-------|------|-------|
| High-MLP memory dominated | aggressive | 5441 |
| Resource-contention / compute dominated | aggressive | 1702 |
| Resource-contention / compute dominated | conservative | 1642 |
| Serialized-memory dominated | conservative | 1463 |
| Serialized-memory dominated | aggressive | 426 |
| Control dominated | conservative | 179 |
| Control dominated | aggressive | 112 |
