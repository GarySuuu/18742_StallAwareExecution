# Parameter Sweep 深度分析报告

> Workload: `balanced_pipeline_stress` (50M instructions, baseline IPC=2.908)
> 方法: 强制100% conservative模式 (`adaptiveMemBlockRatioThres=0.0`, `adaptiveOutstandingMissThres=9999`)
> 遮蔽处理: sweep单个参数时，所有上游遮蔽参数设为0(禁用)

---

## 1. Fetch Width (fw=1/2/4/8, inflight cap禁用)

| Config | IPC | dIPC | fetch_mean | fetch_0% | fetch_8% | IQFull | dec_blk% | ren_blk% |
|--------|-----|------|-----------|---------|---------|--------|---------|---------|
| fw1 | 0.900 | **-69.0%** | 0.92 | 8.1% | 0.0% | 0 | 0.0% | 0.0% |
| fw2 | 1.569 | **-46.1%** | 1.62 | 14.3% | 0.0% | 0 | 0.0% | 0.0% |
| fw4 | 2.507 | **-13.8%** | 2.68 | 23.9% | 0.0% | 0 | 0.4% | 0.3% |
| fw8 | 2.908 | baseline | 3.89 | 33.6% | 38.6% | 2.75M | 32.1% | 9.8% |

### 信号解读

**fetch.nisnDist（每周期取指数分布）**：
- fw=1时，平均每周期只取0.92条指令，前端成为绝对瓶颈
- fw=2时，平均1.62条——fetch width直接成为IPC的上限
- fw=4时，平均2.68条，IPC恢复到2.507（baseline的86%）
- fw=8时，38.6%的周期满取8条——但平均只有3.89，说明33.6%的周期取0条（被后端反压阻塞）

**IQFullEvents**：
- fw=1/2/4时IQFull=0——前端太窄，指令根本填不满IQ
- fw=8时IQFull=2.75M——前端足够快，后端IQ成为瓶颈

**decode_blockedCycles / rename_blockCycles**：
- fw=1/2/4时 dec_blk≈0%——前端太慢，decode/rename从不被后端阻塞（因为根本没足够指令送过去）
- fw=8时 dec_blk=32.1%——后端反压导致decode 1/3时间被阻塞

### 结论

> **Fetch Width是一个极其有效的调节杠杆**。从fw=8降到fw=4就能降低13.8%的IPC，且这种降低是干净的前端限制（不触发任何后端阻塞）。
> 
> **关键发现**：fw=4是一个"甜点"——IPC损失可控（-13.8%），同时完全消除了IQ/LQ/SQ的后端full events（因为前端送入速度降低了）。这意味着fw=4可以在不改变任何后端参数的情况下，大幅降低整个后端的活动度和功耗。
> 
> **之前Task 3中fw=2对fetch_bandwidth_stress无效的原因现在很清楚了**：那个workload的baseline IPC只有1.05，远低于fw=2的上限，所以fw=2不构成瓶颈。而balanced_pipeline_stress的IPC=2.91，fw=2直接截断了吞吐量。

---

## 2. IQ Cap (iqcap=16/24/32/48/0, inflight cap禁用)

| Config | IPC | dIPC | issue_mean | IQFull | ren_blk% | forwLoads |
|--------|-----|------|-----------|--------|---------|-----------|
| iqcap16 | 2.651 | **-8.9%** | 2.734 | 0 | 1.0% | 1.58M |
| iqcap24 | **3.055** | **+5.1%** | 3.167 | 0 | 1.6% | 1.92M |
| iqcap32 | 3.014 | +3.6% | 3.181 | 0 | 3.6% | 2.27M |
| iqcap48 | 2.897 | -0.4% | 3.115 | 315K | 6.8% | 2.65M |
| iqcap0 | 2.908 | baseline | 3.118 | 2.75M | 9.8% | 2.68M |

### 信号解读

**IQFullEvents**：
- iqcap=16/24/32时IQFull=0——IQ从不满（cap低于实际需求，指令进出平衡）
- iqcap=48时IQFull=315K——开始偶尔触发IQ满
- iqcap=0（禁用/baseline IQ=64）时IQFull=2.75M——大量IQ满阻塞

**反直觉发现：iqcap=24的IPC比baseline还高5.1%！**

这是因为：当IQ cap限制为24时，IQ不会过度填满，rename/dispatch的阻塞从9.8%降到1.6%。减少的IQ压力让decode和rename流水线更通畅，反而提高了指令的有效吞吐。

**forwLoads（store-to-load forwarding）**：
- iqcap=16时forwarding仅1.58M（vs baseline 2.68M）——IQ中同时存在的load/store变少，forwarding机会减少
- iqcap=24时恢复到1.92M——说明IQ够大让足够多的load/store共存

### 结论

> **IQ Cap是一个有效但非线性的杠杆**。存在一个最优IQ cap（≈24），比完全禁用（baseline IQ=64）和过度限制（16）都好。
> 
> **机制**：较小的IQ cap减少了rename阻塞（因为IQ不会满到需要stall rename），同时保持足够的指令窗口来发现ILP。这是一个"减少过度投机"带来的净正效果。
> 
> **对adaptive设计的启示**：IQ cap不应该设为0（禁用），也不应该设得太低。24-32的范围是这个workload上的最优区间。当前V2默认IQ cap=0（禁用）是次优的。

---

## 3. LSQ Cap (lsqcap=8/12/16/24/0, inflight cap禁用)

| Config | IPC | dIPC | LQFull | SQFull | forwLoads | memOrdViol |
|--------|-----|------|--------|--------|-----------|-----------|
| lsqcap8 | 1.974 | **-32.1%** | 0 | 0 | 388K | 150 |
| lsqcap12 | 2.487 | **-14.5%** | 0 | 0 | 1.27M | 188 |
| lsqcap16 | 2.600 | **-10.6%** | 0 | 0 | 1.31M | 215 |
| lsqcap24 | 2.950 | +1.4% | 0 | 0 | 1.71M | 366 |
| lsqcap0 | 2.908 | baseline | 266K | 22K | 2.68M | 9,457 |

### 信号解读

**LQFullEvents / SQFullEvents**：
- 有趣：lsqcap=8到24时LQFull和SQFull都是0——因为LSQ cap通过`adaptiveShouldThrottleFetch()`暂停取指来限制，不是等LSQ满了才阻塞
- baseline（无cap）时LQFull=266K，SQFull=22K——正常后端反压

**forwLoads（store-to-load forwarding）**：
- lsqcap=8时仅388K forwarding（vs baseline 2.68M），**减少了85%**
- 这意味着LSQ cap不仅限制了吞吐量，还大幅减少了store-to-load forwarding的机会——LSQ中同时存在的load/store太少

**memOrderViolation**：
- lsqcap=8时仅150（vs baseline 9,457），减少98%
- 更少的inflight memory操作 = 更少的内存顺序违规

**lsqcap=24的IPC略微超过baseline（+1.4%）**：与IQ cap类似，适度限制LSQ反而减少了投机浪费。

### 结论

> **LSQ Cap是最有效的后端限制参数**（Task 3已证明），因为它创建了硬性取指暂停壁垒。
> 
> **关键信号**：forwLoads是LSQ cap最灵敏的观测信号——cap降低直接导致forwarding机会骤减。
> 
> **lsqcap=24是甜点**：IPC略微提高（+1.4%），同时减少了97%的memOrderViolation。这说明baseline的32-entry LSQ实际上允许了过多的投机内存操作。

---

## 4. Inflight Cap / ROB (robcap=32/48/64/96/128/0, fetch width禁用)

| Config | IPC | dIPC | ROBFull | IQFull | ren_blk% | dec_blk% | rob_writes |
|--------|-----|------|---------|--------|---------|---------|-----------|
| robcap32 | 2.662 | **-8.4%** | 0 | 0 | 0.7% | 0.8% | 103.7M |
| robcap48 | 2.887 | -0.7% | 0 | 0 | 2.0% | 2.1% | 106.5M |
| robcap64 | **3.028** | **+4.1%** | 0 | 0 | 2.5% | 2.6% | 107.5M |
| robcap96 | 2.959 | +1.8% | 0 | 226K | 5.8% | 7.6% | 117.1M |
| robcap128 | 2.896 | -0.4% | 0 | 2.81M | 9.9% | 32.7% | 122.4M |
| robcap0 | 2.908 | baseline | 0 | 2.75M | 9.8% | 32.1% | 122.3M |

### 信号解读

**ROBFullEvents始终为0**：ROB满事件从未触发——说明在这个workload上，ROB的192 entries从未完全填满。inflight cap的作用不是通过"ROB满"来限制，而是通过`adaptiveShouldThrottleFetch()`中的inflight count检查来暂停取指。

**IQFullEvents**：
- robcap=32/48/64时IQFull=0——inflight cap限制了总的inflight指令数，间接防止了IQ过满
- robcap=96时IQFull=226K——inflight cap开始放松，IQ偶尔满
- robcap=128/0时IQFull=2.75M+——inflight cap不再有效限制，IQ频繁满

**这证实了遮蔽关系：Inflight Cap → IQ Cap**

**robcap=64的IPC比baseline高4.1%**：与IQ cap类似的机制——适度限制inflight指令数减少了后端拥塞（ren_blk从9.8%降到2.5%），反而提高了有效吞吐。

**rob_writes**：
- robcap=32时103.7M（vs baseline 122.3M），减少15%——更少的指令进入ROB
- 对功耗有直接影响：ROB读写是动态功耗的重要组成部分

### 结论

> **Inflight Cap是最高层的遮蔽参数，能间接控制IQ、LSQ、rename所有后端压力**。
> 
> **robcap=64是最优点（+4.1% IPC）**——比baseline的192/无限制更好。这是一个重要发现：当前V2的inflight cap=96实际上还偏高。
> 
> **rob_writes是一个好的功耗代理信号**：rob_writes减少直接意味着更少的ROB动态功耗。

---

## 5. Rename Width (rw=1/2/4/8, fetch+inflight禁用)

| Config | IPC | dIPC | ren_run% | ren_blk% | ren_idle% | dec_blk% |
|--------|-----|------|---------|---------|----------|---------|
| rw1 | 0.894 | **-69.3%** | 46.8% | 0.0% | 53.2% | 93.3% |
| rw2 | 1.602 | **-44.9%** | 46.8% | 0.0% | 53.1% | 86.4% |
| rw4 | 2.615 | **-10.1%** | 47.4% | 1.1% | 51.5% | 72.9% |
| rw8 | 2.908 | baseline | 60.3% | 9.8% | 30.0% | 32.1% |

### 信号解读

**rename周期分布**：
- rw=1/2时：rename运行47%的时间，空闲53%——这里的"空闲"是因为rename每周期只能处理1-2条指令，但每次处理完就空闲等下一批。rename从不阻塞（blk=0%）因为后端永远跟得上
- rw=4时：与rw=1/2类似，但开始出现1.1%的阻塞
- rw=8时：rename运行60%，阻塞9.8%——后端反压开始显著

**decode_blockedCycles**：
- rw=1时 dec_blk=93.3%——decode几乎一直被rename阻塞，因为rename吞吐太低
- rw=8时 dec_blk=32.1%——恢复到正常的后端反压水平

**renamedInsts基本恒定（~50-62M）**：说明总提交指令数（50M）不变，但处理的总指令数（含squash）随rename width增大而增加——更宽的rename允许更多投机指令进入pipeline。

### 结论

> **Rename Width是一个有效杠杆（-69%到-10%的IPC影响范围）**，但它的效果模式与Fetch Width几乎一致——因为在gem5 O3 CPU中，rename width限制了指令从decode到IQ的吞吐，效果等价于一个"中间位置的fetch width"。
> 
> **之前Task 3中rw=2对rename_dispatch_stress无效的原因**：那个workload IPC=1.68，数据依赖限制了实际ILP，rw=2不构成瓶颈。当前workload IPC=2.91，rw=2直接截断了指令流。

---

## 6. Dispatch Width (dw=1/2/4/8, fetch+inflight禁用)

| Config | IPC | dIPC | issue_mean | commit_mean | dec_blk% | ren_blk% |
|--------|-----|------|-----------|------------|---------|---------|
| dw1 | 0.859 | **-70.5%** | 0.864 | 0.863 | 91.1% | 86.5% |
| dw2 | 1.491 | **-48.7%** | 1.518 | 1.505 | 83.3% | 75.2% |
| dw4 | 2.923 | **+0.5%** | 3.141 | 3.100 | 54.1% | 49.4% |
| dw8 | 2.908 | baseline | 3.118 | 3.169 | 32.1% | 9.8% |

### 信号解读

**issue_mean和commit_mean几乎等于dispatch width限制**：
- dw=1时issue_mean=0.864（≈1）——dispatch每周期只送1条到执行单元
- dw=2时issue_mean=1.518（≈1.5）——略低于理论上限2，因为偶尔有数据依赖stall

**dw=4的IPC略微超过baseline（+0.5%）**：与ROB cap=64、IQ cap=24类似的现象——dw=4减少了rename/dispatch的阻塞。baseline的dw=8让太多指令涌入后端，造成IQ满和rename阻塞，而dw=4刚好平衡了前后端吞吐。

**rename_blockCycles**：
- dw=1时ren_blk=86.5%——dispatch太窄，rename频繁被阻塞
- dw=4时ren_blk=49.4%——中等阻塞，但IPC反而略好
- dw=8时ren_blk=9.8%——最少阻塞（后端阻塞主要来自IQ满）

### 结论

> **Dispatch Width和Rename Width效果类似但略有不同**：
> - dw=4完全恢复baseline性能（+0.5%），而rw=4还有-10.1%的损失
> - 这说明dispatch width的"有效范围"更宽——dw=4已经足够维持baseline吞吐
> - 从4降到2才开始显著损失性能
>
> **设计启示**：如果要用dispatch width作为throttle手段，dw=4基本无损，dw=2是一个中等强度的限制点。

---

## 7. Combined Fetch Width + Inflight Cap

| Config | IPC | dIPC |
|--------|-----|------|
| fw2_cap64 | 1.569 | -46.1% |
| fw2_cap96 | 1.569 | -46.1% |
| fw2_cap128 | 1.569 | -46.1% |
| fw4_cap64 | 2.507 | -13.8% |
| fw4_cap96 | 2.507 | -13.8% |
| fw4_cap128 | 2.507 | -13.8% |

### 结论

> **当fetch width已经限制了前端吞吐时，inflight cap完全没有额外效果**。
> - fw=2时，IPC被限制在1.57，无论inflight cap是64/96/128都不变
> - fw=4时，IPC被限制在2.51，inflight cap同样无差异
> 
> **这完美验证了遮蔽关系**：Fetch Width遮蔽了Inflight Cap。当前端吞吐已被fetch width限制时，后端永远不会达到inflight cap的上限。
>
> **V2设计的启示**：V2同时使用fw=2和cap=96，但实际上cap=96完全被fw=2遮蔽了——只有fw=2在起作用。如果要让cap有独立贡献，需要提高fw（如fw=4或fw=8）。

---

## 综合结论

### 1. 参数有效性排名

| 排名 | 参数 | IPC影响范围 | 是否有效 | 最优点 |
|------|------|-----------|---------|--------|
| 1 | **Dispatch Width** | -70.5% ~ +0.5% | **极有效** | dw=4（无损） |
| 2 | **Fetch Width** | -69.0% ~ baseline | **极有效** | fw=4（-13.8%） |
| 3 | **Rename Width** | -69.3% ~ baseline | **极有效** | rw=4（-10.1%） |
| 4 | **LSQ Cap** | -32.1% ~ +1.4% | **有效** | lsqcap=24（+1.4%） |
| 5 | **IQ Cap** | -8.9% ~ +5.1% | **有效且存在最优点** | iqcap=24（+5.1%） |
| 6 | **Inflight Cap (ROB)** | -8.4% ~ +4.1% | **有效且存在最优点** | robcap=64（+4.1%） |

### 2. 遮蔽关系验证

| 遮蔽关系 | 验证结果 |
|---------|---------|
| Fetch Width → Inflight Cap | **完全确认**：fw=2/4时，inflight cap=64/96/128完全无差异 |
| Inflight Cap → IQ Cap | **完全确认**：robcap=32/48/64时IQFull=0（被inflight cap限制住了） |
| Inflight Cap → LSQ Cap（间接） | **部分确认**：inflight cap限制了总inflight数，间接限制了LSQ中的操作数 |

### 3. 对Adaptive V2设计的关键发现

1. **V2的fw=2+cap=96配置中，cap=96完全被fw=2遮蔽**。如果要让两个参数都有独立贡献，应该考虑fw=4+cap=64这样的组合。

2. **存在"甜点"现象**：多个参数在适度限制时IPC反而超过baseline（IQ cap=24: +5.1%, ROB cap=64: +4.1%, LSQ cap=24: +1.4%, dw=4: +0.5%）。原因是baseline的8-wide O3 CPU对这类workload过度投机，适度限制反而提高了有效吞吐。

3. **Width参数（fetch/rename/dispatch）的效果模式相似**，都是通过限制流水线中间的指令流吞吐来间接控制后端压力。其中dispatch width的"无损区间"最宽（dw=4就已经无损）。

4. **LSQ Cap是唯一能产生"硬性暂停"的后端参数**，因为它通过直接触发取指暂停来限制。其他参数（IQ Cap, ROB Cap）的限制更间接。

### 4. 建议的conservative模式参数组合

基于sweep结果，建议测试以下配置作为新的conservative模式：

| 方案 | 参数 | 预期IPC影响 | 理由 |
|------|------|-----------|------|
| **Balanced** | fw=4, dw=4, robcap=64 | 约-10% | fw=4和robcap=64各贡献独立限制，dw=4无损 |
| **Moderate** | fw=4, iqcap=24, lsqcap=24 | 约-5%~0% | 利用"甜点"效应，可能比baseline还好 |
| **Aggressive Save** | fw=2, lsqcap=16 | 约-46% | 最大功耗节省，但性能代价很大 |
