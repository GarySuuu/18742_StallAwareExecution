# Signal Correlation Report: phase_scan_mix

**Log**: `runs/adaptive/v2/phase_scan_mix/latest/adaptive_window_log.csv`

**Windows**: 21206


## Signal-to-Classification Correlations

| Signal | Corr(class) | Corr(mode) | Corr(IPC) | Mean | Std |
|--------|-------------|------------|-----------|------|-----|
| _mem_block_ratio | +0.112 | +0.364 | -0.571 | 0.1511 | 0.0515 |
| avg_outstanding_misses_proxy | -0.762 | -0.597 | +0.299 | 12.7268 | 7.6965 |
| iq_saturation_ratio | +0.142 | -0.234 | +0.614 | 0.2897 | 0.1729 |
| branch_recovery_ratio | +0.585 | +0.669 | -0.814 | 0.0504 | 0.0418 |
| squash_ratio | +0.687 | +0.798 | -0.865 | 0.3495 | 0.2733 |
| commit_activity_ratio | -0.648 | -0.745 | +0.858 | 0.5891 | 0.3244 |
| avg_inflight_proxy | +0.426 | +0.080 | +0.299 | 62.7871 | 25.7036 |

## Threshold Boundary Analysis

Windows where signals are within 20% of decision thresholds:

- **mem_block_ratio** (threshold=0.12): 4141 borderline windows (19.5%)
- **avg_outstanding_misses_proxy** (threshold=12.0): 7442 borderline windows (35.1%)
- **branch_recovery_ratio** (threshold=0.1): 2648 borderline windows (12.5%)
- **squash_ratio** (threshold=0.2): 1 borderline windows (0.0%)
- **iq_saturation_ratio** (threshold=0.1): 54 borderline windows (0.3%)
- **commit_activity_ratio** (threshold=0.2): 2416 borderline windows (11.4%)
- **avg_inflight_proxy** (threshold=32.0): 0 borderline windows (0.0%)

## Signal Statistics by Class


### Control dominated (506 windows)

| Signal | Mean | Min | Max | Std |
|--------|------|-----|-----|-----|
| _mem_block_ratio | 0.1029 | 0.0530 | 0.1198 | 0.0132 |
| avg_outstanding_misses_proxy | 10.0867 | 9.2236 | 11.0022 | 0.2924 |
| iq_saturation_ratio | 0.3897 | 0.2284 | 0.5058 | 0.0454 |
| branch_recovery_ratio | 0.1170 | 0.1000 | 0.1398 | 0.0077 |
| squash_ratio | 0.5405 | 0.5070 | 0.5804 | 0.0133 |
| commit_activity_ratio | 0.2132 | 0.1738 | 0.2586 | 0.0140 |
| avg_inflight_proxy | 83.8829 | 78.0332 | 89.2696 | 1.9036 |

### High-MLP memory dominated (2979 windows)

| Signal | Mean | Min | Max | Std |
|--------|------|-----|-----|-----|
| _mem_block_ratio | 0.2149 | 0.1752 | 0.3168 | 0.0156 |
| avg_outstanding_misses_proxy | 30.9470 | 27.7496 | 31.1390 | 0.0883 |
| iq_saturation_ratio | 0.0000 | 0.0000 | 0.0654 | 0.0012 |
| branch_recovery_ratio | 0.0000 | 0.0000 | 0.0148 | 0.0003 |
| squash_ratio | 0.0001 | 0.0000 | 0.1643 | 0.0030 |
| commit_activity_ratio | 0.9999 | 0.7498 | 1.0300 | 0.0072 |
| avg_inflight_proxy | 5.4454 | 4.5026 | 21.1518 | 0.4245 |

### Resource-contention / compute dominated (6726 windows)

| Signal | Mean | Min | Max | Std |
|--------|------|-----|-----|-----|
| _mem_block_ratio | 0.0909 | 0.0380 | 0.1198 | 0.0101 |
| avg_outstanding_misses_proxy | 12.0405 | 6.8640 | 13.4998 | 2.3917 |
| iq_saturation_ratio | 0.4613 | 0.1022 | 0.6080 | 0.1279 |
| branch_recovery_ratio | 0.0180 | 0.0000 | 0.0998 | 0.0311 |
| squash_ratio | 0.1407 | 0.0000 | 0.6680 | 0.2430 |
| commit_activity_ratio | 0.8426 | 0.2036 | 1.0068 | 0.2716 |
| avg_inflight_proxy | 81.0673 | 55.4730 | 89.8368 | 10.7663 |

### Serialized-memory dominated (10995 windows)

| Signal | Mean | Min | Max | Std |
|--------|------|-----|-----|-----|
| _mem_block_ratio | 0.1730 | 0.1200 | 0.2976 | 0.0327 |
| avg_outstanding_misses_proxy | 8.3314 | 6.7040 | 11.4364 | 0.9314 |
| iq_saturation_ratio | 0.2585 | 0.0624 | 0.5308 | 0.0733 |
| branch_recovery_ratio | 0.0808 | 0.0470 | 0.1398 | 0.0179 |
| squash_ratio | 0.5631 | 0.4500 | 0.7813 | 0.0288 |
| commit_activity_ratio | 0.3401 | 0.1622 | 0.4669 | 0.0647 |
| avg_inflight_proxy | 66.1699 | 53.8360 | 92.8150 | 8.7120 |

## IPC Distribution by Class

| Class | Windows | Mean IPC | Std IPC |
|-------|---------|----------|---------|
| Control dominated | 506 | 0.3541 | 0.0260 |
| High-MLP memory dominated | 2979 | 0.5280 | 0.0313 |
| Resource-contention / compute dominated | 6726 | 0.7696 | 0.2412 |
| Serialized-memory dominated | 10995 | 0.3531 | 0.0257 |
