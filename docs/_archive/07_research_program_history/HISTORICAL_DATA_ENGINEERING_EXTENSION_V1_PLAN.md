# 下一阶段任务：Historical Data Engineering Extension V1

## 背景

请先完整审阅当前仓库和最近完成的历史数据研究，包括：

- Maximum Historical Extension & Qualification；
- Historical Frontier Admission；
- Historical Data Authority Resolution；
- Factor Universe V2；
- 当前 frozen Matrix；
- 项目已有所有数据源、缓存和数据更新流程。

不要仅按照本任务描述机械实现。

前几轮已经完成了大量历史数据审计，现在需要调整研究方向。

---

# 核心认识调整

此前我们过度强调 historical provider vintage。

现在明确：

> 本项目是个人 A 股量化研究，不要求证明今天数据库中保存的历史记录与当年数据库 snapshot 完全一致。

对于 Fundamental PIT，只要能够利用可靠的：

- announcement date；
- financial announcement date；
- revision / update information；

合理重建历史时点可见数据，就可以作为研究数据。

仍然必须严格避免：

- 使用未来公告；
- 使用尚未公开的 revision；
- survivorship bias；
- label leakage；
- train / validation 时间泄漏。

也就是说：

> **降低的是历史数据库审计标准，不是降低防未来函数标准。**

---

# 本阶段核心目标

现在不要再让当前 `2016-07` coverage candidate 决定历史范围。

下一阶段目标是：

> **主动将项目的数据工程向更早、具有研究价值的 A 股历史推进。**

目前从文献、A 股制度发展和 Qlib 等研究实践来看，2007/2008 左右是非常值得重点支持的现代 A 股研究时期；2000 左右则是值得保留的更长历史能力。

这些日期是数据工程的研究目标，不是最终训练集起点。

最终模型究竟应该使用：

- 2000+；
- 2007/2008+；
- 或较短 rolling history；

将在后续独立研究。

本阶段先解决：

> **我们能不能把需要的数据真正准备出来。**

---

# 优先推动 Full Factor Universe V2 向前扩展

请自行分析 Factor Universe V2 各数据依赖，并尽可能将完整因子体系历史向前推进。

重点不要局限于当前 Tushare coverage。

如果某个数据层在早期存在缺口，应先调查：

- 项目其他现有数据源；
- 已有历史 caches；
- Qlib provider；
- BaoStock；
- AkShare；
- 当前已经集成或曾经使用过的其他 source；
- 必要时成熟可靠的外部公开数据来源。

项目本身已经存在多数据源体系。

请优先复用、组合和交叉验证现有能力，而不是重新造一个独立数据系统。

---

# 不要让单个数据源成为历史硬边界

例如：

> Tushare moneyflow 某时期 coverage 不完整

不应直接推出：

> 整个模型只能从该时期以后训练。

而应该先回答：

- 是否有其他 source 提供等价或兼容信息；
- 是否可以从项目已有数据合理恢复；
- 是否只是 universe denominator 问题；
- 是否只是 API 调用方式问题；
- 是否确实存在不可补的数据断层。

只有确认某项信息真实不可恢复后，才把它视为数据工程限制。

---

# Practical Reconstructed PIT

Fundamental 数据统一采用 practical reconstructed PIT 思路。

目标是：

> 根据当前获得的历史 statement/revision/announcement records，重建历史时点可见状态。

不要继续研究：

> provider 在 2012 年当天的数据库 snapshot 究竟长什么样。

这一问题不再作为 Full V2 历史扩展的 blocker。

但必须继续验证现有 PIT pipeline 在向前扩展后不会：

- 使用未来公告；
- 提前使用 revision；
- 错误 forward-fill；
- 混用不同 report period；
- 出现其他实际 leakage。

---

# Practical Historical Universe

Lifecycle 同样采用 practical reconstruction。

允许综合：

- Qlib intervals；
- list / delist metadata；
- namechange；
- historical market presence；
- 多数据源历史存在性；

构造合理的 historical security master。

不再要求获得逐日 archived security-master snapshots。

真正目标是：

> 尽可能避免 survivorship bias，并合理恢复当时真实存在的证券集合。

---

# 数据历史可以分层

不要强迫所有因子拥有完全相同的历史。

可以保留例如：

```text id="m2kvre"
Full-feature common history
Long-history core
其他有充分经济意义的历史层
```

如果 price-volume 因子可以可靠追溯到 2000，而 fundamental / moneyflow 只能推到更晚：

不要删除长历史能力。

应明确记录各 factor family 的历史 frontier。

后续由模型研究决定不同 representation / history 的价值。

---

# 目标不是立即选最终 start date

本阶段不应该得出：

```text id="yb5vp2"
最佳训练起点 = YYYY
```

本阶段只负责尽可能建立可用历史数据。

后续将单独开展：

> A-share Historical Sample / Training History Study

在那里根据：

- 高质量文献；
- 市场制度变化；
- non-stationarity；
- development performance；

比较少量预注册的 history hypotheses。

因此这里不要运行模型来选择数据起点。

---

# 尽可能真正完成历史扩展

这一阶段不再以 probe 和报告为主要成果。

如果数据条件允许，应真正：

- 获取必要历史 raw data；
- 建立可恢复的缓存；
- 扩展 reconstructed PIT；
- 扩展 historical universe；
- materialize historical factors；
- 生成新的 Extended Matrix。

不要覆盖当前 frozen Matrix。

新 Matrix 必须有独立 identity / lineage。

---

# 新旧 Matrix 重叠验证

如果成功生成 Extended Matrix，需要重点验证：

> 新 Matrix 在现有 2021+ 区间是否能够复现旧 frozen Matrix。

重点调查任何：

- factor value；
- PIT result；
- universe；
- missingness；
- schema；

差异。

合理的 upstream data revision 可以记录解释，但不能静默改变历史证据。

---

# 数据工程应尽可能向前，而不是人为停在某个年份

不要因为：

```text id="mvmdqp"
2008 是一个方便的目标
```

就禁止继续向前。

如果某些数据层能够合理推进到：

```text id="s9prdi"
2000+
```

就保留这些能力。

如果 Full V2 也能够进一步推进，继续推进。

本阶段应找出：

> **实际能够构建出来的最大可靠历史。**

而不是提前规定答案。

---

# 重点记录真实不可解决的数据缺口

最终真正有价值的是知道：

```text id="ugauph"
哪些字段可以到2000
哪些可以到2007
哪些只能到更晚
为什么
有没有替代source
是否影响哪些factor
```

对于真实不可恢复的历史信息，要明确记录。

但不要把“当前 provider 不方便”与“历史信息不存在”混为一谈。

---

# 本阶段不做模型研究

不要启动：

- Structured ML；
- LightGBM competition；
- DoubleEnsemble；
- training-history selection；
- Model V2；
- Portfolio V2；
- Strategy V2。

也不要重新设计 Research Protocol。

本阶段只负责：

> **把数据工程能力尽可能向前推。**

---

# 最终希望回答

REPORT 请重点回答：

1. 最终实际把数据工程推到了多早？
2. Full Factor Universe V2 最早可以合理 materialize 到哪里？
3. 各 factor family 分别可以追溯到哪里？
4. 哪些历史字段通过其他数据源成功补齐？
5. 哪些字段仍存在真实不可恢复缺口？
6. 是否形成 Full-history / long-history 等多个数据层？
7. Practical reconstructed PIT 是否稳定通过 leakage checks？
8. Historical universe 是否能够合理控制 survivorship bias？
9. 是否生成 Extended Matrix？
10. Extended Matrix 实际覆盖多少 dates / instruments / factors？
11. 与现有 2021+ Matrix overlap 是否一致？
12. 现在具备哪些可供后续研究选择的 historical dataset hypotheses？

---

# 执行方式

这是开放式数据工程任务。

请：

```text id="d5soxp"
read repository
↓
map existing sources
↓
identify early-history gaps
↓
search existing alternatives
↓
extend raw history
↓
reconstruct PIT / universe
↓
materialize factors
↓
build Extended Matrix if feasible
↓
validate overlap
```

具体：

- 如何分段；
- 使用哪个 provider；
- 不同 source 如何融合；
- 哪些字段需要 fallback；
- 怎样实现缓存与 checkpoint；
- 怎样处理资源和性能；

由你根据仓库实际情况决定。

不要机械照搬 prompt 中的示例。

---

# 治理要求

保持：

```text id="1uoxgj"
model outcomes read = false
Structured ML started = false
Research Protocol redesign started = false
Factor Universe V2 definitions changed = false
Strategy V1 changed = false
Forward Track changed = false
old frozen Matrix changed = false
```

同时：

- 保留数据 lineage；
- 不写入 token；
- 不提交巨大 raw datasets；
- 保护用户未跟踪文件。

完成真实实施、测试和验证后：

1. review diff；
2. 运行必要 tests / validators；
3. commit；
4. push；
5. 汇报 branch 和 SHA；
6. 汇报最终历史覆盖；
7. 汇报各 factor family frontier；
8. 汇报 Extended Matrix 状态；
9. 汇报 overlap validation；
10. 汇报真正剩余的数据缺口；
11. 停止。

不要自动进入模型阶段。

---

# 成功标准

本阶段不追求：

> “证明某个数据源绝对权威”。

也不追求：

> “提前选出最佳训练年份”。

真正目标是：

> **尽可能把可合理使用的 A 股历史数据准备出来，为后续科学选择训练历史提供数据基础。**

研究问题决定需要什么历史。

数据工程负责尽可能实现它。

最终训练起点由后续研究决定，而不是由当前哪个 API 最方便决定。
