# Classification Quality Report: phase_scan_mix

**Log**: `runs/adaptive/v2/phase_scan_mix/latest/adaptive_window_log.csv`

**Total windows**: 21206


## Switch Quality (2462 switches analyzed)

- Beneficial switches (IPC improved): 1215 (49.4%)
- Harmful switches (IPC degraded): 1247 (50.6%)
- Average IPC delta after switch: 0.000043

| Window | Old Mode | New Mode | Before IPC | After IPC | Delta | Beneficial? |
|--------|----------|----------|------------|-----------|-------|-------------|
| 2979 | aggressive | conservative | 0.5010 | 0.2138 | -0.2872 | No |
| 2992 | conservative | aggressive | 0.3176 | 0.3317 | +0.0141 | Yes |
| 2994 | aggressive | conservative | 0.2955 | 0.3317 | +0.0363 | Yes |
| 3000 | conservative | aggressive | 0.3293 | 0.3109 | -0.0185 | No |
| 3002 | aggressive | conservative | 0.3345 | 0.3341 | -0.0003 | No |
| 3006 | conservative | aggressive | 0.3341 | 0.3524 | +0.0183 | Yes |
| 3008 | aggressive | conservative | 0.3339 | 0.3572 | +0.0233 | Yes |
| 3010 | conservative | aggressive | 0.3524 | 0.3489 | -0.0035 | No |
| 3012 | aggressive | conservative | 0.3572 | 0.3637 | +0.0065 | Yes |
| 3014 | conservative | aggressive | 0.3489 | 0.3657 | +0.0168 | Yes |
| 3016 | aggressive | conservative | 0.3637 | 0.3628 | -0.0009 | No |
| 3020 | conservative | aggressive | 0.3628 | 0.3602 | -0.0026 | No |
| 3022 | aggressive | conservative | 0.3680 | 0.3667 | -0.0013 | No |
| 3028 | conservative | aggressive | 0.3361 | 0.3313 | -0.0048 | No |
| 3030 | aggressive | conservative | 0.3469 | 0.3405 | -0.0064 | No |
| 3034 | conservative | aggressive | 0.3405 | 0.3605 | +0.0199 | Yes |
| 3036 | aggressive | conservative | 0.3403 | 0.3497 | +0.0095 | Yes |
| 3041 | conservative | aggressive | 0.3395 | 0.3487 | +0.0092 | Yes |
| 3043 | aggressive | conservative | 0.3619 | 0.3799 | +0.0180 | Yes |
| 3045 | conservative | aggressive | 0.3487 | 0.3661 | +0.0175 | Yes |
| 3047 | aggressive | conservative | 0.3799 | 0.3613 | -0.0187 | No |
| 3050 | conservative | aggressive | 0.3599 | 0.3468 | -0.0131 | No |
| 3052 | aggressive | conservative | 0.3579 | 0.3547 | -0.0031 | No |
| 3054 | conservative | aggressive | 0.3468 | 0.3606 | +0.0138 | Yes |
| 3056 | aggressive | conservative | 0.3547 | 0.3643 | +0.0095 | Yes |
| 3058 | conservative | aggressive | 0.3606 | 0.3790 | +0.0184 | Yes |
| 3060 | aggressive | conservative | 0.3643 | 0.3465 | -0.0178 | No |
| 3062 | conservative | aggressive | 0.3790 | 0.3306 | -0.0484 | No |
| 3064 | aggressive | conservative | 0.3465 | 0.3404 | -0.0061 | No |
| 3067 | conservative | aggressive | 0.3475 | 0.3500 | +0.0025 | Yes |

## Oscillation Detection

- Rapid re-switches (within 3 windows): 1921
- Oscillation windows: [2994, 3002, 3008, 3010, 3012, 3014, 3016, 3022, 3030, 3036, 3043, 3045, 3047, 3050, 3052, 3054, 3056, 3058, 3060, 3062]...

## Class Stability

- Class changes: 3602 / 21206 windows (17.0%)

## IPC by Mode

| Mode | Windows | Mean IPC | Min IPC | Max IPC |
|------|---------|----------|---------|---------|
| aggressive | 10479 | 0.6695 | 0.2706 | 0.9600 |
| conservative | 10727 | 0.3537 | 0.1816 | 0.4548 |

## Class -> Mode Mapping (observed)

| Class | Mode | Count |
|-------|------|-------|
| Serialized-memory dominated | conservative | 10031 |
| Resource-contention / compute dominated | aggressive | 6280 |
| High-MLP memory dominated | aggressive | 2979 |
| Serialized-memory dominated | aggressive | 964 |
| Resource-contention / compute dominated | conservative | 446 |
| Control dominated | aggressive | 256 |
| Control dominated | conservative | 250 |
