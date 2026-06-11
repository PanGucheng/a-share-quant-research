# 第四步具体计划：宽股票池组合约束与流动性过滤

第三步完成了 `all_stock_shsz` 宽股票池 qrun。结果显示信号 IC 明显提升，但组合超额收益为负，说明问题已经从“数据能不能跑”转向“宽股票池是否有合适的组合构建和交易约束”。

本步骤不追求更多复杂模型。它的目标是先回答一个更基础的问题：在 A 股宽股票池里，怎样的股票池和组合约束能让已有信号变成可解释、可交易、可复验的组合结果。

## 1. 当前观察

完整宽股票池 qrun：

```text
Experiment ID: 853240997789502366
Run ID: 9a3ead374ca94ed78901e856d49c600f
Config: configs/workflow_lightgbm_alpha158_all_stock_shsz_community_20260609.yaml
```

指标：

| metric | value |
| --- | ---: |
| IC | `0.176501` |
| ICIR | `1.629054` |
| Rank IC | `0.072703` |
| Rank ICIR | `0.819241` |
| excess return with cost annualized return | `-0.060844` |
| excess return with cost information ratio | `-0.379644` |
| excess return with cost max drawdown | `-0.351861` |

解释：

- 排序信号有效性看起来很强。
- 现有 `TopkDropoutStrategy(topk=50, n_drop=5)` 不适合直接套到 5532 只沪深股票的宽股票池。
- 负收益可能来自流动性、停牌/不可交易、宽股票池 benchmark 选择、TopK 太小、换手和交易成本、以及极端小盘/异常数据暴露。

## 2. 第一轮修正：流动性过滤 universe

已新增脚本：

```text
scripts/create_liquidity_universe.py
```

第一版流动性股票池：

```text
outputs/universes/community_20260609/all_stock_shsz_liquid2000.txt
```

筛选口径：

- provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- source universe: `all_stock_shsz`
- observation window: `2016-01-01` to `2016-12-31`
- metric: median `$amount`
- minimum valid days: `180`
- selected instruments: top `2000`

安装到派生 provider：

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/all_stock_shsz_liquid2000.txt
```

生成配置：

```text
configs/workflow_lightgbm_alpha158_all_stock_shsz_liquid2000_community_20260609.yaml
```

验证报告：

```text
outputs/reports/provider_validation_all_stock_shsz_liquid2000_community_20260609.md
```

## 3. 下一步实验顺序

### 实验 A：`liquid2000` 原策略复跑

状态：已完成。

目的：只改变股票池，不改变模型和策略参数，判断流动性过滤是否改善组合表现。

命令：

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_baseline.ps1 -ConfigPath E:\qlib_prj\qlib_baseline\configs\workflow_lightgbm_alpha158_all_stock_shsz_liquid2000_community_20260609.yaml
```

验收：

- qrun 完成。
- 写入 `outputs/reports/baseline_summary.csv`。
- 与 `all_stock_shsz` 和 `csi500` 对比 IC、Rank IC、年化超额收益、IR、最大回撤。

结果：

```text
Experiment ID: 365355581238963703
Run ID: 8902c70d60f14afa8064275c1db3404a
Config: configs/workflow_lightgbm_alpha158_all_stock_shsz_liquid2000_community_20260609.yaml
Log: logs/qrun_workflow_lightgbm_alpha158_all_stock_shsz_liquid2000_community_20260609_20260612_002008.log
```

| metric | all_stock_shsz | liquid2000 |
| --- | ---: | ---: |
| IC | `0.176501` | `0.072184` |
| ICIR | `1.629054` | `0.846341` |
| Rank IC | `0.072703` | `0.062222` |
| Rank ICIR | `0.819241` | `0.665992` |
| excess return with cost annualized return | `-0.060844` | `0.054915` |
| excess return with cost information ratio | `-0.379644` | `0.312190` |
| excess return with cost max drawdown | `-0.351861` | `-0.169295` |

Interpretation:

- Liquidity filtering reduced headline IC but made the portfolio result usable again.
- The current model and TopK strategy are not enough for a raw broad universe.
- `liquid2000` is a better starting universe than raw `all_stock_shsz` for the next portfolio experiments.

### 实验 B：TopK 参数扫描

状态：待执行。

候选参数：

| topk | n_drop |
| ---: | ---: |
| 50 | 5 |
| 100 | 10 |
| 200 | 20 |
| 300 | 30 |

目的：

- 宽股票池上 `topk=50` 可能过窄。
- 提高持仓数可能降低噪声、停牌冲击和换手集中度。

### 实验 C：异常流动性核查

状态：待执行。

需要核查：

```text
SH601313
```

它在 2016 年 `$amount` 中位数排名异常靠前。下一步应检查该标的是否为真实股票、指数/特殊符号误入、或数据口径异常。

### 实验 D：因子研究模块衔接

状态：计划中。

目的：

- 判断 `Alpha158` 的哪些信号在 `liquid2000` 中真正有效。
- 分离“模型有效”和“少数强因子/异常数据驱动”的情况。
- 为后续自定义因子库提供基准。

第一批输出：

```text
docs/STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md
```

实验 D 只定义计划，不在本步骤直接运行。

## 4. 完成标准

- 完成 `liquid2000` 原策略 qrun。
- 记录与 `all_stock_shsz`、`csi500` 的对比。
- 至少形成一个“继续使用宽股票池”或“回到 CSI 指数池优先”的阶段性判断。
- 明确下一轮是否做 TopK 参数扫描。

当前阶段性判断：

- CSI500 仍作为主要基线锚点。
- 宽股票池路线可以继续，但必须从 `liquid2000` 这类可交易性更好的 universe 开始。
- 下一轮优先做 `liquid2000` 上的 TopK 参数扫描，而不是继续扩大股票池。
- 因子研究应与 TopK 扫描并行规划，但执行顺序上先完成最小因子分析框架，再大规模扩展模型。
