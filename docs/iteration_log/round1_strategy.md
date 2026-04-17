# Round 1 Strategy

## 当前状态

V2-tuned是目前的最佳基准：avg WPE = +1.0%（12个workload）。

过去三次V3尝试的结果：
- V3-sweetspot-only（fw=6,cap=56,iqcap=26,lsqcap=28）: avg WPE +1.1%，micro上好但GAPBS power/energy节省不够
- V3ml（Resource→LightCons, mem_block=0.08）: avg WPE -2.2%，GAPBS灾难（100% deep conservative）
- V3ml_t1（Resource→LightCons, mem_block=0.12）: avg WPE -0.8%，GAPBS仍然差（Resource窗口被LightCons拖慢）

## 根因分析

1. **Sweet spot参数只对高IPC workload有效**。balanced_pipeline_stress(IPC=2.9)和branch_entropy(IPC=0.9)从sweet spot获益，但GAPBS(IPC=1.3-1.4)和stream_cluster_reduce(IPC=0.5)受损。原因：sweet spot是在IPC=2.9的workload上找到的，不适用于低IPC workload。

2. **Resource→LightConservative映射是错误的**。大部分workload的大部分窗口都是Resource类（因为default fallback是Resource）。把Resource映射到任何throttle都会影响大量不需要throttle的窗口。

3. **分类漂移问题**：conservative参数改变pipeline信号→改变分类→反馈环。信号去耦合（只在aggressive下更新EMA）有帮助但不够。

4. **V2在GAPBS上的优势来自V2-tuned的特殊配置**：window=2500, fw=4, cap=128。这不是V2的default，是专门为GAPBS调优的。我们的V3没有做类似的per-workload-type调优。

## Round 1 策略

**核心思路**：不追求一个通用的conservative配置。改为让multi-level准确区分需要throttle和不需要throttle的窗口。

**具体改动（已在编译中）**：
- Resource → **Aggressive**（回到baseline，不throttle）
- HighMLP → **Aggressive**（不变）
- Serialized → **LightConservative**（sweet spot: fw=6, cap=56, iqcap=26, lsqcap=28）
- Control → **Conservative**（deep: fw=4, cap=48, iqcap=20, lsqcap=16）
- mem_block_ratio阈值保持V2的0.12（通过--param覆盖）
- EMA信号去耦合保持启用

**预期效果**：
- Resource/HighMLP窗口完全不受影响（=baseline），GAPBS应该恢复
- Serialized窗口用sweet spot而非V2的fw=2，应该比V2更温和
- Control窗口用deep throttle，对branch-heavy phase有效
- branch_entropy应该继续受益（大部分窗口因classification drift变成Serialized→LightCons）

**测试要求**：
1. 6个micro + 6个GAPBS，每个50M指令
2. 每个跑baseline + v3ml_t2
3. 跑McPAT获取power/energy
4. 用WPE=(IPC)^0.8×(E_bl/E)^0.2评估
5. 分析每个workload的mode distribution
6. 与V2对比，输出完整的WPE对比表

**成功标准**：avg WPE > V2的+1.0%，且没有任何workload的WPE < -3%
