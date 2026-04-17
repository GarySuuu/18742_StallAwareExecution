# Round 5 Strategy — 最终优化

## 当前最佳：v3t4 GAPBS + v3t3 micro = +2.10% avg WPE

Round 4证明fw=5和fw=4+iq/lsq都不如v3t4的纯fw=4/cap=128。v3t4的GAPBS weak spots是：
- cc: -0.88% WPE（IPC -5.1%换Energy -14.5%，不够）
- bc: -0.08%（几乎持平）

## Round 5 思路：优化分类阈值减少不必要的throttle

当前GAPBS的分类分布（以v3t4为参考）：
- bfs: 47% Aggressive + 53% Conservative（Control窗口）
- bc: 41% Aggressive + 59% Conservative
- pr: 44% Aggressive + 56% Conservative
- cc: 49% Aggressive + 51% Conservative
- sssp: 100% LightConservative（Serialized）
- tc: 33% Aggressive + 67% Conservative

cc和bc的问题是**太多窗口被分类为Control→Conservative**。如果能减少Control分类的比例（让更多窗口留在Resource→Aggressive），就能减少不必要的IPC损失。

方法：**提高Control分类的阈值**——让只有"真正严重"的branch-recovery + squash才触发Control，边缘case回到Resource→Aggressive。

当前阈值：
- branch_recovery_ratio >= 0.10 AND squash_ratio >= 0.20 → Control

尝试：
- **Config A**：branch_recovery >= 0.15 AND squash_ratio >= 0.25（更严格，减少Control分类）
- **Config B**：branch_recovery >= 0.12 AND squash_ratio >= 0.22（微调）

这可以通过--param覆盖，不需要编译：
```
--param "system.cpu[0].adaptiveBranchRecoveryRatioThres=0.15"
--param "system.cpu[0].adaptiveSquashRatioThres=0.25"
```

## 执行计划

对6个GAPBS跑两组阈值配置，其他params维持v3t4（fw=4, cap=128, iq=0, lsq=0, window=2500, mem_block=0.12）。

**Config A (v3t6a)**：strict Control阈值 (branch>=0.15, squash>=0.25)
**Config B (v3t6b)**：mild Control阈值 (branch>=0.12, squash>=0.22)

观察：
1. Control窗口占比是否下降
2. cc和bc的WPE是否改善
3. tc的WPE是否受损（tc依赖Control→Conservative，如果Control减少tc可能变差）

## 成功标准

- 任一Config的GAPBS avg WPE > v3t4的+1.64%
- 如果不行，至少改善cc/bc而不损害tc
