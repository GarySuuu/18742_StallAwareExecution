# Round 4 Strategy — 精细化调优

## 当前状态 (v3t4)

Overall avg WPE = +1.91%, GAPBS avg = +1.43%, Micro avg = +2.39%

### GAPBS逐benchmark分析

| Bench | v3t4 WPE | V2 WPE | 问题 |
|-------|---------|--------|------|
| tc | **+9.39%** | +7.38% | 已经很好 |
| bfs | +0.26% | +0.11% | 微赢V2，但接近0 |
| sssp | +0.23% | +0.14% | 微赢V2，但接近0 |
| pr | +0.04% | -0.10% | 基本持平 |
| bc | -0.26% | -0.22% | 微输V2 |
| cc | **-1.08%** | -0.57% | 最差点，输V2 0.51pp |

### 分析：为什么bfs/bc/pr/cc的WPE接近0或为负

v3t4 GAPBS配置是fw=4, cap=128, iq=0, lsq=0。这在tc上极好（+9.39%），但在其他5个benchmark上效果平平。原因：

1. **tc是特殊的**：70%窗口是Control（高squash），fw=4在tc上既提升了IPC（+4.1%，因为减少了投机浪费）又大幅降低Energy（-25%）。
2. **其他GAPBS（bfs/bc/pr/cc）**：只有40-54%是Control，剩余是Resource→Aggressive。fw=4对这些benchmark的Energy savings约-14%~-19%，但IPC损失约-4%~-5%。在80/20 WPE权重下，IPC损失惩罚大于Energy收益。

### 改进方向

**尝试fw=5作为GAPBS compromise**：
- fw=5在tc sweep中WPE≈+5.0%（vs fw=4的+9.4%），牺牲了4.4pp
- 但fw=5在其他GAPBS上IPC损失应该更小（约-2%而非-4%），Energy savings中等（约-13%而非-19%）
- 净效果：tc上损失一些，但bfs/bc/pr/cc上改善，可能提升GAPBS avg

**同时尝试window=2500 vs window=5000的影响**——Round 3的tc sweep全用window=2500，但还没验证window size对其他GAPBS的影响。

## Round 4 执行计划

跑两组GAPBS配置（micro保持不变）：

**Config A (fw=5 compromise)**:
- GAPBS: fw=5, cap=96, iq=0, lsq=0, window=2500, mem_block=0.12
- tag: v3t5a

**Config B (fw=4 with iq/lsq assist)**:
- GAPBS: fw=4, cap=128, iq=26, lsq=28, window=2500, mem_block=0.12
- 在fw=4的基础上加上IQ/LSQ cap的sweet spot——Round 3 sweep显示iq/lsq对tc影响很小（<0.2pp），但可能对其他GAPBS有帮助（减少IQ拥塞）
- tag: v3t5b

每组跑6个GAPBS + McPAT，与baseline和V2对比WPE。Micro复用v3t3/v3t4结果。

## 成功标准

- GAPBS avg WPE > v3t4的+1.43%
- Overall avg WPE > v3t4的+1.91%
- 没有任何workload < -3%
