# 第五步具体计划：因子研究模块与模型扩展边界

本文档用于校准后续路线。当前项目面向量化新手，目标是通过 Qlib 和开源项目整合出一个可复现、可解释、可逐步扩展的 A 股量化研究框架。因此，第五步的重点不是马上追求复杂模型，而是建立因子研究模块，并把模型扩展限定为对照实验。

## 1. 路线判断

当前方向总体准确：

- 先做数据层和可复现实验是正确的。
- 保留 `CSI500 + LightGBM + Alpha158` 作为主基线是必要的。
- 宽股票池路线不能直接用全市场，`all_stock_shsz_liquid2000` 比原始 `all_stock_shsz` 更适合继续研究。
- 目前最大问题不是“模型不够复杂”，而是因子质量、股票池、组合约束和交易可行性还没有被系统拆开。

需要修正的地方：

- 不应把“多模型实验”放在因子研究之前大规模推进。
- 不应因为 `all_stock_shsz` 的 IC 高就认定宽股票池已经可用。
- 不应在缺少单因子分析和组合约束报告时进入深度学习或强化学习。

## 2. 下一阶段优先级

优先级从高到低：

1. `liquid2000` 上的 TopK / n_drop 参数扫描。
2. 因子研究模块第一版。
3. 线性模型 sanity check。
4. XGBoost/CatBoost 与 LightGBM 对照。
5. Alpha360 或自定义多因子集合。
6. 自定义组合策略。
7. 深度学习模型。

暂缓：

- 强化学习。
- 高频/分钟级数据。
- 自动实盘下单。
- 复杂神经网络模型矩阵。

## 3. 因子研究模块目标

第一版因子研究模块只做日频横截面因子评价，不做模型训练。

目标：

- 能定义一批可解释因子。
- 能计算因子覆盖率和缺失率。
- 能计算 IC、Rank IC、ICIR。
- 能做分组收益。
- 能估算换手率。
- 能检查因子相关性和冗余度。
- 能输出 Markdown/CSV 报告。

建议目录：

```text
factor_research/
  __init__.py
  config.yaml
  factor_library.py
  evaluator.py
  report.py
scripts/
  run_factor_research.ps1
```

建议输出：

```text
outputs/factor_research/<market>_<start>_<end>/
  factor_summary.csv
  ic_series.csv
  group_return.csv
  turnover.csv
  correlation.csv
  factor_research_report.md
```

## 4. 第一批因子

先从简单、可解释、可排查的因子开始。

| 类型 | 因子例子 | 目的 |
| --- | --- | --- |
| 动量 | `ret_5`, `ret_10`, `ret_20` | 判断趋势延续 |
| 反转 | `ret_1`, `ret_3`, `ret_5` 的负值 | 判断短期反转 |
| 波动率 | `std_20`, `amplitude_20` | 判断风险和噪声 |
| 流动性 | `amount_mean_20`, `amount_std_20` | 判断成交活跃度 |
| 量价 | `corr_ret_volume_20`, `volume_ratio_5_20` | 判断量价配合 |

标签建议：

```text
未来 1 日收益
未来 5 日收益
```

第一版先使用 Qlib 表达式和当前 provider 中已有字段，不引入外部基本面数据。

## 5. 因子入选规则

第一版只使用硬规则，避免主观挑选。

建议规则：

- 覆盖率高于 `95%`。
- 平均 Rank IC 绝对值高于 `0.02`。
- ICIR 绝对值高于 `0.20`。
- 分组收益方向与 IC 方向一致。
- 与已入选因子相关性绝对值低于 `0.80`。
- 因子逻辑能用一句话解释。

不满足规则的因子不删除，只标记为 `rejected` 或 `watchlist`。

## 6. 模型扩展边界

模型扩展应服务于验证因子和数据，而不是替代因子研究。

第一批模型对照：

| 模型 | 优先级 | 目的 |
| --- | ---: | --- |
| Linear/Ridge/Lasso | 高 | 检查因子是否有线性解释力 |
| LightGBM | 高 | 主基线 |
| XGBoost | 中 | 与 LightGBM 同类对照 |
| CatBoost | 中 | 与 LightGBM 同类对照 |
| MLP | 低 | 简单深度模型观察 |
| LSTM/ALSTM | 低 | 时序模型，待数据和因子稳定后再做 |

暂不做：

- Transformer 类复杂模型。
- 强化学习策略。
- 自动模型搜索。

## 7. 与第四步的衔接

第四步继续处理组合约束：

- `liquid2000` 上的 TopK / n_drop 参数扫描。
- 异常流动性标的核查。
- Benchmark 和交易成本敏感性检查。

第五步并行规划因子研究，但执行时应先完成最小因子研究框架，再扩展模型。

推荐执行顺序：

1. 创建因子研究模块目录和配置。
2. 实现 5 到 10 个基础因子。
3. 输出单因子 IC/Rank IC/分组收益报告。
4. 在 `csi500` 和 `liquid2000` 上各跑一版因子报告。
5. 根据因子报告决定是否引入线性模型对照。
6. 之后再做 XGBoost/CatBoost 对照。

## 8. 完成标准

- 有可运行的因子研究入口。
- 至少 5 个基础因子完成评价。
- 有 `csi500` 与 `liquid2000` 的因子报告。
- 有明确的因子入选/剔除规则。
- 模型扩展计划被约束在对照实验范围内。
- 不因为单次回测收益高而跳过因子解释。

## 9. 当前执行结果

状态：第一版因子研究模块已完成。

新增模块：

```text
factor_research/
scripts/run_factor_research.ps1
```

已实现基础因子：

```text
ret_5
ret_10
ret_20
rev_5
std_20
amplitude_20
amount_mean_20
amount_std_20
volume_ratio_5_20
corr_ret_volume_20
```

已生成报告：

```text
outputs/factor_research/csi500_2017-01-01_2020-08-01/factor_research_report.md
outputs/factor_research/all_stock_shsz_liquid2000_2017-01-01_2020-08-01/factor_research_report.md
outputs/reports/factor_research_initial_comparison.md
```

初步结论：

- `liquid2000` 上短期反转 `rev_5` 的 Rank IC 高于 `csi500`。
- 高波动、高振幅因子在两个股票池里都偏负向。
- 流动性水平适合作为股票池过滤条件，但原始 `amount_mean_20` 本身不是明显正向 alpha。

下一步：

1. 增加稳健流动性因子，降低极端成交额样本影响。
2. 增加 `label_5d_t1` 的因子评价。
3. 在因子结果基础上做线性模型 sanity check。

## 10. 标签周期对比结果

状态：已完成 `label_5d_t1` 第一轮评价。

新增报告：

```text
outputs/factor_research/csi500_2017-01-01_2020-08-01_label5d/factor_research_report.md
outputs/factor_research/all_stock_shsz_liquid2000_2017-01-01_2020-08-01_label5d/factor_research_report.md
outputs/reports/factor_label_comparison.md
outputs/reports/factor_label_comparison.csv
```

关键观察：

- `label_5d_t1` 下，`std_20`、`amplitude_20`、`ret_20` 的负向 Rank IC 更强。
- `rev_5` 在 1 日和 5 日标签下都为正，但 5 日标签明显衰减。
- `all_stock_shsz_liquid2000` 的因子分离度整体强于 `csi500`。
- 原始流动性因子更适合作为 universe/tradability 过滤，而不是直接作为正向 alpha。

对后续的影响：

- 线性模型 sanity check 应同时测试 `label_1d_t1` 和 `label_5d_t1`。
- 因子方向需要显式元数据，例如 `rev_5` 正向、`std_20/amplitude_20/ret_20` 负向。
- 下一轮因子库应加入稳健流动性因子和风险惩罚类组合因子。

## 11. 线性模型 sanity check

状态：已完成第一轮。

新增脚本：

```text
scripts/run_linear_factor_model.py
```

报告：

```text
outputs/reports/linear_factor_model_sanity_check.md
```

结果摘要：

| market | label | Rank IC | Rank ICIR |
| --- | --- | ---: | ---: |
| `csi500` | `label_1d_t1` | `0.013532` | `0.113278` |
| `all_stock_shsz_liquid2000` | `label_1d_t1` | `0.029948` | `0.326393` |
| `csi500` | `label_5d_t1` | `0.003396` | `0.027699` |
| `all_stock_shsz_liquid2000` | `label_5d_t1` | `-0.000956` | `-0.009671` |

结论：

- 基础因子的线性组合对 1 日标签有解释力，尤其在 `liquid2000` 上更明显。
- 同一组因子对 5 日标签不稳定，不能直接把 1 日反转逻辑外推到 5 日。
- 下一步不急着做 XGBoost/CatBoost，应先补因子方向元数据、稳健流动性因子和风险惩罚类因子。

## 12. 因子打分组合第一轮

状态：已完成第一轮规则组合验证。

新增脚本：

```text
scripts/run_factor_score_portfolio.py
scripts/summarize_factor_score_portfolios.py
```

报告：

```text
outputs/reports/factor_score_portfolio_scan.md
outputs/reports/factor_score_portfolio_scan.csv
```

回测口径：

```text
label: label_1d_t1
cost: 5 bps per one-way turnover
score normalization: daily cross-sectional 1%/99% winsorized z-score, clipped to +/-3
```

结果摘要：

| portfolio | net annualized excess | net excess IR | average turnover |
| --- | ---: | ---: | ---: |
| `liquid2000 low_risk_only` | `-0.037848` | `-0.362253` | `0.071484` |
| `liquid2000 rev_5 + low risk` | `-0.067818` | `-0.784255` | `0.187962` |
| `liquid2000 rev_5 only` | `-0.140270` | `-1.859341` | `0.420521` |
| `csi500 rev_5 + low risk` | `-0.118672` | `-1.518602` | `0.198092` |

结论：

- 单因子 Rank IC 为正，不等于简单 TopK 组合可交易。
- `rev_5` 直接选股换手较高，成本和组合暴露会显著侵蚀表现。
- 低风险组合相对没那么差，但仍不能作为可用策略。
- 下一步应做分层 long-short、行业/市值/流动性暴露检查，再决定是否把因子打分接入 Qlib 策略配置。

## 13. 分层 long-short 诊断

状态：已完成第一轮。

新增脚本：

```text
scripts/run_factor_long_short.py
scripts/summarize_factor_long_short.py
```

报告：

```text
outputs/reports/factor_long_short_comparison.md
outputs/reports/factor_long_short_comparison.csv
```

诊断口径：

```text
label: label_1d_t1
quantile: top 20% long, bottom 20% short
cost: 5 bps per one-way turnover
```

结果摘要：

| market | signal | net annualized return | net IR |
| --- | --- | ---: | ---: |
| `all_stock_shsz_liquid2000` | `std_20` | `0.140036` | `0.923612` |
| `all_stock_shsz_liquid2000` | `amplitude_20` | `0.143531` | `0.912179` |
| `all_stock_shsz_liquid2000` | `score` | `0.125890` | `0.859777` |
| `all_stock_shsz_liquid2000` | `rev_5` | `0.094322` | `0.763515` |
| `csi500` | `score` | `-0.090962` | `-0.473142` |

结论：

- `liquid2000` 上 long-short 信号为正，而前一轮 long-only TopK 为负，说明排序信号存在，但简单多头组合吸收了不利暴露。
- `csi500` 上同类 long-short 诊断为负，进一步支持继续以 `liquid2000` 作为因子研究主股票池。
- 低波动、低振幅是当前最稳定的横截面排序信号。
- 下一步应检查 long leg / short leg 的流动性、波动、动量暴露，并尝试做分组内选股或风险约束后的 long-only 组合。

## 14. 多空腿暴露检查

状态：已完成第一轮。

新增报告：

```text
outputs/reports/factor_long_short_exposure_comparison.md
outputs/reports/factor_long_short_exposure_comparison.csv
```

暴露检查口径：

- 正数表示多头腿平均值高于空头腿。
- `spread_mean_label` 表示多头腿未来收益减空头腿未来收益。
- 重点观察 `score`、`rev_5`、`std_20`、`amplitude_20`、`ret_20`、`amount_mean_20`。

`liquid2000` 关键观察：

| signal | spread label | spread std_20 | spread amplitude_20 | spread ret_20 | spread amount_mean_20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `std_20` | `0.000605` | `-0.024905` | `-0.027473` | `-0.061912` | `-288662.777425` |
| `amplitude_20` | `0.000611` | `-0.022265` | `-0.030678` | `-0.067902` | `-251199.878340` |
| `score` | `0.000594` | `-0.022215` | `-0.027311` | `-0.105161` | `-273503.417232` |
| `rev_5` | `0.000563` | `0.000103` | `0.000358` | `-0.114712` | `-44156.246853` |

结论：

- 当前有效排序主要来自“低风险 + 前期弱势/反转”组合。
- 多头腿通常比空头腿流动性更低，因此 long-only 组合不能只按分数选 TopK，需要加流动性分桶或最低流动性约束。
- `csi500` 中类似风险排序没有正收益，说明该信号更适合在更宽的 `liquid2000` 横截面中使用。
- 下一步应做“流动性分桶内低波动/低振幅选股”，并比较其 long-only 表现是否优于上一轮朴素 TopK。
