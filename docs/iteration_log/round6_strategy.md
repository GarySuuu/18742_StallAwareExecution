# Round 6 Strategy — Serialized子分级

## 问题诊断

当前3级（Aggressive/LightConservative/Conservative），但GAPBS全部走Serialized→LightConservative，用同一套fw=4参数。这导致：
- tc（高squash，70%窗口squash_ratio>0.2）：fw=4刚好，IPC+4.1%，WPE+9.4%
- bfs/bc/pr/cc（低squash，squash_ratio多在0.05-0.15）：fw=4过强，IPC-4~5%

## 方案：Serialized子分级

在LightConservative模式内部，加一个squash_ratio检查：
- **Serialized + 高squash**（squash_ratio >= 阈值）→ 强throttle（fw=4, cap=128）——适合tc
- **Serialized + 低squash**（squash_ratio < 阈值）→ 弱throttle（fw=5或fw=6, cap=128）——适合bfs/bc/pr/cc

这类似于已有的ResourceTight子分级机制（adaptiveShouldUseTightResourceProfile）。

## 实现方式

**不需要改代码**。可以利用现有的EMA信号去耦合+信号分析来验证方案。但要真正实现子分级需要改cpu.cc。

**更快的验证方案**：先分析GAPBS窗口的squash_ratio分布，确定合适的阈值，然后再决定是否值得改代码。

## 执行计划

### Phase A：分析GAPBS窗口squash_ratio分布

对v3t4（fw=4）和v3t7（fw=5）的GAPBS运行结果，从adaptive_window_log.csv中提取每个benchmark的squash_ratio分布。具体：
1. 读取每个GAPBS benchmark的v3t4 window log
2. 统计squash_ratio的分布（均值、P25、P50、P75、P90）
3. 分析tc vs 其他benchmark的squash_ratio差异
4. 确定一个阈值，使得tc的大部分窗口在阈值以上，其他benchmark的大部分窗口在阈值以下

### Phase B：实现Serialized子分级

在cpu.cc中：
1. 在adaptiveAdvanceWindow()中，当分类为Serialized时，额外检查squash_ratio
2. 如果squash_ratio >= 阈值，标记为"tight serialized"
3. tight serialized用fw=4参数，普通serialized用fw=5或fw=6参数

新增参数（BaseO3CPU.py）：
- adaptiveSerializedTightSquashThres（阈值）
- adaptiveSerializedTightFetchWidth
- adaptiveSerializedTightInflightCap

### Phase C：编译+测试

跑6个GAPBS + 6个micro，计算WPE，验证：
- tc维持WPE > +5%
- bfs/bc/pr/cc的IPC损失 < -3%
- GAPBS avg WPE > +1%

## 成功标准

- GAPBS avg WPE >= +1.0%
- tc WPE >= +5%
- 至少5/6个GAPBS的dIPC > -3%
- Overall WPE > +1.5%
