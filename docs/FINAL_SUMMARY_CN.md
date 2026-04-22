# 自适应O3 CPU功耗优化 — 最终总结

**18-742课程项目**：在gem5 `DerivO3CPU`（ARM, SE模式）上实现运行时自适应throttle机制，在最小化性能损失的前提下降低功耗和能耗。

**最终结果**：V4实现 **Overall EDP +13.36%**（Micro +14.70%，GAPBS +12.03%）对比baseline，12个workload（6 micro + 6 GAPBS）全部使用完全相同的统一参数。单workload最佳结果：branch_entropy EDP +39.6%。

---

## 目录

1. [项目概述](#1-项目概述)
2. [评估指标：EDP](#2-评估指标edp)
3. [Part I: 分析](#part-i-分析)
   - 3.1 参数分类
   - 3.2 参数扫描与Sweet Spot发现
   - 3.3 逐窗口模式分析
   - 3.4 Window Size扫描
4. [Part II: 设计与实现](#part-ii-设计与实现)
   - 4.1 三层Execution Mode
   - 4.2 Resource拥塞检测
   - 4.3 自适应Window Size
   - 4.4 统一配置
5. [迭代过程（8轮）](#5-迭代过程8轮)
6. [最终结果](#6-最终结果)
   - 6.1 单核结果（12个workload）
   - 6.2 多核结果（4核）
   - 6.3 最佳案例vs最差案例分析
7. [关键经验与放弃的方向](#7-关键经验与放弃的方向)

---

## 1. 项目概述

**目标平台**：单核（后扩展至4核）`DerivO3CPU`，ARM架构，SE模式，含L1/L2缓存和2GB内存。

**核心假设**：某些执行窗口天然wide-parallel，适合aggressive执行；其他窗口被串行化内存访问或控制流恢复瓶颈，wide aggressive执行浪费功耗。如果能在线分类窗口并选择性进入conservative模式，可以改善性能-能耗权衡。

**架构设计**：在O3 CPU之上加一个controller：
- 每个窗口采样流水线行为
- 将窗口分类为4种stall类型之一
- 将分类映射到execution mode（Aggressive/Conservative/Deep Conservative）
- 在窗口边界调整fetch/inflight/IQ/LSQ限制

**V2基线**（前人工作）：2层模式（Aggressive/Conservative），固定conservative参数fw=2, cap=96。需要手动per-workload调优（如GAPBS用window=2500）。

**V4（本工作）**：3层模式 + Resource拥塞子检测 + 自适应window + 统一参数。

---

## 2. 评估指标：EDP

**EDP（能耗-延迟乘积）**：
```
EDP = Energy × Time（焦耳-秒，越低越好）
EDP改善% = (1 - EDP_new / EDP_baseline) × 100%
```

计算机架构领域的标准指标（Gonzalez & Horowitz 1996）。能耗和性能等权重。相比纯IPC对能耗节省更敏感。

---

## Part I: 分析

### 3.1 参数分类（Task 1）

对`BaseO3CPU.py`中39个adaptive参数按流水线阶段分类：

| 类别 | 数量 | 作用阶段 | 代表参数 |
|------|------|---------|---------|
| Frontend | 8 | 取指 | FetchWidth, IQCap, LSQCap |
| Backend | 19 | 执行/提交 | InflightCap, RenameWidth, DispatchWidth |
| Classification/Policy | 11 | 分类器 | MemBlockRatioThres, SwitchHysteresis |
| Window/Sampling | 1 | 窗口 | WindowCycles |

对每个参数追踪其在`cpu.cc`/`fetch.cc`中的使用位置，构建完整数据流图：参数定义 → 模式选择 → 各阶段throttle。

### 3.2 参数扫描与Sweet Spot发现（Task 2）

设计了均衡workload `balanced_pipeline_stress`（IPC=2.91），压测所有流水线阶段。对6个架构参数进行了74个dense sweep实验，观测16个底层流水线信号。

**核心发现——"过度投机"问题**：

Baseline 8-wide O3 CPU表现出burst-stall振荡：
- 33.6%的周期：取0条指令（被后端压力阻塞）
- 38.6%的周期：满取8条指令（全速）
- IQFullEvents = 2.75M，rename阻塞占9.8%周期

**5个参数存在sweet spot** —— 适度限制时IPC反而超过baseline：

| 参数 | Sweet Spot | dIPC | 机制 |
|------|-----------|------|------|
| IQ Cap | 26 | +5.3% | 减少IQ对rename的反压 |
| LSQ Cap | 28 | +5.0% | 消除96%的memory order violation |
| Inflight Cap | 52~72 | +4.4% | 间接控制IQ+LSQ填充 |
| Fetch Width | 6 | +3.3% | 前端吞吐匹配后端能力 |
| Dispatch Width | 5 | +1.5% | 减少IQ过度填充 |

**遮蔽关系**：Fetch Width遮蔽Inflight Cap（fw=2时cap=64/96/128的IPC完全一样）。Inflight Cap遮蔽IQ Cap。sweep下游参数时必须禁用上游遮蔽参数。

**方法**：通过`memBlockRatioThres=0.0 + outstandingMissThres=9999`强制conservative模式。sweet spot附近非均匀dense采样。

**已保存的图**（全部在 [gem5/results/charts/](../results/charts/) 下）：
- **单参数详细图**（每张PNG展示该参数对16个信号的全部影响）：
  - [sweep_detail_fetch_width.png](../results/charts/sweep_detail_fetch_width.png)
  - [sweep_detail_dispatch_width.png](../results/charts/sweep_detail_dispatch_width.png)
  - [sweep_detail_rename_width.png](../results/charts/sweep_detail_rename_width.png)
  - [sweep_detail_iq_cap.png](../results/charts/sweep_detail_iq_cap.png)
  - [sweep_detail_lsq_cap.png](../results/charts/sweep_detail_lsq_cap.png)
  - [sweep_detail_inflight_cap_rob.png](../results/charts/sweep_detail_inflight_cap_rob.png)
- **跨参数对比图**：
  - [sweep_ipc_all_groups.png](../results/charts/sweep_ipc_all_groups.png) — 所有参数对IPC影响的合并图
  - [sweep_width_comparison.png](../results/charts/sweep_width_comparison.png) — fetch/dispatch/rename width 叠加对比
  - [sweep_sweet_spot.png](../results/charts/sweep_sweet_spot.png) — sweet spot现象专题图
  - [sweep_masking_proof.png](../results/charts/sweep_masking_proof.png) — fw→inflight→IQ 遮蔽关系证据图
  - [sweep_signal_heatmap.png](../results/charts/sweep_signal_heatmap.png) — 16信号×参数值的热力图
  - [sweep_lsq_detail.png](../results/charts/sweep_lsq_detail.png) — LSQ专项深入图
- **单参数×单信号网格图**（6参数 × 16信号 = 96张 PNG）：[results/charts/sweep/\<参数\>/\<信号\>.png](../results/charts/sweep/) — 例如 [fetch_width/ipc.png](../results/charts/sweep/fetch_width/ipc.png)、[iq_cap/iq_full_events.png](../results/charts/sweep/iq_cap/iq_full_events.png)。
- **原始数据**：[results/sweep_signals.csv](../results/sweep_signals.csv)。

### 3.3 逐窗口模式分析（Task 3）

分析了3个代表性workload（phase_scan_mix, serialized_pointer_chase, branch_entropy）共21,000+窗口。

**核心发现**：

1. **`squash_ratio`是最强的分类信号**：与IPC的|r|=0.87，远高于`mem_block_ratio`的|r|=0.36。但原分类器决策树把mem_block_ratio作为一级判断——这是个设计弱点，直接推动了我们用squash做子分级。

2. **35.1%的窗口在`avg_outstanding_misses`阈值（12.0）附近振荡**——主要的模式切换噪声来源。

3. **分类器对serialized_pointer_chase存在盲点**：该workload被分为Serialized的窗口占0%，尽管workload确实是内存串行化的。原因：`mem_block_ratio` proxy在O3 CPU等待cache miss期间继续投机执行时灵敏度不足。

4. **Conservative模式IPC比Aggressive高22.3%**（在serialized_pointer_chase上）——直接验证了"过度投机"假设。8-wide前端在pointer-chase模式下浪费流水线资源执行几乎全被squash的投机指令。

5. **分类器精度不是关键**——只要两个模式的IPC差异不大，分类噪声不影响结果。

**已保存的图**（在 [gem5/results/mode_analysis/](../results/mode_analysis/) 下，每个workload一个目录）：
- `phase_scan_mix/` — [class_distribution.png](../results/mode_analysis/phase_scan_mix/phase_scan_mix_class_distribution.png)（4类窗口分布直方图）、[mode_timeline.png](../results/mode_analysis/phase_scan_mix/phase_scan_mix_mode_timeline.png)（逐窗口模式轨迹时间线）
- `serialized_pointer_chase/` — [class_distribution.png](../results/mode_analysis/serialized_pointer_chase/serialized_pointer_chase_class_distribution.png)、[mode_timeline.png](../results/mode_analysis/serialized_pointer_chase/serialized_pointer_chase_mode_timeline.png)
- `branch_entropy/` — [class_distribution.png](../results/mode_analysis/branch_entropy/branch_entropy_class_distribution.png)、[mode_timeline.png](../results/mode_analysis/branch_entropy/branch_entropy_mode_timeline.png)

### 3.4 Window Size扫描

对6个代表性workload扫描了9种window size（1000~10000）：

| Workload | 最佳Window | 行为 |
|----------|-----------|------|
| gapbs_tc | **1000** | phase变化快，短window显著更优（EDP +25.9% vs 5000的+18.9%） |
| gapbs_bfs | 1000 | 短window快速throttle |
| branch_entropy | 7500 | 稳态workload偏好大window |
| balanced_pipeline_stress | 4000 | 中等 |
| phase_scan_mix | 任意 | window size不敏感 |

**结论**：不同workload需要的window size差异巨大。这推动了自适应window机制的设计——消除手动per-workload选择。

---

## Part II: 设计与实现

### 4.1 三层Execution Mode

将V2的2层系统（Aggressive/Conservative）扩展为3层，加入基于squash的子级。

| 层级 | FetchWidth | 触发条件 | 设计理由 |
|------|-----------|---------|---------|
| **Aggressive** | 8 (baseline) | Resource或HighMLP窗口 | 这些窗口不需要throttle |
| **Conservative** | 5 | Serialized/Control且squash_ratio < 0.25 | 轻度throttle用于中等投机浪费 |
| **Deep Conservative** | 3 | Serialized且squash_ratio ≥ 0.25 | 重度投机浪费需要强throttle |

**分类流程**：
```
Step 1: mem_block_ratio >= 0.12 ?
  YES → outstanding_misses >= 12 ?
    YES → HighMLP → Aggressive
    NO  → Serialized
      → Step 1a: squash_ratio >= 0.25 ?
        YES → Deep Conservative (fw=3)
        NO  → Conservative (fw=5)
  NO →
Step 2: branch_recovery >= 0.10 AND squash >= 0.20 ?
  YES → Control → Conservative (fw=5)
  NO →
Step 3 (default): Resource → Aggressive
```

**阈值选择依据**：
- `mem_block_ratio = 0.12`：V2验证过的值。尝试过0.08导致GAPBS灾难性退化。
- `outstanding_misses = 12`：V2默认值。区分HighMLP（并行内存）和Serialized。
- `squash_ratio = 0.25`：Task 3数据驱动——tc有67%窗口≥0.25，bfs/cc/pr只有<14%。清晰分开高浪费窗口。

### 4.2 Resource拥塞检测

在Aggressive模式中，Resource窗口如果有高投机浪费，**自动启用sweet spot caps**（iqcap=26, lsqcap=28, inflight cap=56）。

**触发条件**：`commit_activity_ratio < 0.95` AND `IPC > 2.0`

**理由**：
- `commit_activity < 0.95`表示>5%指令被squash浪费——sweet spot caps减少IQ反压
- `IPC > 2.0` guard防止低IPC workload被误触发（低IPC workload的pipeline不拥塞）

**效果**：balanced_pipeline_stress（IPC=2.9，100% Resource）自动获得sweet spot——EDP从-0.6%提升到+15.8%。

### 4.3 自适应Window Size

Window大小根据分类变化频率自动调整：

```
每8个窗口检查分类变化率：
  changeRate = (分类变化次数) / 8
  if changeRate > 0.3:   windowCycles = max(windowCycles / 2, 1000)
  if changeRate < 0.1:   windowCycles = min(windowCycles * 2, 10000)
```

**参数**：初始值2500，范围[1000, 10000]。

**理由**：Window sweep（§3.4）显示不同workload需要的window差异巨大。自适应机制消除了手动选择——tc自然缩小到1000，branch_entropy增大到7500+。

### 4.4 统一配置

所有workload——Micro和GAPBS——使用**完全相同的参数**。没有per-workload调优。

| 参数 | 值 |
|------|-----|
| Conservative FetchWidth | 5 |
| Conservative InflightCap | 48 |
| Conservative IQCap | 24 |
| Conservative LSQCap | 24 |
| Deep FetchWidth | 3 |
| Deep SquashThres | 0.25 |
| Resource Congestion InflightCap | 56 |
| Resource Congestion IQCap | 26 |
| Resource Congestion LSQCap | 28 |
| Resource Congestion CommitThres | 0.95 |
| Resource Congestion IPC Guard | 2.0 |
| Adaptive Window | 启用（初始=2500，范围=[1000, 10000]） |
| mem_block_ratio阈值 | 0.12 |

---

## 5. 迭代过程（8轮）

| Round | 改动 | 结果 | 关键教训 |
|-------|------|------|---------|
| R1 | Ser→Light, Ctrl→Deep | Overall WPE -0.39% | Deep Conservative对GAPBS的Control窗口太强 |
| R2 | 所有throttle统一用sweet spot | WPE +1.34% | 首次超过V2 |
| R3 | GAPBS专用fw=4/win=2500 | WPE +1.91% | fw是GAPBS的主导参数 |
| R4 | 试fw=5和fw=4 + iq/lsq caps | 更差 | iq/lsq caps对GAPBS无效（IPC太低，无IQ拥塞） |
| R5 | 调Control阈值 | 无变化 | GAPBS不走Control分支（所有mem_block>=0.12） |
| R6 | Serialized-Deep子级（squash>=0.30） | WPE +2.14% | squash_ratio有效区分窗口 |
| R7 | Normal层fw=6（从5提到6） | WPE +2.21% | 73-92%的IPC损失来自normal层窗口 |
| R8 | Resource拥塞检测 | WPE +2.73% | sweet spot对高IPC workload自动生效 |
| +统一 | Micro和GAPBS相同参数 | **EDP +13.36%** | 在当前阈值下IQ/LSQ caps对GAPBS安全 |

---

## 6. 最终结果

### 6.1 单核结果（12个workload，每个50M指令）

**Microbenchmarks**：

| Workload | BL IPC | V4 IPC | dIPC | BL Energy | V4 Energy | dEnergy | **V4 EDP** |
|----------|--------|--------|------|-----------|-----------|---------|-----------|
| balanced_pipeline_stress | 2.908 | 3.024 | +4.0% | 3.313J | 2.902J | -12.4% | **+15.8%** |
| phase_scan_mix | 0.467 | 0.464 | -0.7% | 6.005J | 4.318J | -28.1% | **+27.7%** |
| **branch_entropy** | 0.909 | 0.987 | **+8.5%** | 6.087J | 3.990J | **-34.5%** | **+39.6%** |
| serialized_pointer_chase | 0.827 | 0.805 | -2.7% | 4.323J | 3.990J | -7.7% | +5.2% |
| compute_queue_pressure | 2.392 | 2.392 | +0.0% | 2.686J | 2.686J | +0.0% | 0.0% |
| stream_cluster_reduce | 0.514 | 0.514 | +0.0% | 3.456J | 3.457J | +0.0% | 0.0% |
| **Micro平均** | | | | | | | **+14.70%** |

**GAPBS**（g20图规模，50M指令）：

| Benchmark | BL IPC | V4 IPC | dIPC | BL Energy | V4 Energy | dEnergy | **V4 EDP** |
|-----------|--------|--------|------|-----------|-----------|---------|-----------|
| bfs | 1.410 | 1.343 | -4.7% | 4.189J | 3.542J | -15.4% | +11.3% |
| bc | 1.397 | 1.334 | -4.5% | 4.219J | 3.590J | -14.9% | +10.9% |
| pr | 1.406 | 1.344 | -4.4% | 4.208J | 3.664J | -12.9% | +8.9% |
| cc | 1.411 | 1.345 | -4.6% | 3.936J | 3.639J | -7.6% | +3.1% |
| sssp | 1.391 | 1.342 | -3.6% | 4.009J | 3.581J | -10.7% | +7.4% |
| **tc** | 1.346 | 1.376 | **+2.3%** | 5.461J | 3.871J | **-29.1%** | **+30.7%** |
| **GAPBS平均** | | | | | | | **+12.03%** |

**Overall EDP: +13.36%**，覆盖所有12个workload。

**已保存的图和数据**：
- **汇总柱状图**：[results/charts/baseline_vs_adaptive_bars.png](../results/charts/baseline_vs_adaptive_bars.png) — baseline vs V4 并列比较（所有workload）。
- **Pareto图**：[results/charts/pareto_perf_vs_energy.png](../results/charts/pareto_perf_vs_energy.png)、[results/charts/all_v2_pareto.png](../results/charts/all_v2_pareto.png) — 性能 vs 能耗散点图。
- **汇总CSV**（12 workload × baseline/V4 全部指标）：[results/all_experiments.csv](../results/all_experiments.csv)。
- **单次运行产物**（每个 `<workload>_<baseline|v4>/latest/` 下的 config.json, stats.txt, mcpat.out, adaptive_window_log.csv）：[runs/v4_presentation/](../runs/v4_presentation/)。

### 6.2 多核结果（4核，同workload跑在所有核上）

6个Micro workload，每个在4核上跑4个副本，私有L1 + 共享L2。

| Workload | 4核 dIPC | 4核 dEnergy | **4核 EDP** | 单核 EDP |
|----------|---------|------------|-----------|---------|
| balanced_pipeline_stress | +4.3% | -12.5% | **+16.1%** | +15.8% |
| phase_scan_mix | -2.6% | -21.7% | **+20.6%** | +27.7% |
| branch_entropy | +0.2% | -0.7% | +1.0% | +39.6% |
| serialized_pointer_chase | -2.2% | -7.2% | +5.1% | +5.2% |
| compute_queue_pressure | 0% | 0% | 0% | 0% |
| stream_cluster_reduce | 0% | 0% | 0% | 0% |
| **Micro 4核平均** | | | **+7.1%** | +14.5% |

**观察**：
- balanced_pipeline_stress在4核下反而更好（+16.1% vs +15.8%）—— Resource拥塞检测在per-core上正常工作
- branch_entropy在4核下大幅下降（+1.0% vs +39.6%）—— 共享L2竞争改变了它的pipeline行为
- 单核不受益的workload在多核下也不受损
- **GAPBS在gem5 SE mode多核下无法运行**——因为未实现`statx` syscall——这是gem5的限制，不是我们机制的问题

**已保存的数据**：每核的逐窗口自适应日志在 [runs/v4_presentation/multicore/v4_4core/latest/](../runs/v4_presentation/multicore/v4_4core/latest/) 下：
- [adaptive_window_log.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log.csv)（CPU0）、[adaptive_window_log_cpu1.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log_cpu1.csv)、[adaptive_window_log_cpu2.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log_cpu2.csv)、[adaptive_window_log_cpu3.csv](../runs/v4_presentation/multicore/v4_4core/latest/adaptive_window_log_cpu3.csv) — 每个核的原始逐窗口信号trace。

### 6.3 最佳案例vs最差案例分析

#### 最佳案例：`adaptive_showcase_best`（自己构造的workload）

**构造方法**：我们专门设计了这个workload，目的是同时展现V4最适合处理的两种行为——高mem_block_ratio 和 高squash_ratio。

**Workload结构**：
```c
// 1. 建一条随机化的链表（2048个节点，指针数组 chase[]）
//    chase[i] = 0..CHASE_SIZE-1 的随机置换
//
// 2. 主循环：每次迭代交替执行两个"子操作"：
//
//    (a) 通过链表做间接load：
//        chase_idx = chase[chase_idx];     // 每次都 cache miss
//        val = arr_a[chase_idx & (ARRAY_SIZE-1)];
//
//    (b) 基于load回来的val做数据依赖的嵌套分支：
//        if (val & 0x80)  { acc += ...; if (val & 0x40) {...} else {...} }
//        else             { acc ^= ...; if (val & 0x20) {...} else {...} }
//        if ((val>>8) & 0x03) acc += ...; else acc ^= ...;
```

**每个特征的设计意图**：
| 特征 | 触发什么 | 为什么对V4有利 |
|------|---------|---------------|
| 随机化链表（`chase[chase_idx]`） | 高mem_block_ratio（0.515） | 每次load都是cache miss，预取器无法预测。Commit等内存 → 分类器识别为Serialized |
| 基于loaded val的数据依赖分支 | 高squash_ratio（0.317） | 分支方向依赖还没返回的值，预测器约50%错 → 投机路径白跑 |
| 嵌套分支（3层） | 放大投机浪费 | 每多一层，浪费的投机深度翻倍 |
| 小工作集（2048节点 × 4B = 8KB） | 聚焦于内存延迟 | 表本身能放进L1，但由于随机化pointer-chase还是会miss |

**逐窗口行为**：7331个窗口中99%分类为Serialized → Deep Conservative（fw=3）。平均 mem_block_ratio = 0.515（超过一半的周期commit被memory阻塞），平均 squash_ratio = 0.317（1/3 取指指令被浪费）。

**结果**：

| 指标 | Baseline | V4 | 变化 |
|------|---------|-----|------|
| IPC | 0.562 | 0.606 | **+7.9%** |
| Power | 150.8W | 92.1W | **-38.9%** |
| Energy | 6.337J | 3.724J | **-41.2%** |
| **EDP** | 0.250 | 0.136 | **+45.6%** |

注意：IPC居然**提高**了，因为baseline的8-wide fetch不停把投机指令往错误路径塞，堵住IQ/LSQ/ROB。fw=3消除了大部分这种浪费，真正有效的指令反而能更快拿到流水线资源。

#### 最差案例：`adaptive_showcase_worst`（自己构造的"轻微负面"workload）

**构造方法**：我们专门设计了这个workload，目的是让V4 **确实触发了 throttle**，但这个throttle 完全没有可以"回收"的浪费——这是V4最糟糕的情况。

**Workload结构**：
```c
#define CHASE_SIZE (1U << 16)   // 64K节点 × 4B = 256KB，miss L1但L2能装下
static uint32_t chase[CHASE_SIZE];  // 随机置换，构成一个大循环

for (r = 0; r < rounds; ++r) {
    // (a) 串行pointer chase —— 下一个idx取决于刚load回来的值。
    //     CPU无法提前预取：任何时刻LSQ里只有 ~1-2 条chase load。
    idx = chase[idx];
    uint32_t v = idx;

    // (b) 28条无分支、完全依赖的compute链。
    //     每步依赖上一步 -> 无ILP、无squash。
    //     用compute把IQ占住，所以LSQ始终很空。
    v ^= v >> 16; v *= 0x7feb352dU;
    v ^= v >> 15; v *= 0x846ca68bU;
    v ^= v >> 16; v *= 0xcaffe171U;
    // ... 接下来11步类似 ...
    v ^= v >> 13;
    acc ^= v;
}
```

**每个特征的设计意图**：
| 特征 | 触发什么 | 为什么让V4受损（有throttle但没收益） |
|------|---------|-------------------------------------|
| 256KB chase数组（L1 miss，L2 hit） | commit_blocked_mem > 0 | ROB头等L2返回 -> 解耦后的`mem_block_ratio`保持在0.12阈值以上 -> 分类器选`Serialized-memory dominated` |
| chase load之间串行依赖 | LSQ平均占用 ~ 8.7 | 低于 12 的`outstandingMissThres` -> 不会被归为`High-MLP` -> Conservative throttle（fw=5）真正生效 |
| 28条依赖compute链 | IQ被compute填满、不是被load填满 | 同时保证LSQ占用低 *并且* 给V4足够的fetch带宽可以砍——但没有任何投机浪费可以消除 |
| 无分支 | squash_ratio ≈ 0.006 | 低于所有子级阈值 -> 分类器停在普通`Conservative`（fw=5），不会进Deep（fw=3） |

**逐窗口行为**（4394个窗口，自适应window size）：
| 信号 | 数值 | 解读 |
|------|------|------|
| 分类为`Serialized-memory dominated` | **99.0%**（4351/4394） | 几乎每个窗口都触发throttle |
| 实际mode = `Conservative` | **99.0%** | fw=5 throttle一直开着 |
| avg_outstanding_misses_proxy | **8.74** | 低于12的阈值，否则会切换到HighMLP |
| squash_ratio | 0.006 | 几乎没有投机浪费可以回收 |
| mem_block_ratio（解耦值） | ≈ 0.19 | Aggressive探测窗口期间保持在0.12之上 |
| avg IQ占用 | 23.0 | IQ使用健康 —— 是compute chain而不是memory-bound |
| V4逐窗口平均IPC | 1.18 | 依然挺高 —— workload本身效率就高 |

**为什么V4在这里受损**：

1. **没有投机浪费可回收**。squash_ratio ≈ 0.006 意味着99.4%取指的指令都会retire。fw=5只是限制了*有效*的取指。
2. **较高的baseline IPC（1.233）**意味着任何fetch width削减都会直接变成吞吐损失。Baseline的8-wide fetch对这个workload的ILP+compute chain profile本来就刚刚好。
3. **Energy节省极小**，因为前端本来就没有被过度投机 —— 没有可以省的speculative power。动态能耗只降了0.3%。
4. **分类器并没有*错***：mem_block_ratio确实超过0.12，LSQ确实低于12。决策规则按设计精确地应用。这就是"模式匹配启发式"不可避免的代价。

**结果**：

| 指标 | Baseline | V4 | 变化 |
|------|---------|-----|------|
| IPC | 1.233 | 1.166 | **-5.5%** |
| Power | 121.40 W | 114.38 W | -5.8% |
| Energy | 2.516 J | 2.508 J | -0.3% |
| 仿真时间 | 0.02073 s | 0.02192 s | +5.8% |
| **EDP (E×T)** | 0.0522 J·s | 0.0550 J·s | **-5.4%** |

这是V4**真实世界里最差的结果**：当分类器在一个没有任何"浪费"可以消除的workload上触发时，会吃到干净的 -5.4% EDP 损失。（参考：我们统一benchmark集合里最差的*真实*benchmark是 GAPBS-cc，仍然有 +3.3% EDP。这个自己构造的案例因此比标准集合里任何workload都更差，专门用来展示V4的failure mode。）

#### 总结对比

| 信号 | 最佳案例 | 最差案例 | 解读 |
|------|---------|---------|------|
| squash_ratio | **0.317** | 0.006 | 最佳案例有50倍以上投机浪费可以消除 |
| mem_block_ratio | **0.515** | ~0.19（解耦） | 最佳案例memory占主导；最差案例只是刚过阈值 |
| baseline IPC | 0.562 | **1.233** | 最差案例IPC高2.2倍（可损失的吞吐更多） |
| 实际throttle | Deep Conservative (fw=3) 99% | Conservative (fw=5) 99% | 两种class都把窗口送进throttled路径 |
| **EDP变化** | **+45.6%** | **-5.4%** | 约50点的摆幅 —— 机制是明显bimodal的 |

**已保存的逐窗口trace和单次运行产物**（在 [runs/v4_presentation/showcase/](../runs/v4_presentation/showcase/) 下）：
- 最佳案例V4：[adaptive_showcase_best_v4/latest/adaptive_window_log.csv](../runs/v4_presentation/showcase/adaptive_showcase_best_v4/latest/adaptive_window_log.csv) — 全部7331个窗口的class、mode、squash_ratio、mem_block_ratio、IPC。
- 最差案例V4：[adaptive_showcase_worst_v4/latest/adaptive_window_log.csv](../runs/v4_presentation/showcase/adaptive_showcase_worst_v4/latest/adaptive_window_log.csv) — 新"轻微负面"设计的全部4394个窗口。
- 最差案例Baseline：[adaptive_showcase_worst_baseline/latest/](../runs/v4_presentation/showcase/adaptive_showcase_worst_baseline/latest/) — 同一workload的baseline stats。
- 每次V4运行还包含 `config.json`、`stats.txt`、`mcpat.xml`、`mcpat.out`，用于查看完整的功耗分解。
- Workload源码：[workloads/adaptive_showcase_worst/adaptive_showcase_worst.c](../workloads/adaptive_showcase_worst/adaptive_showcase_worst.c)。

*说明*：V4 showcase的运行没有预先渲染成PNG——数据以CSV形式保存，可用任意绘图工具重新生成。§3.3 里提到的v2时代逐窗口时间线PNG在较早的workload上演示了相同的思路。

### 设计的擅长和不擅长

**V4擅长处理的workload特征**：
- 高squash_ratio（>0.25）—— 大量投机浪费
- 高mem_block_ratio（>0.12）—— memory stall是真正瓶颈
- 数据依赖分支 —— 投机路径几乎都错
- 低baseline IPC（<1.0）—— throttle不伤有效吞吐

*典型例子*：指针追踪、哈希表查找、树遍历、规则匹配。

**V4不擅长处理的workload特征**：
- 低squash_ratio（<0.15）—— 投机大多正确
- 较高baseline IPC（>1.0）—— throttle直接限制吞吐
- 可预测的分支模式 —— 限制投机没有收益
- 低mem_block_ratio —— memory不是瓶颈

*典型例子*：图遍历（访问模式部分可预测）、streaming计算（顺序内存，预取器友好）。

**一句话总结**：V4的核心能力是识别并减少**无效投机**——当流水线将精力浪费在注定被squash的指令上时，限制投机既省能耗又（往往）提升性能。当投机大多有效时，限制投机就是纯粹的性能损失。

---

## 7. 关键经验与放弃的方向

### 放弃的方向

| 方向 | 放弃原因 |
|------|---------|
| EMA信号平滑（α=0.3） | 效果<0.2%，概念上错误——当前stall应该用当前信号 |
| 信号去耦合（Conservative模式下冻结信号） | 根本缺陷——一旦进Conservative信号就冻结，无法感知phase变化 |
| Squash比例化throttle（fw连续映射） | EDP比binary阈值差（tc从+28.2%降到+18.6%） |
| 降低mem_block_ratio到0.10 | 影响可忽略 |
| Aggressive模式fw=7（常开轻度throttle） | 对EDP影响可忽略 |
| 3级Conservative（Light+Normal+Deep） | Light和Normal参数最终一致——简化为2层+Deep子级 |
| Rename Width throttle | 全有或全无阈值效应（rw=4~7完全一样，rw=8突变）——没用 |

### 学到的核心设计原则

1. **不要在信号层面解决分类漂移**——在参数层面修复（避免会扭曲信号的参数）。
2. **Sweet spot参数是workload-IPC依赖的**——IQ/LSQ caps帮助高IPC workload，对低IPC workload无效。用IPC-guard的自动检测（Resource拥塞子级）。
3. **Fetch Width是低IPC workload的主导throttle参数**。IQ/LSQ caps几乎不影响它们。
4. **当决策边界清晰时，binary阈值优于连续映射**（squash_ratio是双峰分布）。
5. **自适应window size消除了手动per-workload调优**——机制自然适应phase变化频率。

### 代码改动汇总

| 文件 | 改动内容 |
|------|---------|
| `src/cpu/o3/BaseO3CPU.py` | 新增参数：SerializedTight, ResourceCongestion, AdaptiveWindow |
| `src/cpu/o3/cpu.hh` | 新增成员变量（子级flag、自适应window状态） |
| `src/cpu/o3/cpu.cc` | Deep子级逻辑、Resource拥塞逻辑、自适应window逻辑、模式映射简化 |

---

## 8. Overhead分析

我们的机制在三处增加了逻辑：每周期信号采样、窗口边界分类、throttle应用。相对于O3 core，总开销可忽略。

### 硬件开销

**存储（片上寄存器/SRAM）**：

| 组件 | 大小 | 说明 |
|------|------|------|
| 窗口统计计数器（11个64位） | 88 B | cycles、fetched/committed/squashed insts、mem_block_cycles、iq_sat_cycles、branch_recovery_cycles、inflight/iq/outstanding_miss samples、branch_mispredicts |
| 配置寄存器（~30个32位） | 120 B | 阈值、各模式参数、自适应window参数 |
| 运行时状态寄存器 | 16 B | 当前模式、当前类别、windows_in_mode、adaptive_window_cycles、子级flag |
| **总存储** | **~224 B** | 典型L1 cache的<0.01% |

**逻辑**：

| 组件 | 门数估算 | 对关键路径的影响 |
|------|---------|----------------|
| 11个每周期计数器自增 | ~500门 | 与pipeline并行；不增加新关键路径 |
| Fetch width控制的3个mux/比较器 | ~50门 | 在已有的fetch gating逻辑上 |
| Inflight/IQ/LSQ cap的3个比较器 | ~100门 | 在已有的throttle-fetch路径上 |
| 窗口边界分类器（7个阈值、4个类、子级检查） | ~1000门 | 每~2500周期触发一次——不在关键路径上 |
| 自适应window调整器 | ~50门 | 每8个窗口触发一次 |
| **总逻辑** | **~1700门** | << 典型~10M门O3 core的0.1% |

**功耗与面积**：
- 每周期采样计数器很小（1GHz下<1mW）
- 窗口边界分类器每2500周期运行一次——摊销功耗约为0
- 不改变pipeline关键路径 → 不影响频率/电压
- 面积估算：**< O3 core面积的0.1%**

**延迟**：
- 每周期采样：零增加延迟（并行计数器）
- 窗口边界分类：~5-10周期的逻辑，但在窗口结束时运行，不在关键路径。参数更新在下一个窗口生效
- 模式切换：即时（只更新参数mux选择）

### 软件开销

**零软件开销**。机制对应用程序、OS、ISA完全透明：

| 层级 | 开销 |
|------|------|
| 应用程序 | 无——无代码修改，无API，无系统调用 |
| 操作系统 | 无——无驱动，无中断，无内核参与 |
| ISA | 无新指令 |
| 编译器 | 无修改 |
| 固件/微码 | 无——所有逻辑在硬件计数器和状态机中 |

**配置方式**：阈值和模式参数可以选择通过MSR暴露给BIOS/固件做调优。在gem5中通过`--param`设置。实际产品会ship固定的最优值（fw=5/3, squash=0.25, window=[1000, 10000]）。

### 成本 vs 收益

| 方面 | 开销 |
|------|------|
| Core面积 | +0.1% |
| L1/L2缓存容量 | 不变 |
| 流水线关键路径 | 不变 |
| 峰值频率 | 不变 |
| 每周期功耗 | +<1mW |
| 软件复杂度 | 零 |
| **favorable workload能耗节省** | **10%~35%** |
| **12个benchmark平均EDP改善** | **+13.36%** |

实现成本微不足道（<0.1%面积，零软件影响），任何追求能效的O3设计都应该加上类似机制——几乎是"免费"的改进。

---

## 最终数据一览

| 指标 | 值 |
|------|-----|
| **Overall EDP改善** | **+13.36%** |
| Micro EDP（6个workload） | +14.70% |
| GAPBS EDP（6个workload） | +12.03% |
| 4核 Micro EDP平均 | +7.1% |
| 单workload最佳EDP | +39.6%（branch_entropy） |
| Showcase最佳案例EDP | +45.6% |
| 真实benchmark里最差EDP（GAPBS-cc） | +3.3% |
| Showcase最差案例EDP（`adaptive_showcase_worst`） | **-5.4%** |
