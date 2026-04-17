# Round 3 Strategy — GAPBS优化

## 当前GAPBS状态

| Bench | V2-tuned WPE | V3t3 WPE | Gap |
|-------|-------------|----------|-----|
| bfs   | +0.11% | +0.40% | V3赢+0.29pp |
| bc    | -0.22% | -0.36% | V2赢+0.14pp |
| pr    | -0.10% | +0.19% | V3赢+0.29pp |
| cc    | -0.57% | -0.04% | V3赢+0.53pp |
| sssp  | +0.14% | -0.39% | V2赢+0.53pp |
| tc    | **+7.38%** | +1.97% | V2赢+5.41pp |
| **Avg** | **+1.12%** | +0.30% | V2赢+0.82pp |

V3t3在bfs/pr/cc上微赢V2，在bc/sssp上微输，**tc是决定性的差距**（V2 +7.38% vs V3 +1.97%）。

## 根因分析

### 为什么V3t3在GAPBS上效果平平

1. **Sweet spot参数是为IPC=2.9的workload设计的**。GAPBS的IPC=1.3-1.4，pipeline行为完全不同。fw=6在IPC=1.4的workload上几乎不限制fetch（实际fetch rate已经低于6），所以fw=6 ≈ fw=8 ≈ baseline对GAPBS没有throttle效果。

2. **V2-tuned的优势来自两个GAPBS专属调优**：
   - `window=2500`（不是5000）——graph workload的phase变化更快，短窗口响应更快
   - `fw=4`——在IPC=1.4的workload上fw=4确实能限制前端，减少投机浪费
   - `cap=128`——比baseline ROB=192适度限制

3. **V3t3在GAPBS上本质上≈baseline**——sweet spot参数对低IPC workload没有有意义的throttle效果。V3t3的GAPBS WPE≈0%正好说明了这一点。

### tc是关键——V2在tc上的+7.38%怎么来的

tc（triangle counting）的baseline IPC=1.346，V2-tuned的IPC=1.391（+3.3%）且Energy从5.46J降到4.36J（-20.1%）。V2-tuned在tc上同时提升了IPC和大幅降低了Energy——这和Task 3中发现的serialized_pointer_chase的"conservative IPC > aggressive IPC"现象一致。tc的大量投机执行（约70%窗口是Control/高squash）在V2的fw=4下被有效控制。

## Round 3 策略

### 核心思路：对GAPBS使用更强的throttle参数

V3t3的sweet spot（fw=6, cap=56, iqcap=26, lsqcap=28）对GAPBS太温和了。需要一组**更强的GAPBS-tuned参数**。

### 具体方案：在GAPBS上做参数扫描，找到GAPBS的sweet spot

由于不能对每个workload单独调参（实际部署中不知道workload是什么），但我们可以：
1. 用V2-tuned的window=2500（已验证对GAPBS有效）
2. 在tc上做一组快速参数扫描（fw=3/4/5/6, cap=48/64/96/128, iqcap=0/20/26, lsqcap=0/16/28），找出对GAPBS最优的参数
3. 然后用找到的参数跑全部6个GAPBS确认

### 执行步骤

**Phase A**：在gapbs_tc上做快速扫描（tc是V2最大的优势点，优化tc就能大幅拉近差距）
- 12-16个参数组合，每个50M指令，强制conservative模式（mem_block=0.0 + outstanding_miss=9999）
- 观测IPC + Energy，计算WPE
- 找到GAPBS sweet spot

**Phase B**：用GAPBS sweet spot作为新的conservative参数，跑全部6个GAPBS + 6个micro
- 如果GAPBS sweet spot和micro sweet spot不同，则需要两组参数——Serialized用一组（micro sweet spot），Control用另一组（GAPBS sweet spot）
- 这正是multi-level存在的意义

**Phase C**：如果GAPBS sweet spot确实不同，重新编译让Serialized和Control用不同参数

### 成功标准

- GAPBS avg WPE > V2-tuned的+1.12%
- tc的WPE > +3%（至少接近V2的+7.38%的一半）
- micro avg WPE维持在+2%以上
