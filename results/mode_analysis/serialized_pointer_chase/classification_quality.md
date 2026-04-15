# Classification Quality Report: serialized_pointer_chase

**Log**: `runs/adaptive/v2/serialized_pointer_chase/latest/adaptive_window_log.csv`

**Total windows**: 12817


## Switch Quality (3655 switches analyzed)

- Beneficial switches (IPC improved): 1829 (50.0%)
- Harmful switches (IPC degraded): 1826 (50.0%)
- Average IPC delta after switch: 0.000174

| Window | Old Mode | New Mode | Before IPC | After IPC | Delta | Beneficial? |
|--------|----------|----------|------------|-----------|-------|-------------|
| 5500 | aggressive | conservative | 0.5893 | 0.8023 | +0.2129 | Yes |
| 5502 | conservative | aggressive | 0.6809 | 0.8556 | +0.1747 | Yes |
| 5504 | aggressive | conservative | 0.8023 | 0.8774 | +0.0751 | Yes |
| 5506 | conservative | aggressive | 0.8556 | 0.9251 | +0.0695 | Yes |
| 5508 | aggressive | conservative | 0.8774 | 0.8264 | -0.0510 | No |
| 5510 | conservative | aggressive | 0.9251 | 0.9169 | -0.0082 | No |
| 5512 | aggressive | conservative | 0.8264 | 0.8374 | +0.0110 | Yes |
| 5514 | conservative | aggressive | 0.9169 | 0.9028 | -0.0141 | No |
| 5516 | aggressive | conservative | 0.8374 | 0.8463 | +0.0089 | Yes |
| 5518 | conservative | aggressive | 0.9028 | 0.8990 | -0.0038 | No |
| 5520 | aggressive | conservative | 0.8463 | 0.8359 | -0.0104 | No |
| 5522 | conservative | aggressive | 0.8990 | 0.9165 | +0.0175 | Yes |
| 5524 | aggressive | conservative | 0.8359 | 0.8631 | +0.0273 | Yes |
| 5526 | conservative | aggressive | 0.9165 | 0.9397 | +0.0232 | Yes |
| 5528 | aggressive | conservative | 0.8631 | 0.8238 | -0.0393 | No |
| 5530 | conservative | aggressive | 0.9397 | 0.8941 | -0.0456 | No |
| 5532 | aggressive | conservative | 0.8238 | 0.8596 | +0.0358 | Yes |
| 5534 | conservative | aggressive | 0.8941 | 0.9366 | +0.0425 | Yes |
| 5536 | aggressive | conservative | 0.8596 | 0.8330 | -0.0266 | No |
| 5538 | conservative | aggressive | 0.9366 | 0.9329 | -0.0037 | No |
| 5540 | aggressive | conservative | 0.8330 | 0.8455 | +0.0125 | Yes |
| 5542 | conservative | aggressive | 0.9329 | 0.8991 | -0.0337 | No |
| 5544 | aggressive | conservative | 0.8455 | 0.8179 | -0.0276 | No |
| 5546 | conservative | aggressive | 0.8991 | 0.9060 | +0.0069 | Yes |
| 5548 | aggressive | conservative | 0.8179 | 0.8310 | +0.0131 | Yes |
| 5550 | conservative | aggressive | 0.9060 | 0.8846 | -0.0214 | No |
| 5552 | aggressive | conservative | 0.8310 | 0.8700 | +0.0390 | Yes |
| 5554 | conservative | aggressive | 0.8846 | 0.9067 | +0.0221 | Yes |
| 5556 | aggressive | conservative | 0.8700 | 0.8399 | -0.0301 | No |
| 5558 | conservative | aggressive | 0.9067 | 0.9175 | +0.0108 | Yes |

## Oscillation Detection

- Rapid re-switches (within 3 windows): 3655
- Oscillation windows: [5502, 5504, 5506, 5508, 5510, 5512, 5514, 5516, 5518, 5520, 5522, 5524, 5526, 5528, 5530, 5532, 5534, 5536, 5538, 5540]...

## Class Stability

- Class changes: 3665 / 12817 windows (28.6%)

## IPC by Mode

| Mode | Windows | Mean IPC | Min IPC | Max IPC |
|------|---------|----------|---------|---------|
| aggressive | 9160 | 0.7608 | 0.4896 | 1.2088 |
| conservative | 3657 | 0.9307 | 0.6776 | 1.2194 |

## Class -> Mode Mapping (observed)

| Class | Mode | Count |
|-------|------|-------|
| Resource-contention / compute dominated | aggressive | 7346 |
| Control dominated | conservative | 1829 |
| Resource-contention / compute dominated | conservative | 1828 |
| Control dominated | aggressive | 1814 |
