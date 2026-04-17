# Round 2 Strategy

## Round 1 结果摘要

- V3t2 micro avg WPE = +2.28% > V2 micro avg = +0.81% ✓
- V3t2 GAPBS avg WPE = -3.06% < V2 GAPBS avg = +1.12% ✗
- **根因**：GAPBS 39-45%的窗口被分类为Control → deep Conservative（fw=4, cap=48, iqcap=20, lsqcap=16）→ IPC损失5-9%，WPE惩罚严重
- **关键证据**：gapbs_sssp是100% Serialized → LightConservative，WPE只损失-0.39%，和V2几乎持平。**说明LightConservative对GAPBS是可以接受的，deep Conservative才是问题。**

## Round 2 策略

### 核心改动：Control也映射到LightConservative

Round 1证明了：
- LightConservative（fw=6, cap=56, iqcap=26, lsqcap=28）对大部分workload是安全的
- Deep Conservative对GAPBS有害

因此Round 2的映射改为：
- HighMLP → Aggressive
- Resource → Aggressive  
- **Serialized → LightConservative**
- **Control → LightConservative**（从deep改为light）

这实质上是**取消deep conservative**，让所有throttle都用sweet spot参数。Deep conservative级别暂时保留在代码中但不使用。

### 为什么这样做

1. Control窗口在GAPBS上占39-45%，是GAPBS退化的直接原因
2. Control窗口特征是高branch recovery + 高squash ratio，这些窗口确实需要某种throttle来减少投机浪费
3. 但fw=4 + iqcap=20 + lsqcap=16太激进——这些参数在Task 2 sweep中对应的IPC损失约10-14%
4. LightConservative的fw=6 + iqcap=26 + lsqcap=28更温和，在branch_entropy（也是Control-like行为）上效果极好（WPE +13.63%）

### 这不需要重新编译

只需要修改代码中的一行映射（Control → LightConservative instead of Conservative），然后重编译。

但实际上，有一个更快的方案：**通过--param把conservative的参数覆盖为和light相同的值**，这样Control→Conservative和Serialized→LightConservative用的是一样的参数。不需要重编译！

具体：
```
--conservative-fetch-width 6
--conservative-inflight-cap 56
--conservative-iq-cap 26
--conservative-lsq-cap 28
```

这样Conservative mode的参数和LightConservative完全一样，等效于所有throttle都用sweet spot。

### 测试要求

1. 跑12个workload（6 micro + 6 GAPBS），tag=v3ml_t3
2. 使用以上--param覆盖conservative参数
3. mem_block_ratio保持0.12
4. 跑McPAT
5. 计算WPE，对比V2
6. 分析mode distribution，确认GAPBS的Control窗口现在用的是sweet spot参数

### 成功标准

- avg WPE > V2的+1.0%
- 没有任何workload WPE < -3%
- micro avg WPE维持在+2%以上（不能因为GAPBS修复而退化micro）
