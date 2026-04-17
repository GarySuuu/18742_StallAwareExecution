# Round 7 Strategy — 逐窗口分析 + IPC优化

## 当前最佳：v3t8, Overall WPE = +2.14%

GAPBS IPC损失仍然偏大（bfs -3.6%, bc -3.8%, pr -3.6%, cc -3.5%）。需要通过逐窗口分析找出根因，然后针对性调整。

## Phase A：逐窗口深度分析

对v3t8的所有12个workload的adaptive_window_log.csv进行分析：

### 对GAPBS（重点）：
1. **per-window IPC分布**：计算每个窗口的IPC proxy（committed_insts / cycles），按模式（aggressive/light-conservative/ser-tight）分组统计IPC均值和标准差
2. **tight vs normal IPC对比**：tight窗口的IPC是否真的比normal低？如果tight窗口IPC其实也很高，说明fw=4对它们也过强
3. **squash_ratio阈值敏感性**：如果把阈值从0.30调高到0.35或0.40，tight%如何变化？是否能进一步减少不必要的强throttle？
4. **fw=5 normal窗口的IPC影响**：对比v3t8的normal窗口IPC和baseline的对应窗口IPC。如果fw=5让IPC下降了3-4%但squash_ratio很低（说明不需要throttle），那fw=6可能更合适

### 对Micro（验证）：
5. branch_entropy和phase_scan_mix的tight%和WPE来源

## Phase B：基于分析的参数调整

根据Phase A发现，可能的调整：
- 如果normal窗口的IPC损失是GAPBS退化的主因，把normal的fw从5提高到6
- 如果tight窗口的阈值太低导致太多窗口被强throttle，提高阈值到0.35
- 或者两者组合

不需要重编译——所有参数通过--param覆盖：
- adaptiveSerializedTightSquashThres（阈值）
- adaptiveLightConsFetchWidth（normal fw）
- adaptiveSerializedTightFetchWidth（tight fw）

## Phase C：测试新配置

跑12个workload + McPAT，计算WPE，对比v3t8和V2。

## 成功标准
- Overall WPE > v3t8的+2.14%
- GAPBS IPC损失改善（至少3个benchmark的dIPC > -3%）
