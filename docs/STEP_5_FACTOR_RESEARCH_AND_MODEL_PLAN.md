# 第五步具体计划：因子研究模块与模型扩展边界

本文档用于校准后续路线。当前项目面向量化新手，目标是通过 Qlib 和开源项目整合出一个可复现、可解释、可逐步扩展的 A 股量化研究框架。因此，第五步的重点不是马上追求复杂模型，而是建立因子研究模块，并把模型扩展限定为对照实验。

补充约束：使用者是个人投资者，不希望承担过高交易频率和过高换手。因此，后续研究目标应从 1 日短线预测，逐步转向 10 到 20 个交易日持有周期，并优先评估周度/月度调仓、换手约束和交易成本敏感性。`label_1d_t1` 保留为诊断信号速度的工具，不再作为最终策略主目标。

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
未来 10 日收益
未来 20 日收益
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

## 15. 流动性约束 long-only 组合

状态：已完成第一轮。

新增脚本：

```text
scripts/run_liquidity_bucket_portfolio.py
scripts/summarize_liquidity_bucket_portfolios.py
```

报告：

```text
outputs/reports/liquidity_bucket_portfolio_comparison.md
outputs/reports/liquidity_bucket_portfolio_comparison.csv
```

回测口径：

```text
market: all_stock_shsz_liquid2000
label: label_1d_t1
topk: 200
cost: 5 bps per one-way turnover
score: rev_5:1,std_20:-1,amplitude_20:-1
```

结果摘要：

| selection | average liquidity bucket | net annualized excess | net excess IR | average turnover |
| --- | ---: | ---: | ---: | ---: |
| `min_liquidity_bucket3` | `3.837250` | `-0.039804` | `-0.452260` | `0.159046` |
| `bucket_balanced` | `3.000000` | `-0.063406` | `-0.704341` | `0.189105` |
| `plain_topk` | `2.509882` | `-0.067818` | `-0.784255` | `0.187962` |

结论：

- 流动性约束改善了朴素 long-only 组合，但还没有把组合变成可用策略。
- 排除最低两个流动性桶，比在全部流动性桶中强制均衡选股更好。
- 这确认了流动性暴露是问题的一部分，但不是全部问题。
- 下一步应加入风险/基准约束，例如限制组合平均波动、振幅、动量暴露，或者做 benchmark-relative 的分组内选股。

## 16. 时间切片稳定性评估

状态：已完成 `all_stock_shsz_liquid2000 + label_1d_t1` 第一轮。

新增脚本：

```text
scripts/run_factor_time_slices.py
```

报告：

```text
outputs/reports/factor_time_slice_stability_liquid2000_label1d.md
outputs/reports/factor_time_slice_stability_liquid2000_label1d.csv
outputs/reports/factor_time_slice_summary_liquid2000_label1d.csv
```

时间角色：

| slice | date range | role |
| --- | --- | --- |
| `historical_reference_2010_2016` | `2010-01-01` to `2016-12-31` | 历史参考，不作为主训练目标 |
| `baseline_alignment_2017_2020` | `2017-01-01` to `2020-08-01` | Qlib 风格 baseline 对齐 |
| `main_research_2021_2023` | `2021-01-01` to `2023-12-29` | 后续主研究/训练窗口 |
| `recent_oos_2024_2026` | `2024-01-01` to `2026-06-09` | 近现实样本外检验 |

稳定性摘要：

| factor | expected direction | positive directional slices | mean directional Rank IC | recent directional Rank IC |
| --- | --- | ---: | ---: | ---: |
| `amplitude_20` | negative | `4/4` | `0.039469` | `0.038382` |
| `std_20` | negative | `4/4` | `0.037023` | `0.039549` |
| `rev_5` | positive | `4/4` | `0.036709` | `0.025411` |

结论：

- `2010-2016` 仍有参考价值，但不应作为主训练期。
- `2021-2023` 与 `2024-2026` 都支持低波动、低振幅、短期反转方向，说明这些不是只在旧 baseline 时段有效。
- `rev_5` 在近期仍为正，但强度低于历史参考期；后续组合中应控制换手，避免被交易成本吃掉。
- 下一步的策略研究应以 `2021-2023` 为主要调参窗口，并把 `2024-2026` 留作轻触碰的近现实检验。

## 17. 个人投资者低频约束

状态：已调整研究方向。

背景：

- 当前大部分实验使用 `label_1d_t1`，属于短线日频研究。
- 个人投资者通常不适合高换手、高频调仓，因为交易成本、滑点、精力成本和执行误差都会明显放大。
- 现有结果也显示 `rev_5` 虽然有 Rank IC，但直接 long-only 会带来较高换手。

标签扩展：

```text
label_1d_t1   # 诊断短线信号，不作为最终主策略目标
label_5d_t1   # 短中期观察
label_10d_t1  # 约两周持有，个人投资者优先研究
label_20d_t1  # 约一月持有，个人投资者优先研究
```

后续优先级：

1. 对 `label_10d_t1` 和 `label_20d_t1` 跑时间切片稳定性评估。
2. 对 10 日/20 日标签重新评估低波动、低振幅、反转、流动性因子。
3. 组合回测改为周度或月度调仓，不再默认每日调仓。
4. 把平均换手、单次换手、持仓天数和成本敏感性放进核心报告。
5. 只有在 2021-2023 有效，并且 2024-2026 仍然稳定的低频组合，才进入模型对照阶段。

## 18. 低频标签时间切片结果

状态：已完成 `label_10d_t1` 和 `label_20d_t1` 第一轮。

新增报告：

```text
outputs/reports/factor_time_slice_stability_liquid2000_label10d.md
outputs/reports/factor_time_slice_stability_liquid2000_label10d.csv
outputs/reports/factor_time_slice_summary_liquid2000_label10d.csv
outputs/reports/factor_time_slice_stability_liquid2000_label20d.md
outputs/reports/factor_time_slice_stability_liquid2000_label20d.csv
outputs/reports/factor_time_slice_summary_liquid2000_label20d.csv
outputs/reports/factor_horizon_comparison_liquid2000.md
```

跨持有周期对比：

| label | factor | positive directional slices | mean directional Rank IC | recent directional Rank IC |
| --- | --- | ---: | ---: | ---: |
| `label_1d_t1` | `amplitude_20` | `4/4` | `0.039469` | `0.038382` |
| `label_1d_t1` | `std_20` | `4/4` | `0.037023` | `0.039549` |
| `label_1d_t1` | `rev_5` | `4/4` | `0.036709` | `0.025411` |
| `label_10d_t1` | `amplitude_20` | `4/4` | `0.065014` | `0.045089` |
| `label_10d_t1` | `std_20` | `4/4` | `0.062395` | `0.047369` |
| `label_10d_t1` | `rev_5` | `4/4` | `0.028299` | `0.034178` |
| `label_20d_t1` | `amplitude_20` | `4/4` | `0.075864` | `0.051124` |
| `label_20d_t1` | `std_20` | `4/4` | `0.071619` | `0.053787` |
| `label_20d_t1` | `rev_5` | `4/4` | `0.030789` | `0.040805` |

结论：

- 低波动、低振幅因子在 10 日和 20 日标签下更强，尤其 `label_20d_t1`。
- `rev_5` 仍然方向稳定，但更适合作为辅助项，不适合作为高换手主驱动。
- 个人投资者路线应优先使用 `label_20d_t1`，以月度持有/调仓为主要研究方向；`label_10d_t1` 可作为更快反应的对照。
- 下一步组合实验应从 `label_20d_t1` 开始，增加周度/月度调仓约束和换手报告。

## 19. 统一可交易性标签层

状态：第一版建设中。

新增模块：

```text
tradability/
scripts/run_tradability_labels.ps1
scripts/validate_tradability_outputs.py
docs/TRADABILITY_LABEL_LAYER.md
```

定位：

- `tradability` 是后续因子研究、组合约束、回测约束的统一入口。
- 后续模块不得重复实现停牌、涨跌停、流动性、新股、异常数据过滤逻辑。
- 本模块只读取 Qlib provider 和数据质量诊断输出，不修改 Qlib 源码、不修改原始数据、不训练模型、不回测。

默认产物：

```text
outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv
```

首版目标：

- 生成 `date x instrument` 可交易性标签表。
- 输出 `can_buy`、`can_sell`、`tradability_score` 和 `disabled_reason`。
- 对 `amount` 缺失做优雅降级，优先使用 `amount`，否则使用 `close * volume`。
- 对无法精确判断的涨跌停、流动性、质量问题标记 `unknown` 或 `unavailable`，不强行判断。

## 20. 可交易性约束下的低频组合实验

状态：已完成第一轮主窗口与近现实窗口扫描。

新增脚本：

```text
scripts/run_low_frequency_tradability_portfolio.py
scripts/run_low_frequency_tradability_scan.py
scripts/summarize_low_frequency_portfolios.py
scripts/summarize_tradability_windows.py
```

新增报告：

```text
outputs/reports/tradability_window_comparison.md
outputs/reports/tradability_window_comparison.csv
outputs/reports/low_frequency_tradability_portfolio_comparison.md
outputs/reports/low_frequency_tradability_portfolio_comparison.csv
```

样本窗口：

| window | role |
| --- | --- |
| `2021-01-01` to `2023-12-29` | 主研究窗口 |
| `2024-01-01` to `2026-06-09` | 近现实样本外观察 |

可交易性过滤：

```text
can_buy == true
liquidity_bucket >= 3
tradability_score >= 75
eligible_count >= topk * 2
```

组合扫描：

```text
label_20d_t1 + rebalance_every=20 + topk=100/200/300
label_10d_t1 + rebalance_every=10 + topk=100/200/300
cost_bps=5/10/20
weights:
  low_risk = std_20:-1,amplitude_20:-1
  low_risk_rev = std_20:-1,amplitude_20:-1,rev_5:0.25
  low_risk_momentum_guard = std_20:-1,amplitude_20:-1,ret_20:-0.25
```

晋级门槛：

```text
cost_bps = 10
2021-2023 net annualized excess > 0
2021-2023 net excess IR >= 0.30
2024-2026 net annualized excess >= 0
2024-2026 net excess IR >= -0.20
average turnover <= 0.35
```

关键结果：

| window | best observed group | net annualized excess | net excess IR | average turnover |
| --- | --- | ---: | ---: | ---: |
| `2021-2023` | `label_20d_t1 top300 low_risk cost10` | `0.021351` | `0.298978` | `0.479905` |
| `2024-2026` | `label_20d_t1 top200 low_risk cost10` | `-0.082280` | `-0.534014` | `0.447500` |

结论：

- 没有组合通过晋级门槛，不能进入 XGBoost/CatBoost 或更复杂模型对照。
- 低波动/低振幅在 2021-2023 有弱正超额，但在 2024-2026 明显跑输可交易股票池。
- 换手仍高于个人投资者目标，月度调仓下仍需进一步降低组合变动。
- 当前问题不是模型不足，而是因子组合缺少基准相对约束、风格暴露控制和更稳健的市场状态过滤。

下一步：

1. 暂停模型扩展。
2. 做 benchmark-relative 组合：在流动性桶/风险桶内部选低波动低振幅，而不是全市场直接 TopK。
3. 引入持仓缓冲区，例如保留上期持仓中仍处于前 40% 的股票，只替换跌出阈值的股票。
4. 增加市场状态切片，至少区分上涨/下跌/震荡区间，检查低波动因子是否只在特定市场环境有效。

## 21. 因子研究框架 V2

状态：已完成第一版框架和默认运行结果。

这一步先不继续调具体策略，也不进入 XGBoost/CatBoost。当前目标是把因子研究的基础工具补齐，让后续新增因子、筛选因子、解释因子失效原因时有统一入口。

新增模块：

```text
factor_research/registry.py
factor_research/diagnostics.py
factor_research/candidate.py
scripts/run_factor_research_v2.py
scripts/summarize_factor_candidates.py
```

默认运行：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v2.py --output-dir outputs\factor_research_v2\liquid2000_default
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_factor_candidates.py --input-dir outputs\factor_research_v2\liquid2000_default --output-csv outputs\reports\factor_candidate_pool.csv --output-md outputs\reports\factor_candidate_pool.md
```

默认设计：

- 复用旧版 raw 时间切片摘要，避免重复计算 2010-2026 全历史 raw 诊断。
- 重新计算 `2021-2023` 和 `2024-2026` 的 `tradable_only` 诊断。
- `tradable_only` 过滤条件为 `can_buy == true`、`liquidity_bucket >= 3`、`tradability_score >= 75`。
- 候选判断覆盖 `label_10d_t1` 和 `label_20d_t1`。
- 桶内 IC 默认只对 `label_20d_t1` 运行，用于解释因子在流动性/波动率分桶中的稳定性。

输出：

```text
outputs/factor_research_v2/liquid2000_default/factor_registry.csv
outputs/factor_research_v2/liquid2000_default/factor_summary.csv
outputs/factor_research_v2/liquid2000_default/factor_time_slice.csv
outputs/factor_research_v2/liquid2000_default/factor_bucket_ic.csv
outputs/factor_research_v2/liquid2000_default/factor_group_monotonicity.csv
outputs/factor_research_v2/liquid2000_default/factor_correlation.csv
outputs/factor_research_v2/liquid2000_default/factor_candidate_decision.csv
outputs/factor_research_v2/liquid2000_default/factor_research_v2_report.md
outputs/reports/factor_candidate_pool.csv
outputs/reports/factor_candidate_pool.md
```

候选晋级规则：

```text
main tradable_only coverage >= 90%
main directional Rank IC > 0.03
recent OOS directional Rank IC > 0
raw time slices 至少 3/4 方向正确
main tradable_only 分组收益方向正确
monotonicity_score > 0
与已晋级因子的 Spearman correlation < 0.80
```

当前候选池结果：

| label | promote | reject | watch |
| --- | ---: | ---: | ---: |
| `label_10d_t1` | `1` | `1` | `8` |
| `label_20d_t1` | `1` | `1` | `8` |

晋级因子：

| label | factor | main directional Rank IC | OOS directional Rank IC | stability | monotonicity |
| --- | --- | ---: | ---: | ---: | ---: |
| `label_10d_t1` | `amplitude_20` | `0.087936` | `0.068054` | `1.000000` | `0.800000` |
| `label_20d_t1` | `amplitude_20` | `0.109863` | `0.075408` | `1.000000` | `1.000000` |

解释：

- `amplitude_20` 暂时是候选池里最值得继续研究的基础因子。
- `std_20` 自身也通过基础规则，但与 `amplitude_20` 高相关，被标记为 `redundant_weak`，暂不作为独立主因子。
- `rev_5` 在 10 日/20 日上有正向样本外表现，但主窗口强度没有达到晋级阈值，保留为 `watch`。
- 动量、流动性、量价相关类因子目前仍是观察变量，下一步要先明确方向假设、分桶解释和中性化方式。

下一步合理目标：

1. 扩展因子注册表，加入更多开源常见因子：估值/质量/成长/换手/偏度/流动性冲击等。
2. 增加因子中性化工具：至少支持行业、市值、流动性桶、波动率桶。
3. 增加分层诊断视图：按年份、市场状态、行业、流动性桶、波动率桶输出 IC 和分组收益。
4. 建立候选因子版本记录：每次新增因子都输出 candidate pool 差异，避免凭单次结果拍脑袋。
5. 在候选池稳定前，不新增复杂模型，不把 `promote` 因子直接等同于可实盘策略。

## 22. 参考 qlib_factor_platform 与 Alphalens 后的最小实现

状态：已落地第一版接口增强。

本阶段只增强因子研究与因子筛选模块，不替换 Qlib baseline，不新增模型训练，不做实盘，不引入复杂 UI。

新增文件：

```text
factor_research/dataset.py
factor_research/metrics.py
factor_research/selector.py
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_MODULE_PLAN.md
```

借鉴边界：

- 借鉴 `qlib_factor_platform` 的因子注册、因子计算、分析指标、运行工作流分层方式。
- 借鉴 Alphalens / alphalens-reloaded 的 `factor_data` 思路和 IC、Rank IC、ICIR、分组收益、换手率、相关性等指标体系。
- 不借鉴 Streamlit UI，不把本项目改造成独立平台，不绕开现有 Qlib 主线。

当前 `factor_research` 数据流：

```text
Qlib provider
  -> factor_library 基础因子
  -> dataset 合并 tradability_labels.csv
  -> dataset 合并 data_quality row_issues.csv
  -> tradable_only 前置过滤
  -> diagnostics / metrics 指标
  -> selector 候选筛选
  -> CSV / Markdown 输出
```

新增输出：

```text
factor_data_schema.md
factor_data_sample.csv
factor_missing_coverage.csv
factor_group_return.csv
factor_group_return_summary.csv
factor_turnover.csv
factor_turnover_summary.csv
```

新增指标：

- `missing_rate`
- `ic_win_rate`
- `mean_top_quantile_turnover`
- `median_top_quantile_turnover`
- `max_top_quantile_turnover`
- `has_data_quality_issue`

筛选规则已从硬编码扩展为参数化规则，默认包括：

```text
coverage >= 0.90
missing_rate <= 0.10
main directional Rank IC > 0.03
recent OOS directional Rank IC > 0
IC win rate >= 0.52
top quantile turnover <= 1.0
correlation < 0.80
```

后续继续完善：

1. 将 `factor_research/config.yaml` 直接接入 runner，减少命令行参数长度。
2. 增加行业、市值、流动性、波动率中性化。
3. 增加市场状态切片。
4. 扩展因子注册表，而不是直接进入模型训练。

## 23. 参考实现算法审计

状态：已完成第一轮。

参考仓库：

```text
tmp/reference_repos/qlib_factor_platform
tmp/reference_repos/alphalens-reloaded
```

审计文档：

```text
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_ALGORITHM_AUDIT.md
```

本轮校准结果：

- IC / Rank IC 口径与 Alphalens 的按日横截面 Spearman IC 体系一致。
- 分组收益补齐为显式输出，不再只依赖单调性摘要。
- 换手率修正为 Alphalens 风格：本期 top quantile 中新进入标的数除以本期 top quantile 标的数。
- 相关性保留 Spearman 排序相关，用于候选池冗余过滤。
- 继续保留 `tradable_only` 前置过滤，确保因子研究不会绕过已有 `data_quality` 和 `tradability` 约束。

新增/更新输出：

```text
outputs/factor_research_v2/liquid2000_default/factor_group_return.csv
outputs/factor_research_v2/liquid2000_default/factor_group_return_summary.csv
outputs/factor_research_v2/liquid2000_default/factor_turnover.csv
outputs/factor_research_v2/liquid2000_default/factor_research_v2_report.md
```

## 24. 因子研究 V3 开源参考调研

状态：已完成第一轮。

新增调研文档：

```text
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_V3_REFERENCE_SURVEY.md
```

本轮额外拉取到 `tmp/reference_repos/` 的参考仓库：

```text
JoinQuant/jqfactor_analyzer
jltxzxy/FactorTest
Jensenberg/multi-factor
jerryxyx/AlphaTrading
```

结论：

- 优先借鉴 `jqfactor_analyzer` 的预处理、中性化接口和 tear-sheet 指标组织。
- 借鉴 `FactorTest` 的 Barra/暴露相关性、双重排序、分组 IC 思路，但不引入其数据体系。
- 借鉴 `multi-factor` 的 MAD 去极值、z-score、行业/市值残差中性化顺序，但不复制代码。
- 借鉴 Qlib 原生 `CSZScoreNorm`、`CSRankNorm` 和 group return 口径，保持与现有 baseline 主线解耦。
- `AlphaTrading` 适合作为研究流程参考，暂不采用其中模型组合和 notebook 代码。

V3 最小实现方向：

1. 新增本地 DataFrame 版 `preprocess.py`。
2. 新增年份、流动性桶、波动率桶、市场状态切片。
3. 新增轻量中性化：流动性桶内标准化、波动率桶内标准化、成交额代理残差中性化。
4. 输出中性化前后 IC、Rank IC、分组收益、相关性对照。
5. 在候选池稳定前继续暂停新模型和策略参数调优。

## 25. 因子研究 V3 最小实现

状态：已完成第一版。

新增模块：

```text
factor_research/preprocess.py
factor_research/slices.py
factor_research/neutralization.py
scripts/run_factor_research_v3.py
```

默认运行：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --output-dir outputs\factor_research_v3\liquid2000_core
```

默认研究对象：

```text
market: all_stock_shsz_liquid2000
label: label_20d_t1
factors: amplitude_20,std_20,rev_5,ret_20,amount_mean_20
windows:
  main_research_2021_2023
  recent_oos_2024_2026
```

新增输出：

```text
outputs/factor_research_v3/liquid2000_core/factor_preprocess_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_neutralized_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_neutralized_group_return.csv
outputs/factor_research_v3/liquid2000_core/factor_neutralized_group_return_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_neutralized_correlation.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_ic.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_group_return.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_group_return_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_exposure_correlation.csv
outputs/factor_research_v3/liquid2000_core/factor_candidate_changelog.csv
outputs/factor_research_v3/liquid2000_core/factor_research_v3_report.md
```

首轮关键发现：

- `amplitude_20` raw directional Rank IC 约 `0.1099`，仍是最强基础因子。
- `amplitude_20` 在流动性桶内标准化后降至约 `0.0853`。
- `amplitude_20` 在波动率桶内标准化后降至约 `0.0467`。
- `amplitude_20` 在成交额代理残差中性化后降至约 `0.0761`。
- `amplitude_20` 在流动性、波动率、成交额代理联合残差中性化后降至约 `0.0050`。
- `amplitude_20` 与 `std_20` 的 Spearman 暴露相关性约 `0.90+`，两者高度冗余。
- `rev_5` 在成交额代理残差中性化后有所增强，但仍未达到强 promote 级别。

解释：

- `amplitude_20` 更像“低波动 + 流动性/成交额暴露”的综合风险信号，而不是干净独立 alpha。
- 这不代表它不能用于组合，但后续不能把它简单当成模型特征的独立 alpha；需要作为风险/风格约束对象继续研究。
- `std_20` 继续维持冗余因子判断。
- 下一步仍不应训练新模型，应先扩展风险/流动性分层解释，并研究更稳健的低波动定义。

## 26. 因子研究 V3.1 工具链修正

状态：代码链路已完成，当前 coverage contract blocked。

新增计划文档：

```text
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_V3_1_PLAN.md
docs/PROJECT_CONTEXT_SUMMARY.md
```

V3.1 继续遵循“先参考开源、再最小实现”的原则：

- `alphalens-reloaded`：继续对齐 IC、Rank IC、ICIR、分组收益的评价口径。
- `jqfactor_analyzer`：参考 A 股单因子分析中“预处理 -> 中性化 -> 指标汇总 -> tear sheet”的组织方式。
- `FactorTest`：参考暴露相关性、分层检验与中性化前后对照。
- `microsoft/qlib`：保持数据读取、股票池、Qlib baseline 主线不被替换。

本轮修正目标：

1. 新增 `directional_rank_icir`，避免负向因子的原始 `rank_icir` 被误读。
2. 将 `market_state` 从未来 label 均值切片改为过去 20 日可观测市场状态切片，减少前视风险。
3. 增加 `--write-detail`，默认不写大体积分组收益明细 CSV，只写 summary/report/changelog/correlation/exposure。
4. 新增 `factor_exposure_report.md`，用暴露相关性和中性化变化解释因子是否更像风险/流动性暴露。

默认运行仍为：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --output-dir outputs\factor_research_v3\liquid2000_core
```

如需写出大明细文件，显式加：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --write-detail
```

V3.1 默认输出将包含：

```text
outputs/factor_research_v3/liquid2000_core/factor_exposure_report.md
outputs/factor_research_v3/liquid2000_core/factor_neutralized_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_neutralized_group_return_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_ic.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_group_return_summary.csv
```

## 27. 因子研究 V3.2 性能优化

状态：已完成第一轮。

profile 结论：

- smoke 运行约 `50s` 时，约 `43s` 花在 Qlib `D.features` 原始特征读取。
- 后续 IC、分组收益、中性化和报告计算不是当前最大瓶颈。
- 因此优先优化“重复读取 Qlib 特征面板”，而不是先重写指标算法。

新增优化：

1. `FactorResearchConfig` 支持 `feature_cache_dir` 和 `refresh_feature_cache`。
2. `scripts/run_factor_research_v3.py` 默认使用：

```text
tmp/factor_feature_cache
tmp/factor_frame_cache
```

3. 同一组 `provider_uri + market + start/end + BASE_FIELDS` 会缓存成本地 raw feature pickle。
4. 同一组 `provider_uri + market + start/end + basic_factor_version` 会缓存已计算基础因子和 label 的 frame。
5. 新增参数：

```powershell
--refresh-feature-cache
--no-feature-cache
--feature-cache-dir tmp\factor_feature_cache
--refresh-factor-cache
--no-factor-cache
--factor-cache-dir tmp\factor_frame_cache
```

验证结果：

```text
smoke no cache / original profile: about 50.4s
smoke refresh raw feature cache:   about 40.5s
smoke raw feature cache hit:       about 11.5s-12.2s
smoke basic factor cache hit:      about 9.9s
```

缓存刷新版与缓存命中版的 `factor_neutralized_summary.csv`、`factor_slice_ic.csv` 对比一致。

使用建议：

- 日常调试和重复跑同一窗口时使用默认缓存。
- 更新 Qlib 数据、股票池或基础字段后，加 `--refresh-feature-cache --refresh-factor-cache`。
- 只修改基础因子计算逻辑后，加 `--refresh-factor-cache`。
- 需要完全排查数据读取问题时，加 `--no-feature-cache --no-factor-cache`。

下一轮性能重点：

- 对默认全量窗口建立缓存后，评估中性化和切片诊断的新热点。
- 将 IC、group return、slice diagnostics 的中间结果做可选缓存。
- 在不改变指标口径的前提下，再考虑更深的向量化或并行化。

## 28. 因子筛选 V3.3

状态：已完成最小实现。

新增计划文档：

```text
docs/_archive/03_factor_research_history/FACTOR_SCREENING_V3_3_PLAN.md
```

本阶段目标：

- 不重算 Qlib 数据和基础因子。
- 直接消费 factor research V3 输出。
- 将因子研究指标转成可解释的候选池状态。
- 在后续组合回测前，先给出 `reject / watch / research_candidate / portfolio_test_candidate / risk_exposure / redundant` 判断。

新增模块：

```text
factor_research/screening_v3.py
scripts/run_factor_screening_v3.py
```

默认运行：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_screening_v3.py
```

默认输入：

```text
outputs/factor_research_v3/liquid2000_core
```

默认输出：

```text
outputs/factor_screening_v3/liquid2000_core/factor_candidate_board.csv
outputs/factor_screening_v3/liquid2000_core/factor_screening_report.md
```

当前筛选结果：

```text
rev_5          -> research_candidate
amplitude_20   -> risk_exposure
std_20         -> risk_exposure
ret_20         -> watch
amount_mean_20 -> watch
```

解释：

- `rev_5` 主窗口 directional Rank IC 约 `0.0196`，OOS 约 `0.0352`，残差保留率较高，但强度仍不足以直接进入组合测试。
- `amplitude_20` raw directional Rank IC 较强，但联合中性化后保留率约 `0.045`，被判定为风险/波动率暴露。
- `std_20` 与 `amplitude_20` 高度相关，联合中性化后信号为负，继续作为风险暴露处理。
- `ret_20` 和 `amount_mean_20` 当前方向未定义，保留观察。

## 29. 因子候选池 V3.4

状态：已完成最小实现。

新增计划文档：

```text
docs/_archive/03_factor_research_history/FACTOR_CANDIDATE_POOL_V3_4_PLAN.md
```

本阶段目标：

- 不重算因子或指标。
- 直接消费 V3.3 `factor_candidate_board.csv`。
- 把筛选状态转成可被后续组合回测读取的候选池角色。
- 输出 CSV、JSON 和 Markdown 报告。

新增模块：

```text
factor_research/candidate_pool_v3.py
scripts/run_factor_candidate_pool_v3.py
```

默认运行：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_candidate_pool_v3.py
```

默认输出：

```text
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.csv
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.json
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool_report.md
```

当前候选池角色：

```text
rev_5          -> alpha_candidate
amplitude_20   -> risk_control
std_20         -> risk_control
ret_20         -> monitor
amount_mean_20 -> monitor
```

解释：

- `rev_5` 是当前唯一 alpha 候选，但仍是 `research_candidate` 级别，不是直接上组合的强信号。
- `amplitude_20` 和 `std_20` 不再作为干净 alpha 推进，而是进入风险控制/暴露解释角色。
- 下一步可以围绕 `rev_5` 扩展一小批反转/量价参考因子，并继续走 research -> screening -> candidate pool 的闭环。

## 30. 因子扩展 V3.5 开源参考调研

状态：已完成第一轮参考仓库克隆和 license 调研。

新增文档：

```text
docs/_archive/03_factor_research_history/FACTOR_EXPANSION_V3_5_REFERENCE_SURVEY.md
```

新增克隆到本地忽略目录的参考仓库：

```text
tmp/reference_repos/ta
tmp/reference_repos/KunQuant
tmp/reference_repos/Ginkgo_Alpha101
```

调研结论：

- `bukosabino/ta`：MIT license，适合作为轻量技术指标公式参考，尤其是 volatility、volume、momentum 类指标。
- `microsoft/qlib`：继续作为最重要公式参考，Alpha158 中的 `Ref`、`Mean`、`Std`、`Max`、`Min`、`Corr` 等表达式与本项目数据主线最一致。
- `Menooker/KunQuant`：Apache-2.0，适合作为未来表达式引擎和性能优化参考，但当前接入成本过高，暂不进入主线。
- `Kaoruha/Ginkgo_Alpha101`：MIT license，但当前仓库几乎没有可复用因子实现，暂不采用。

V3.5 下一步建议实现的小批量因子：

```text
downside_std_20
max_drawdown_20
rev_20_exclude_5
amount_cv_20
corr_ret_amount_20
```

实现策略：

- 不 vendor 外部代码。
- 不新增硬依赖。
- 公式参考 Qlib/ta，代码先保持在本项目 `factor_research/factor_library.py` 和 `factor_research/registry.py` 内。
- 输出使用 expanded 目录，避免覆盖 core 基线。

## 31. 因子扩展 V3.5 最小实现

状态：已完成。

新增实施文档：

```text
docs/_archive/03_factor_research_history/FACTOR_EXPANSION_V3_5_IMPLEMENTATION.md
```

新增因子：

```text
downside_std_20
max_drawdown_20
rev_20_exclude_5
amount_cv_20
corr_ret_amount_20
```

新增/更新模块：

```text
factor_research/factor_library.py
factor_research/registry.py
scripts/run_factor_research_v3.py
factor_research/screening_v3.py
factor_research/candidate_pool_v3.py
```

Expanded 输出：

```text
outputs/factor_research_v3/liquid2000_expanded
outputs/factor_screening_v3/liquid2000_expanded
outputs/factor_candidate_pool_v3/liquid2000_expanded
```

当前 expanded 候选池：

```text
rev_20_exclude_5    -> alpha_candidate
rev_5               -> alpha_candidate
amplitude_20        -> risk_control
std_20              -> risk_control
downside_std_20     -> risk_control
max_drawdown_20     -> monitor
amount_cv_20        -> monitor
ret_20              -> monitor
amount_mean_20      -> monitor
corr_ret_amount_20  -> monitor
```

关键发现：

- `rev_20_exclude_5` 成为当前最强新增 alpha 候选，主窗口 directional Rank IC 约 `0.0538`，OOS 约 `0.0590`。
- `rev_5` 继续保留为 alpha 候选。
- `downside_std_20` raw 表现较强，但主要是波动率/风险暴露，进入 `risk_control`。
- `max_drawdown_20` raw/OOS 有一定信号，但联合中性化后翻负，进入 `monitor`。
- `amount_cv_20` OOS 表现较好，但当前证据不足，继续观察。

筛选规则修正：

- 新增规则：`joint_residual_directional_rank_ic < 0` 时，不允许进入 alpha 候选，状态设为 `watch`，原因 `signal_flips_after_controls`。

## 32. V3.6 路线修正：开源评价体系并行复现

状态：已规划，暂未实施。

详细计划：

```text
docs/_archive/03_factor_research_history/FACTOR_EVALUATION_OPEN_SOURCE_COEXISTENCE_PLAN.md
```

路线修正：

- 暂停继续围绕少量常见因子做策略层验证。
- 先补齐因子评价和筛选工具体系，再进入大规模因子池扩张。
- 不急于自研统一评价分数，先让多个成熟开源评价体系并行输出。
- 评价逻辑优先照搬或直接调用开源项目，并标明来源、commit、license、函数位置。
- 本项目只负责 Qlib 数据适配、`data_quality`/`tradability` 前置过滤、输出汇总和后续主观判断层。

优先复现的评价来源：

```text
alphalens-reloaded
jqfactor_analyzer
Qlib evaluate/risk_analysis
current project factor_research
```

后续因子池来源：

```text
Qlib Alpha158 / Alpha360
ta
KunQuant / Ginkgo_Alpha101
FactorTest / multi-factor
```

V3.6 目标：

- 多个开源评价体系结果先共存，不强行合并。
- 输出 Alphalens 风格、jqfactor 风格、Qlib 风格和本项目当前风格的并列结果。
- 增加 provider 字段探测，确认行业、市值、指数成分、ST、停牌、涨跌停等数据可用性。
- 建立 `factor_catalog.yaml`，为后续批量扩张因子池记录来源、公式、依赖字段和 license。
- 等开源评价体系跑通后，再新增本项目自己的 judgement layer。

## 33. V3.6 第一段：来源清单与适配层骨架

状态：已完成。

新增文件：

```text
factor_research/external/__init__.py
factor_research/external/source_manifest.yaml
factor_research/external/adapters.py
docs/_archive/03_factor_research_history/FACTOR_EVALUATION_SOURCE_MANIFEST.md
```

完成内容：

- 记录 Alphalens、jqfactor、Qlib evaluate、qlib_factor_platform、ta、KunQuant、Ginkgo_Alpha101、FactorTest、multi-factor 的来源、commit、license、计划用途和复用边界。
- 新增外部评价适配层，当前只做数据转换，不计算任何评价指标。
- 支持导出 Alphalens 风格 `(date, asset)` MultiIndex factor data。
- 支持导出 jqfactor 风格 factor、forward returns、groupby、weights 对齐对象。
- 支持导出 Qlib 风格 score/label frame。
- 小样本验证通过，确认 adapter 输出形状符合预期。

下一段：

- 增加 `scripts/run_factor_evaluation_v4.py`，用少量已存在因子导出多体系输入样本、adapter report 和 failure reasons。
- 然后再调用外部评价函数生成并列结果。

## 34. V3.6 第二段：开源评价体系 Smoke Test

状态：已完成第一轮。

新增文件：

```text
scripts/run_factor_evaluation_v4.py
docs/_archive/03_factor_research_history/FACTOR_EVALUATION_V4_SMOKE_TEST.md
requirements-factor-evaluation.txt
```

输出目录：

```text
outputs/factor_evaluation_v4/liquid2000_open_source_eval/
```

测试范围：

```text
window: main_research_2021_2023
raw rows: 1,414,832
tradable rows: 824,291
labels: label_10d_t1,label_20d_t1
factors: rev_5,rev_20_exclude_5,std_20,amount_mean_20,downside_std_20
```

结论：

- Alphalens Reloaded 核心 `performance.py` 评价函数已跑通，能输出 IC、mean IC、分组收益、factor returns、alpha/beta、换手率和 rank autocorrelation。
- jqfactor_analyzer 部分跑通，能输出 IC、mean IC、分组收益和换手率。
- jqfactor_analyzer 的 `factor_returns` 和 `factor_alpha_beta` 在当前 pandas 2.x 环境下触发 MultiIndex 兼容问题：`The name date occurs multiple times, use a level number`。
- Qlib evaluate 路径跑通，已输出每日 Rank IC 与 Qlib `risk_analysis`。
- 当前项目 V3 输出已复制到 V4 coexistence 目录，便于并列比较。

重要实现细节：

- 不执行 `alphalens.__init__` 和 `jqfactor_analyzer.__init__`，避免引入 plotting、UI、数据 API 等非评价依赖。
- 直接加载参考项目的 `performance.py` 及必要相对依赖，保持评价函数源码不被改写。
- Alphalens 使用 `10D`/`20D` 周期列；jqfactor 使用 `period_10`/`period_20` 周期列。

下一段：

- 增加 evaluator config，避免参数硬编码在 runner 中。
- 增加运行前依赖检查。
- 决定 jqfactor 兼容策略：要么使用兼容 pandas 环境复现，要么 vendor 并显式标注兼容补丁。
- 在不自研综合分数的前提下，生成一个 open-source output leaderboard，仅做结果索引和成功/失败摘要。

## 35. V3.6 第三段：配置化、依赖检查与结果索引

状态：已完成。

新增文件：

```text
configs/factor_evaluation_v4.yaml
factor_research/external/summary.py
```

更新文件：

```text
scripts/run_factor_evaluation_v4.py
docs/_archive/03_factor_research_history/FACTOR_EVALUATION_V4_SMOKE_TEST.md
```

新增能力：

- runner 支持 `--config configs/factor_evaluation_v4.yaml`，统一配置 provider、市场、窗口、因子、标签、评价体系、可交易性过滤和缓存。
- 运行前输出 `dependency_status.csv`，检查 Python 依赖和外部评价源码文件。
- 输出 `evaluator_status.csv`，逐体系、逐因子记录 `pass`、`partial_pass`、`failed` 或 `not_run`。
- 输出 `open_source_metric_index.csv`，把各开源体系的主要结果整理成长表索引。
- 指标索引不包含综合分、主观权重或自动排序，不改变“多体系先共存”的原则。

本轮完整运行结果：

```text
Alphalens Reloaded: 5 pass
jqfactor_analyzer: 5 partial_pass
Qlib evaluate: 5 pass
current project: 5 pass
open_source_metric_index: 90 rows
```

下一段建议：

- 为 jqfactor 的 pandas 2.x 兼容问题做隔离实验，不直接改原始函数。
- 增加 provider 字段探测，确认行业、市值、指数成分等数据是否足以启动分组/中性化评价。
- 完成数据能力清单后，再开始大规模扩张因子池。

## 36. V3.6 第四段：Provider 数据能力清单

状态：已完成。

新增文件：

```text
scripts/inspect_provider_fields.py
docs/_archive/02_data_layer_history/PROVIDER_DATA_CAPABILITY_V3_6.md
```

输出目录：

```text
outputs/data_inventory/provider_v3_6/
```

自动检查结果：

- provider 有 `6,106` 个 feature instrument。
- `open/high/low/close/volume/amount/vwap/change/factor/adjclose` 在 6,106 个 instrument 目录中均存在。
- 三只样本股在 2021-2023 的实际读取结果中，上述测试字段覆盖率均为 100%。
- CSI300、CSI500、CSI800、CSI1000、csiall 等 point-in-time 成分文件可用。
- CSI300、CSI500、CSI1000 基准指数特征目录可用。
- instrument start/end interval 可用，可派生上市天数和 point-in-time eligibility。
- 行业分类、市值/流通市值、基本面和分析师数据当前不可用，需要外部数据源。

路线影响：

- 价量、技术、波动率、流动性、Alpha158/Alpha360/Alpha101 因子可以开始批量扩张。
- 多股票池一致性、基准相对评价和上市年龄切片可以直接建设。
- 行业 IC、行业中性、市值中性和市值加权分组暂不能启用。
- 基本面因子池继续等待独立数据源与 license 决策。

下一段建议：

- 先增加 benchmark、universe membership 和 listing age 三个现有数据 adapter。
- 同时调研 point-in-time 行业和市值开源数据源。
- adapter 完成后，开始首批大规模价量/技术因子注册与批量筛选。

## 37. V3.7 第一段：时点正确的因子研究上下文

状态：已完成。

新增文件：

```text
configs/factor_context_v1.yaml
factor_research/context/__init__.py
factor_research/context/benchmark.py
factor_research/context/listing.py
factor_research/context/universe.py
scripts/build_factor_context_v1.py
scripts/validate_factor_context_v1.py
docs/_archive/03_factor_research_history/FACTOR_CONTEXT_V1.md
```

输出目录：

```text
outputs/factor_context_v1/main_research_2021_2023/
```

完成能力：

- 基于 Qlib instrument start/end 区间生成 point-in-time CSI300、CSI500、CSI1000 和 liquid2000 成员统计与末日快照。
- 基于 provider 最早可用区间生成上市年龄代理和年龄分组，并明确记录历史左截断限制。
- 基于 Qlib 指数特征生成 CSI300、CSI500、CSI1000 日收益及 T+1 口径 10/20 日前瞻收益。
- 新增独立验证器，检查区间端点、收益公式、重复键、末日成员数和上市年龄一致性。
- 保持 `data_quality -> tradability -> factor evaluation` 前置约束不变，不把上下文模块发展成另一条数据主线。

本轮结果：

```text
benchmark trading days: 727 each
csi300 members: 300 each day
csi500 members: 500 each day
csi1000 members: 1000 each day
liquid2000 members: 1904 to 1977
listing-age snapshot instruments: 5096
```

下一段：

- 将 context V1 接入 V4 evaluator，使股票池切片、上市年龄切片和基准相对评价进入同一次可复现运行。
- 保持 Alphalens、jqfactor、Qlib evaluate 和当前项目评价结果并列，不引入自研综合评分。
- 并行调研 point-in-time 行业和市值数据源，但在 license 与时点语义确认前不写中性化实现。

## 38. V3.7 第二段：上下文接入开源评价体系

状态：已完成实现、单因子 smoke 和五因子全量回归。

新增文件：

```text
configs/factor_evaluation_v4_context_smoke.yaml
factor_research/context/evaluation.py
scripts/validate_factor_evaluation_context.py
```

更新文件：

```text
configs/factor_evaluation_v4.yaml
factor_research/external/adapters.py
scripts/run_factor_evaluation_v4.py
docs/_archive/03_factor_research_history/FACTOR_CONTEXT_V1.md
```

实现原则：

- 上下文层只负责 point-in-time 数据对齐，不重写评价指标。
- 分组 IC、平均 IC 和分组收益直接调用 Alphalens Reloaded 与 jqfactor_analyzer 的 `by_group=True` 实现。
- 原始收益与基准超额收益分目录共存，不合成项目自定义评分。
- jqfactor 输入按其 `prepare.get_clean_factor` 原始语义先清理缺失值，再按日期和分位数组归一化权重。
- 少于两个有效取值的分组维度标记为 `skipped_non_informative`，不生成误导性结果。

单因子 smoke 结果：

```text
factor: rev_5
tradable rows: 824291
index segments: csi300, csi500, csi1000, outside_major_indices
Alphalens grouped context steps: 6 pass
jqfactor grouped context steps: 6 pass
listing_age_bucket: skipped_non_informative
context failures: 0
```

五因子全量回归：

```text
runtime: 398 seconds
complete date/instrument rows per factor: 820580
grouped context steps passed: 60
listing-age checks skipped_non_informative: 20
context failures: 0
context_metric_index rows: 960
```

自动验证包括：

- 成分重叠和上市年龄缺失必须为 0；
- 分组收益不得为空或部分缺失；
- Alphalens 与 jqfactor 的逐日分组 Rank IC 必须一致；
- 同一分组内减去相同基准收益后，Rank IC 必须保持不变。

下一段：

- 为批量扩张增加按因子复用清洗输入、可恢复任务和运行清单，避免把 398 秒线性放大到上百因子。
- 调研并冻结第一批 Alpha158、Alpha101 和 `ta` 因子来源清单、license、字段依赖与公式校验样本。
- 工具链具备批处理与失败恢复后，开始首批大规模价量/技术因子注册和批量筛选。

## 39. V3.8 第一段：因子目录与批量评估编排

状态：已完成最小实现。

新增文件：

```text
configs/factor_evaluation_batch_v1.yaml
configs/factor_evaluation_batch_v1_smoke.yaml
factor_research/catalog.py
factor_research/factor_catalog.yaml
scripts/run_factor_evaluation_batch_v1.py
docs/_archive/03_factor_research_history/FACTOR_BATCH_EVALUATION_V1.md
```

实现目标：

- 建立 `factor_catalog.yaml`，统一记录因子名称、类别、来源项目、来源文件、函数、commit/license、字段依赖、方向假设、标签周期、是否可运行和计算 adapter。
- 将当前已经接入 registry 的 15 个基础价量因子登记为可运行因子。
- 将 Qlib Alpha158、qlib_factor_platform presets、`ta`、KunQuant Alpha101、Ginkgo Alpha101 登记为后续扩张来源，但在 adapter 和公式审计完成前不自动运行。
- 新增批量 runner，从 catalog 选择因子，生成每个 batch 的 V4 配置，并记录 manifest、日志、catalog snapshot、registry 对齐检查和输出摘要。
- 支持 `--dry-run`，用于在不执行耗时 V4 评价的情况下验证批量编排。
- 支持简单断点续跑：当 batch 已存在 `evaluator_status.csv`、`open_source_metric_index.csv` 和 `factor_evaluation_v4_report.md` 时跳过。

最小验证命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_smoke.yaml --dry-run
```

验证输出：

```text
outputs/factor_evaluation_batch_v1/smoke_dry_run/
```

本段边界：

- 不新增评价指标，不改 Alphalens Reloaded 或 jqfactor_analyzer 指标口径。
- 不训练新模型。
- 不直接运行未审计的 Alpha158/TA/Alpha101 因子。
- 不绕过 `data_quality -> tradability -> factor evaluation` 前置约束。

下一段：

- 为 Qlib Alpha158 增加表达式读取与字段审计，把首批 Alpha158 因子转成 catalog entries。
- 对每个新增来源先做 `--dry-run` 和小 batch smoke，再进入完整批量评价。
- 如果批量运行时间成为瓶颈，再考虑复用 V4 清洗后的中间输入，而不是先做并发优化。

## 40. V3.8 第二段：Qlib Alpha158 来源审计

状态：已完成公式抽取、字段审计和首批 metadata catalog。

新增文件：

```text
configs/factor_evaluation_batch_v1_alpha158_metadata_smoke.yaml
factor_research/qlib_alpha158.py
scripts/audit_alpha158_catalog_v1.py
docs/_archive/04_alpha158_history/ALPHA158_CATALOG_AUDIT_V1.md
```

输出目录：

```text
outputs/factor_catalog_alpha158_v1/
```

完成能力：

- 直接从本地 Qlib 源码 `Alpha158DL.get_feature_config()` 抽取 158 个 Alpha158 表达式，避免手写公式。
- 记录 Qlib source commit、source file、source function 和 license。
- 扫描当前 derived provider 的真实 feature 文件，检查 Alpha158 所需字段是否可用。
- 生成 `alpha158_formula_inventory.csv`、`alpha158_field_usage.csv`、`alpha158_catalog_all.yaml` 和 `alpha158_catalog_first_batch.yaml`。
- 为 batch runner 增加防护：`runnable: false` 的 metadata 条目只能 `--dry-run`，不能误触发真实 V4 评价。

本轮结果：

```text
Alpha158 formulas: 158
field_status=available: 158
field_status=missing: 0
first batch metadata entries: 20
```

字段使用：

```text
close: 117 formulas
high: 28 formulas
low: 28 formulas
open: 9 formulas
volume: 40 formulas
vwap: 1 formula
```

首批 metadata dry-run：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_metadata_smoke.yaml --dry-run
```

重要边界：

- Alpha158 条目当前仍是 `enabled: false`、`runnable: false`。
- 字段审计通过不等于因子评价通过。
- 在 Qlib expression adapter 完成前，不把 Alpha158 放入正式筛选。

下一段：

- 实现 Qlib expression adapter，从 catalog/inventory 读取表达式并用 `D.features` 计算首批 Alpha158 因子。
- 将表达式结果与现有 T+1 labels、data_quality、tradability 过滤对齐。
- 对首批 20 个 Alpha158 因子跑 V4 smoke，并通过 context validator 后再改为 runnable。

## 41. V3.9：Alpha158 表达式接入与首批真实评价

状态：已完成。

阶段计划文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_EXPRESSION_EVALUATION_STAGE_PLAN.md
docs/_archive/04_alpha158_history/ALPHA158_EXPRESSION_ADAPTER_V1.md
```

本阶段完成内容：

- 实现 Qlib expression adapter，直接使用 Qlib Alpha158 原始表达式计算首批因子。
- 将 expression frame 与现有基础 frame、T+1 labels、data_quality 和 tradability 输出对齐。
- 扩展 V4 evaluator 支持外部预计算 factor frame 和 catalog-derived FactorSpec。
- 对 5 个 Alpha158 因子跑极小 smoke，对首批 20 个因子跑完整 V4 first20 smoke。
- 用 batch runner 完成首批 20 个因子的 4 批断点续跑验证。
- smoke 与 validation 通过后，将对应 Alpha158 catalog 条目单独晋升为 `enabled: true`、`runnable: true`。

新增文件：

```text
configs/alpha158_expression_adapter_v1.yaml
configs/factor_evaluation_v4_alpha158_smoke5.yaml
configs/factor_evaluation_v4_alpha158_first20.yaml
configs/factor_evaluation_v4_alpha158_batch_base.yaml
configs/factor_evaluation_batch_v1_alpha158_first20.yaml
factor_research/expression_adapter.py
factor_research/alpha158_registry.py
scripts/build_alpha158_expression_frame_v1.py
scripts/validate_alpha158_expression_frame_v1.py
scripts/promote_alpha158_catalog_entries_v1.py
scripts/summarize_alpha158_first20.py
```

关键输出：

```text
outputs/alpha158_expression_frame_v1/first20_main_research/
outputs/factor_evaluation_v4/alpha158_first20_smoke/
outputs/factor_evaluation_batch_v1/alpha158_first20/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml
```

本轮验证结果：

```text
expression frame rows: 1,603,860
factor count: 20
adapter validation: pass
KMID manual max_abs_error: 0.0
KLEN manual max_abs_error: 0.0
Alphalens Reloaded: pass 20
jqfactor_analyzer: partial_pass 20
Qlib eval: pass 20
context: pass 240, skipped_non_informative 80
combined metric index rows: 4,200
batch count: 4
```

断点续跑验证：

```text
batch_001: skipped_existing
batch_002: skipped_existing
batch_003: skipped_existing
batch_004: pass
```

说明：电脑断电后重新运行 batch runner，前三批已完整产出的 batch 被识别并跳过，只补跑第四批，符合本阶段“可恢复批量运行”的目标。

本阶段保留边界：

- 不重写 Alpha158 公式。
- 不新增自研综合评分。
- 不训练新模型。
- 不直接扩到 Alpha158 全量 158 个因子。
- 不绕过已有数据诊断和可交易性约束。

下一段建议：

- 将同样的 adapter、validation、V4 和 batch promotion 流程扩展到 Alpha158 全量 158 个因子。
- 扩容时继续保留小批量 smoke、断点续跑和 compact summary，避免一次性生成不可维护的大量明细。
- Alpha158 全量跑通后，再考虑 `ta` 技术指标和 Alpha101 来源审计。
- 等因子池有足够候选后，再进入筛选 judgement layer 和组合回测接口。

## 42. V3.10：Alpha158 全量扩张启动

状态：已完成 full158 expression frame、remaining138 全量 batch、context validation、strict promotion 和 compact summary。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_FULL_EVALUATION_STAGE_PLAN.md
```

新增文件：

```text
configs/alpha158_expression_adapter_full_v1.yaml
configs/factor_evaluation_v4_alpha158_remaining_batch_base.yaml
configs/factor_evaluation_batch_v1_alpha158_remaining138.yaml
scripts/prepare_alpha158_full_stage_catalogs_v1.py
```

关键输出：

```text
outputs/alpha158_expression_frame_v1/full158_main_research/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_pending.yaml
outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_mixed.yaml
outputs/factor_evaluation_batch_v1/alpha158_remaining138/
```

完成结果：

```text
remaining138 pending catalog: 138 factors
full158 mixed catalog: 158 factors
full158 expression frame rows: 1,603,860
full158 expression factors: 158
full158 expression validation: pass
coverage min: 0.994231
coverage median: 0.996867
remaining138 dry-run batches: 14
remaining138 batch status: 13 pass, 1 skipped_existing
batch_001 elapsed: 912.061 seconds
remaining138 open-source metric rows: 2,484
remaining138 context metric rows: 26,464
remaining138 combined metric index rows: 28,948
remaining138 strict runnable: 135
remaining138 holdout: 3
full strict runnable: 155
```

remaining138 评价状态：

```text
alphalens_reloaded: pass 135, partial_pass 3
jqfactor_analyzer: partial_pass 138
qlib_eval: pass 138
context: pass 1656, skipped_non_informative 552
context validation: pass for all 14 batches
holdout: alpha158_CNTN5, alpha158_IMAX5, alpha158_RANK5
```

工程改进：

- expression adapter 支持 `expression.batch_size` 和 chunk 进度输出。
- batch runner 支持 `--max-batches`，便于先跑少量真实 smoke。
- batch runner 支持显式 `execution.allow_non_runnable_external: true`，只用于外部 adapter 因子的预晋升评价。

下一步：

- 合并 first20 与 remaining138 的 metric index，形成 full Alpha158 筛选输入。
- 保留 holdout 标记，不把 Alphalens turnover 缺失的 3 个因子混入 strict runnable 池。
- 建设筛选看板：覆盖率、缺失率、IC/Rank IC/ICIR、分组收益、换手率、相关性、单调性和多体系共识。
- 在 full Alpha158 工具体系稳定后，再考虑 `ta` 和 Alpha101 来源扩展。

## 43. V3.11：Alpha158 全量筛选输入层

状态：已完成。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_FULL_SCREENING_INPUT_V1.md
```

新增文件：

```text
configs/factor_screening_alpha158_full_v1.yaml
factor_research/alpha158_screening_input.py
scripts/run_alpha158_screening_input_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_screening_input_v1.py --config configs\factor_screening_alpha158_full_v1.yaml
```

关键输出：

```text
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_screening_input.csv
outputs/factor_screening_alpha158_v1/full158/alpha158_full_screening_input_report.md
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_correlation_top_pairs.csv
```

完成结果：

```text
factor board rows: 158
strict_screening_input: 155
holdout: 3
full metric index rows: 33,148
IC summary rows: 948
quantile return summary rows: 632
turnover summary rows: 624
rank autocorrelation summary rows: 474
context IC summary rows: 1,264
context return summary rows: 5,056
correlation used dates: 120
```

本阶段新增能力：

- 合并 first20 与 remaining138 的 metric index。
- 保留 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 三套评价体系状态。
- 从开源输出中抽取 Rank IC、ICIR、分组收益、换手率和 rank autocorrelation。
- 从既有 context/tradability-aware 输出中抽取分组 IC 与分组收益。
- 从 full158 expression frame 计算每日横截面 Spearman 因子相关性，标记最强相关因子和 Top pairs。
- 将 `alpha158_CNTN5`、`alpha158_IMAX5`、`alpha158_RANK5` 继续保留为 holdout。

边界：

- 不新增综合评分。
- 不把 holdout 因子混入 strict screening input。
- 不训练模型，不做实盘，不改 Qlib baseline。

下一步：

- 在 `alpha158_factor_screening_input.csv` 之上建设 judgement layer。
- 先输出候选分层和冗余簇，而不是立刻扩张更多因子。
- 等筛选层可解释且稳定后，再启动 `ta` 和 Alpha101 来源审计与批量接入。

## 44. V3.12：Alpha158 Judgement Layer 与冗余簇

状态：已完成。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_JUDGEMENT_LAYER_V1.md
```

新增文件：

```text
configs/factor_judgement_alpha158_v1.yaml
factor_research/alpha158_judgement.py
scripts/run_alpha158_judgement_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_judgement_v1.py --config configs\factor_judgement_alpha158_v1.yaml
```

关键输出：

```text
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_board.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_redundancy_clusters.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_redundancy_cluster_members.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_report.md
```

完成结果：

```text
judgement board rows: 158
redundancy clusters: 23
cluster members: 78

strong_signal: 10
consistent_signal: 4
redundant: 55
high_turnover: 33
unstable_context: 16
review: 33
weak_signal: 4
holdout: 3
```

本阶段新增能力：

- 在不生成综合分的前提下，为 Alpha158 因子生成可解释规则标签。
- 保留 `signal_label` 和 `judgement_label` 两层结果，区分原始信号强弱与交易/稳定性/冗余问题。
- 根据每日横截面 Spearman 相关性生成 redundancy clusters。
- 每个冗余簇按可读规则选择代表因子：signal label、issue flags、方向一致性、Rank IC、ICIR、换手率、覆盖率、因子名。
- 继续把 `alpha158_CNTN5`、`alpha158_IMAX5`、`alpha158_RANK5` 保留为 holdout。

边界：

- 不修改开源评价体系。
- 不用 judgement label 替代原始指标。
- 不训练模型，不做实盘。

下一步：

- 基于 `alpha158_judgement_board.csv` 冻结 Alpha158 candidate pool v1。
- 优先纳入 `strong_signal` 和 `consistent_signal`。
- 保留每个 redundancy cluster 的代表因子，排除非代表冗余因子。
- 暂时排除 `holdout`、`weak_signal`、`review`、`high_turnover`、`unstable_context`。
- candidate pool 冻结后，再进入小规模组合回测接口；之后才适合扩展 `ta` 和 Alpha101。

## 45. V3.13：Alpha158 Candidate Pool V1

状态：已完成。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_CANDIDATE_POOL_V1.md
```

新增文件：

```text
configs/factor_candidate_pool_alpha158_v1.yaml
factor_research/alpha158_candidate_pool.py
scripts/run_alpha158_candidate_pool_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_pool_v1.py --config configs\factor_candidate_pool_alpha158_v1.yaml
```

关键输出：

```text
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.json
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool_report.md
```

完成结果：

```text
candidate pool rows: 158
alpha_candidate: 14
excluded_redundant: 55
excluded_high_turnover: 33
excluded_unstable_context: 16
monitor: 37
holdout: 3
```

当前 `alpha_candidate`：

```text
alpha158_MIN60
alpha158_QTLD60
alpha158_ROC60
alpha158_MIN30
alpha158_ROC30
alpha158_QTLD30
alpha158_IMIN60
alpha158_MIN10
alpha158_IMIN30
alpha158_MIN5
alpha158_IMIN20
alpha158_QTLD10
alpha158_VSUMN60
alpha158_ROC10
```

本阶段新增能力：

- 将 Alpha158 judgement board 冻结为完整角色表和下游 alpha candidate 子集。
- 保留每个因子的排除原因、warning、冗余簇、代表因子和原始 judgement label。
- 将 `low_monotonicity` 作为 warning 保留，不在 V1 中单独剔除。
- 继续排除 holdout、非代表冗余因子、high turnover 和 unstable context 因子。

边界：

- 不训练模型。
- 不调具体策略参数。
- 不新增自研综合分。
- 不替换开源评价结果。

下一步：

- 进入 V3.14 Alpha158 Candidate Portfolio Smoke。
- 只消费 `alpha158_alpha_candidates.csv` 作为默认 alpha 输入。
- 构建低频、可复现、带交易约束的组合 smoke，用于检查候选池接口是否可用。
- 报告必须显式标记 `low_monotonicity` warning 和 holdout 排除原因。

## 46. V3.14：Alpha158 Candidate Portfolio Smoke V1

状态：已完成。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_CANDIDATE_PORTFOLIO_SMOKE_V1.md
```

新增文件：

```text
configs/alpha158_candidate_portfolio_smoke_v1.yaml
factor_research/alpha158_portfolio_smoke.py
scripts/run_alpha158_candidate_portfolio_smoke_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_v1.yaml
```

关键输出：

```text
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/summary.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/daily_returns.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/rebalance_summary.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/positions.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/candidate_weight_table.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/score_component_summary.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/alpha158_candidate_portfolio_smoke_report.md
```

完成结果：

```text
candidate_count: 14
warning_low_monotonicity_count: 4
trading_days: 700
rebalance_count: 37
executed_rebalances: 35
positions: 3500
net_annualized_excess: 0.060632
net_excess_ir: 0.552843
average_turnover: 0.824857
net_max_drawdown: -0.321708
```

本阶段新增能力：

- 从冻结后的 `alpha158_alpha_candidates.csv` 读取默认 alpha 输入。
- 按 `equal_directional_zscore` 生成组合 score。
- 使用 Alpha158 expression frame chunk，只抽取候选因子，避免全量重读 158 个因子。
- 继续合并现有 tradability labels，按 `can_buy`、`liquidity_bucket` 和 `tradability_score` 过滤。
- 输出低频换仓、持仓、逐日收益、组件覆盖率和候选权重表。

边界：

- 当前结果是接口 smoke，不是可直接使用的策略结论。
- 不训练模型，不调复杂策略参数。
- 暂不扩展新因子池。

下一步：

- 进入 V3.15 Portfolio Smoke Diagnostics。
- 先做单因子候选对比、换手/容量敏感性、暴露诊断和 recent OOS 衔接。
- 等 portfolio diagnostics 稳定后，再考虑继续扩张 `ta`、Alpha101 或其他开源因子来源。

## 47. V3.15：Alpha158 Portfolio Diagnostics V1

状态：已完成。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_PORTFOLIO_DIAGNOSTICS_V1.md
```

新增文件：

```text
configs/alpha158_portfolio_diagnostics_v1.yaml
factor_research/alpha158_portfolio_diagnostics.py
scripts/run_alpha158_portfolio_diagnostics_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_v1.yaml
```

关键输出：

```text
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/base_summary.csv
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/single_factor_summary.csv
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/topk_sensitivity.csv
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/cost_sensitivity.csv
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/liquidity_bucket_exposure.csv
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/alpha158_portfolio_diagnostics_report.md
```

完成结果：

```text
single_factor rows: 14
topk_sensitivity rows: 3
cost_sensitivity rows: 3
best single factor: alpha158_ROC30
best single factor net_excess_ir: 0.803985
topk_50 net_excess_ir: 0.676352
topk_100 net_excess_ir: 0.552843
topk_200 net_excess_ir: 0.405610
cost_5bps net_excess_ir: 0.596277
cost_10bps net_excess_ir: 0.552843
cost_20bps net_excess_ir: 0.465720
```

本阶段新增能力：

- 单因子候选组合 smoke 对比。
- TopK 50/100/200 敏感性。
- 交易成本 5/10/20 bps 敏感性。
- 基础组合持仓 liquidity bucket 分布。

边界：

- 不改变候选池。
- 不做参数优化。
- 不训练模型。
- 不引入新因子。

下一步：

- 先扩展 Alpha158 expression frame 到 recent OOS，或构建一个只覆盖 2024-2026 的轻量候选因子 expression frame。
- 增加行业、市值、流动性和风格代理暴露诊断。
- 在暴露和 OOS 诊断完成前，不建议直接进入策略优化。

## 48. V3.16：Alpha158 Recent OOS Extension V1

状态：已完成。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_RECENT_OOS_EXTENSION_V1.md
```

新增文件：

```text
configs/alpha158_expression_adapter_candidates_recent_oos_v1.yaml
configs/alpha158_candidate_portfolio_smoke_recent_oos_v1.yaml
configs/alpha158_portfolio_diagnostics_recent_oos_v1.yaml
scripts/validate_alpha158_candidate_expression_frame_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_candidate_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml --candidate-pool outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_recent_oos_v1.yaml
```

关键输出：

```text
outputs/alpha158_expression_frame_v1/candidates_recent_oos_2024_2026/expression_frame_summary.csv
outputs/alpha158_expression_frame_v1/candidates_recent_oos_2024_2026/candidate_expression_validation_report.md
outputs/alpha158_candidate_portfolio_smoke_v1/recent_oos_2024_2026/summary.csv
outputs/alpha158_candidate_portfolio_smoke_v1/recent_oos_2024_2026/alpha158_candidate_portfolio_smoke_report.md
outputs/alpha158_portfolio_diagnostics_v1/recent_oos_2024_2026/alpha158_portfolio_diagnostics_report.md
```

完成结果：

```text
recent OOS expression rows: 1,096,231
candidate factors: 14
min factor coverage: 0.995898
validation: pass
recent OOS trading_days: 560
recent OOS executed_rebalances: 28
recent OOS net_annualized_excess: 0.019804
recent OOS net_excess_ir: 0.221295
recent OOS average_turnover: 0.799286
recent OOS best single factor: alpha158_VSUMN60
recent OOS best single factor net_excess_ir: 0.814553
```

对比 main window：

```text
main topk_100 net_excess_ir: 0.552843
recent OOS topk_100 net_excess_ir: 0.221295
```

本阶段新增能力：

- 只构建 14 个候选因子的 recent OOS expression frame。
- 候选 expression frame 轻量验证。
- recent OOS portfolio smoke。
- recent OOS portfolio diagnostics。

边界：

- 大体积 `factor_frame*.pkl` 不提交。
- 不改候选池。
- 不训练模型。
- 不做策略优化。

下一步：

- 进入 V3.17 Alpha158 Stability And Exposure Diagnostics。
- 比较 main 与 recent OOS 单因子排名稳定性。
- 增加流动性、价格动量、波动率和成交量代理暴露诊断。
- 在稳定性与暴露结论清晰前，不扩大新因子来源。

## 49. V3.17：Alpha158 Stability Diagnostics V1

状态：已完成。

阶段文档：

```text
docs/_archive/04_alpha158_history/ALPHA158_STABILITY_DIAGNOSTICS_V1.md
```

新增文件：

```text
configs/alpha158_stability_diagnostics_v1.yaml
factor_research/alpha158_stability_diagnostics.py
scripts/run_alpha158_stability_diagnostics_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_stability_diagnostics_v1.py --config configs\alpha158_stability_diagnostics_v1.yaml
```

关键输出：

```text
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/single_factor_stability.csv
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/topk_sensitivity_delta.csv
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/cost_sensitivity_delta.csv
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/liquidity_bucket_exposure_delta.csv
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/alpha158_stability_diagnostics_report.md
```

完成结果：

```text
single_factor rows: 14
weak_or_negative_oos: 8
positive_but_weaker_oos: 3
main_only: 2
oos_improved: 1
topk_100 main net_excess_ir: 0.552843
topk_100 recent net_excess_ir: 0.221295
topk_100 delta: -0.331548
bucket_3 exposure share delta: +0.063357
```

本阶段新增能力：

- main vs recent OOS 单因子稳定性标签。
- TopK 敏感性差异。
- 成本敏感性差异。
- liquidity bucket 暴露变化。

边界：

- 不重新计算因子。
- 不调整候选池。
- 不训练模型。
- 不优化策略。

下一步：

- 不再把 Alpha158 细分研究作为下一阶段主线。
- 先建立因子研究工具链 readiness 闸门。
- readiness 通过后，开始接入非 Alpha158 开源因子源，并准备大规模筛选。

## 50. V3.18：Factor Research Toolchain Readiness V1

状态：已完成。

阶段文档：

```text
docs/FACTOR_RESEARCH_TOOLCHAIN_READINESS_V1.md
```

新增文件：

```text
configs/factor_research_toolchain_readiness_v1.yaml
scripts/audit_factor_research_toolchain_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

关键输出：

```text
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_checks.csv
outputs/factor_research_toolchain_readiness_v1/current/source_readiness.csv
outputs/factor_research_toolchain_readiness_v1/current/required_output_contracts.csv
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
```

完成结果：

```text
prefilter_policy: pass
open_source_evaluator_systems: pass
batch_runner: pass
required_output_contracts: pass
runnable_factor_inventory: pass
new_source_adapter_inventory: blocked
generic_multi_source_screening: partial
total_runnable: 170
Alpha158 runnable catalog: 155
Alpha158 holdout catalog: 3
new_source_runnable: 0
```

结论：

- Alpha158 研究链路已可复现，可作为后续多来源研究的参照。
- data_quality 与 tradability 前置过滤约束已经在 catalog 和 source manifest 中声明。
- Alphalens Reloaded、jqfactor_analyzer、Qlib eval、project_current 四套评价体系继续共存。
- 大规模多来源因子研究还不能直接开跑，核心阻塞是非 Alpha158 开源因子源尚无 promoted runnable adapter。

下一步：

- 进入 V3.19：首个非 Alpha158 开源因子源 adapter。
- 首选 `ta`，因为本地参考仓库已存在、license 为 MIT、入口函数清晰。
- 先做源码审计、字段映射、look-ahead 检查、少量 smoke。
- 通过后再登记 runnable catalog entries，并进入 batch V4。
- 同步抽象 multi-source screening / candidate-pool contract，避免后续 TA、Alpha101 和 Alpha158 各走各的筛选路径。

## 51. V3.19：TA Factor Adapter Smoke V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/TA_FACTOR_ADAPTER_SMOKE_V1.md
```

新增文件：

```text
configs/ta_factor_adapter_smoke_v1.yaml
configs/ta_factor_evaluation_smoke_v1.yaml
configs/ta_factor_smoke_promotion_v1.yaml
factor_research/ta_source.py
scripts/run_ta_factor_adapter_smoke_v1.py
scripts/promote_ta_smoke_catalog_entries_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_ta_factor_adapter_smoke_v1.py --config configs\ta_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\ta_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_smoke_catalog_entries_v1.py --config configs\ta_factor_smoke_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

关键输出：

```text
outputs/ta_factor_adapter_v1/smoke/ta_adapter_report.md
outputs/ta_factor_adapter_v1/smoke/ta_factor_inventory.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke_passed.yaml
outputs/factor_evaluation_v4/ta_smoke_v1/evaluator_status.csv
outputs/factor_evaluation_v4/ta_smoke_v1/open_source_metric_index.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_smoke_promotion_audit.csv
```

完成结果：

```text
TA eligible factors: 79
TA excluded columns: 7
selected V4 smoke factors: 5
promoted smoke factors: 5
readiness total_runnable: 175
readiness new_source_runnable: 5
readiness large-scale status: blocked
```

排除规则：

- `ta_trend_visual_ichimoku*`：上游 `visual=True` 会向后平移值。
- `ta_others_*`：日收益/累计收益类输出与项目 label 和 basic return 因子重叠。
- `ta_volume_vpt`、`ta_volume_nvi`：上游当前依赖 pandas `pct_change` 默认填充行为，先排除。

V4 smoke 结果：

- Alphalens Reloaded：5/5 pass。
- Qlib eval：5/5 pass。
- jqfactor_analyzer：5/5 partial_pass，失败项仅为已知 `factor_returns` / `factor_alpha_beta` index-name 问题。

下一步：

- 进入 V3.20：TA eligible 因子 batch plan。
- 为剩余 74 个未评价 eligible TA 因子生成可恢复 batch 配置。
- 降低单次运行风险，使用 small-batch + resume + metric summary。
- 通过 batch 后再把 TA promoted catalog 提升到至少 20 个新源 runnable，使 readiness gate 从 `blocked` 进入 `partial/ready-for-large-scale-screening`。

## 52. V3.20：TA Batch Evaluation Plan V1

状态：已完成 dry-run。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/TA_BATCH_EVALUATION_PLAN_V1.md
```

新增文件：

```text
configs/ta_factor_batch_catalogs_v1.yaml
configs/ta_factor_evaluation_batch_base_v1.yaml
configs/factor_evaluation_batch_v1_ta_remaining74.yaml
scripts/prepare_ta_batch_catalogs_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_ta_batch_catalogs_v1.py --config configs\ta_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_ta_remaining74.yaml --dry-run
```

关键输出：

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_remaining74.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_combined79.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_catalog_audit.csv
outputs/factor_evaluation_batch_v1/ta_remaining74_smoke/batch_manifest.csv
outputs/factor_evaluation_batch_v1/ta_remaining74_smoke/factor_evaluation_batch_v1_report.md
outputs/factor_evaluation_batch_v1/ta_remaining74_smoke/generated_configs/batch_*.yaml
```

完成结果：

```text
source_smoke factors: 79
smoke_passed runnable: 5
remaining pending: 74
planned batches: 15
batch size: 5
dry-run status: planned
```

下一步：

- 执行 `--max-batches 1` 真实小批验证。
- 如果第 1 批通过，再逐步执行 2-3 个 batch。
- 每轮执行后汇总 evaluator_status、failure_reasons 和 open_source_metric_index。
- 只有通过 V4 的 TA 因子才进入 promoted runnable catalog。

## 53. V3.21：TA Batch Promotion V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/TA_BATCH_PROMOTION_V1.md
```

新增文件：

```text
configs/ta_factor_batch_promotion_v1.yaml
scripts/promote_ta_batch_catalog_entries_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_ta_remaining74.yaml --max-batches 15 --output-root outputs\factor_evaluation_batch_v1\ta_remaining74_batch1
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_batch_catalog_entries_v1.py --config configs\ta_factor_batch_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

关键输出：

```text
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/factor_evaluation_batch_v1_report.md
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/ta_remaining74_metric_index.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_batch_passed72.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_holdout2.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_promotion_audit.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_promotion_report.md
```

完成结果：

```text
TA remaining evaluated: 74
batch promoted: 72
batch holdout: 2
combined TA promoted catalog: 77
readiness total_runnable: 247
readiness new_source_runnable: 77
readiness large-scale status: partial
```

holdout 因子：

```text
ta_volatility_bbli
ta_volatility_kchi
```

原因：两个因子在 Alphalens Reloaded 的 `quantile_turnover` 步骤没有产生数值。它们通过 Qlib eval，但暂不进入 promoted runnable catalog。

下一步：

- 不继续把 Alpha158 当作单一研究对象细挖。
- 不急着训练新模型或调交易策略。
- 进入 V3.22：通用多来源 screening / candidate-pool contract。
- 将 Alpha158 full runnable catalog、TA promoted77 catalog、V4 metric index 和 holdout 表合并为统一筛选输入。
- 先让 Alphalens Reloaded、jqfactor_analyzer、Qlib eval、本项目 current evaluator 结果共存，再做主观判断层。
- contract 通过 readiness 后，再继续接 Alpha101、基本面、行业风格和更多开源来源。

## 54. V3.22：Multi-Source Screening Contract V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/MULTI_SOURCE_SCREENING_V1.md
```

新增文件：

```text
configs/multi_source_screening_v1.yaml
factor_research/multi_source_screening.py
scripts/run_multi_source_screening_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

关键输出：

```text
outputs/multi_source_screening_v1/current/multi_source_screening_input.csv
outputs/multi_source_screening_v1/current/multi_source_candidate_board.csv
outputs/multi_source_screening_v1/current/multi_source_candidate_pool.csv
outputs/multi_source_screening_v1/current/multi_source_alpha_candidates.csv
outputs/multi_source_screening_v1/current/multi_source_holdouts.csv
outputs/multi_source_screening_v1/current/multi_source_contract_status.csv
outputs/multi_source_screening_v1/current/multi_source_screening_report.md
```

完成结果：

```text
screening rows: 237
sources: 2
Alpha158 strict rows: 155
TA strict rows: 77
holdouts: 5
alpha candidates: 14
multi-source contract status: pass
factor research readiness: ready
```

设计结论：

- Alpha158 继续作为验证过的 reference pipeline。
- TA promoted77 进入通用候选池，但暂时保持 `monitor`，不直接判为 alpha。
- readiness gate 已把 multi-source screening input、candidate board、candidate pool、holdouts 和 contract status 纳入必备输出。
- 现在工具链已经可以支撑大规模多来源因子研究。

下一步：

- 进入 V3.23：Alpha101 或其他开源公式源 adapter。
- 优先复用 KunQuant / Ginkgo Alpha101 等开源实现，避免手写公式。
- 每个新来源继续走 source manifest -> adapter audit -> V4 smoke -> batch -> promotion/holdout -> multi-source screening。
- 在更多新来源进入 `monitor` 后，再建设通用 judgement 层，把新来源因子筛成 `alpha_candidate`、`risk_control`、`monitor` 或 `holdout`。

## 55. V3.23：Alpha101 Source Audit V1

状态：已完成 source audit，adapter pending。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA101_SOURCE_AUDIT_V1.md
```

新增文件：

```text
configs/alpha101_source_audit_v1.yaml
scripts/audit_alpha101_sources_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha101_sources_v1.py --config configs\alpha101_source_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

关键输出：

```text
outputs/factor_catalog_alpha101_v1/source_audit/alpha101_source_summary.csv
outputs/factor_catalog_alpha101_v1/source_audit/kunquant_alpha101_inventory.csv
outputs/factor_catalog_alpha101_v1/source_audit/alpha101_source_audit_report.md
outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml
```

完成结果：

```text
KunQuant parsed formula functions: 82
KunQuant all_alpha entries: 82
Ginkgo runnable implementation files: 0
metadata catalog entries: 82
status: source_audit_passed_adapter_pending
```

重要发现：

- KunQuant 是当前可用的 Alpha101 主来源，license 为 Apache-2.0。
- Ginkgo_Alpha101 本地克隆只有 README/LICENSE，不能作为 runnable adapter 来源。
- KunQuant `all_alpha` 当前不是完整 101 个编号，而是 82 个公式。
- metadata catalog 全部保持 `enabled: false`、`runnable: false`，防止未适配公式误入 batch runner。

下一步：

- 实现 KunQuant Alpha101 adapter smoke。
- 先选择 3-5 个字段依赖简单、窗口较短的公式，例如 `alpha001`、`alpha009`、`alpha012`、`alpha033`、`alpha101`。
- 尽量调用 KunQuant 的公式定义或 pandas reference，不手写公式。
- smoke 通过后，再进入 V4 评价、promotion/holdout 和 multi-source screening。

## 56. V3.24：Alpha101 Adapter Smoke + 三来源 Screening

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA101_ADAPTER_SMOKE_V1.md
```

新增文件：

```text
configs/alpha101_factor_adapter_smoke_v1.yaml
configs/alpha101_factor_evaluation_smoke_v1.yaml
configs/alpha101_factor_smoke_promotion_v1.yaml
factor_research/alpha101_source.py
scripts/run_alpha101_factor_adapter_smoke_v1.py
scripts/promote_alpha101_smoke_catalog_entries_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\alpha101_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_smoke_catalog_entries_v1.py --config configs\alpha101_factor_smoke_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

关键输出：

```text
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_inventory.csv
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_catalog_smoke_passed.yaml
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_smoke_promotion_audit.csv
outputs/factor_evaluation_v4/alpha101_smoke_v1/evaluator_status.csv
outputs/factor_evaluation_v4/alpha101_smoke_v1/open_source_metric_index.csv
outputs/multi_source_screening_v1/current/multi_source_contract_status.csv
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
```

完成结果：

```text
Alpha101 smoke selected factors: 5
adapter rows: 89,000
adapter coverage: 94.23% to 99.37%
Alphalens/Qlib status: pass
JQFactor status: partial_pass with recorded known index-name failures
Alpha101 smoke promoted catalog: 5
multi-source screening rows: 242
multi-source sources: 3
new source strict rows: 82
readiness total_runnable: 252
readiness new_source_runnable: 82
readiness overall: ready
```

重要修正：

- 外部 factor spec 现在使用 catalog `name` 作为项目内唯一因子 ID，避免不同来源的 `alpha001` 等原始名称互相撞。
- JQFactor adapter 空输入时返回完整结构，单个因子过滤为空不会拖垮整批任务。
- Alpha101 进入 multi-source screening 后保持 `monitor`，不直接作为 alpha 信号。
- Readiness 合同已把 Alpha101 adapter inventory、V4 metric index、evaluator status、promotion audit 和 passed catalog 纳入必备输出。

下一步：

- 不继续围绕 Alpha158 或 5 个 Alpha101 smoke 因子做策略细调。
- 将 Alpha101 从 5 个 smoke 因子扩展到 KunQuant 已审计的 82 个可用公式，优先复用开源实现。
- 同步寻找更多可复用开源因子源，例如基本面、行业风格、风险暴露和其他公式库。
- 每个新来源继续走 source audit -> adapter smoke -> V4 batch -> promotion/holdout -> multi-source screening。
- 当新来源 monitor 因子足够多后，再建设通用 judgement 层，把新来源因子筛成 `alpha_candidate`、`risk_control`、`monitor` 或 `holdout`。

## 57. V3.25：Alpha101 Batch Promotion V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA101_BATCH_PROMOTION_V1.md
```

新增文件：

```text
configs/alpha101_factor_batch_catalogs_v1.yaml
configs/alpha101_factor_adapter_batch82_v1.yaml
configs/alpha101_factor_evaluation_batch_base_v1.yaml
configs/factor_evaluation_batch_v1_alpha101_candidate71.yaml
configs/alpha101_factor_batch_promotion_v1.yaml
scripts/prepare_alpha101_batch_catalogs_v1.py
scripts/promote_alpha101_batch_catalog_entries_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha101_batch_catalogs_v1.py --config configs\alpha101_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_batch82_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha101_candidate71.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_batch_catalog_entries_v1.py --config configs\alpha101_factor_batch_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
Alpha101 metadata formulas: 82
adapter factor frame: 82 factors, 500 instruments, 89,000 rows
adapter eligible: 76
adapter zero-valid holdout: 6
V4 batch candidates: 71
V4 batch promoted: 59
V4 batch holdout: 12
combined Alpha101 promoted catalog: 64
combined Alpha101 holdout catalog: 18
multi-source screening rows: 319
new-source strict rows: 141
readiness total_runnable: 311
readiness new_source_runnable: 141
readiness overall: ready
```

重要修正：

- Alpha101 adapter 现在会在 KunQuant pandas reference 丢失股票代码列名时重贴 Qlib instrument 标签，防止出现 `0..499` 这样的伪 instrument。
- batch runner 使用 catalog `name` 作为项目内唯一 factor ID，避免多来源 `alpha001` 名称冲突。
- `zero_valid_rows` 因子进入 adapter holdout，不送入 V4。
- V4 partial/not_run 因子进入 holdout；已知 JQFactor alpha/beta index-name partial 不单独阻塞 promotion。

下一步：

- 不继续围绕 Alpha158、TA 或 Alpha101 单个因子细调策略。
- 优先寻找下一批开源因子源：基本面、行业风格、风险暴露、其他公式库或 A 股单因子测试框架。
- 同时可开始设计通用 multi-source judgement 层，把现有 141 个新来源 promoted monitor 因子进一步筛成 alpha/risk/monitor/holdout。

## 58. V3.26：Multi-Source Judgement V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/MULTI_SOURCE_JUDGEMENT_V1.md
```

新增文件：

```text
configs/multi_source_judgement_v1.yaml
factor_research/multi_source_judgement.py
scripts/run_multi_source_judgement_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_judgement_v1.py --config configs\multi_source_judgement_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
judgement board rows: 319
research candidates: 43
new-source alpha probes: 29
TA probes: 15
Alpha101 probes: 14
holdouts: 23
readiness generic_multi_source_judgement: pass
readiness overall: ready
```

重要边界：

- Alpha158 仍保留既有 14 个 `alpha_candidate`，不改变当前组合/模型默认输入。
- TA 与 Alpha101 的 promoted 因子可以进入 `new_source_alpha_probe`，但不会成为 downstream default。
- V1 只读取 Alphalens Reloaded、jqfactor_analyzer 和 Qlib eval 已生成指标，不改开源评价定义。
- coverage / missing-rate gate 比 source promotion 更严格，避免低覆盖强信号被误当成 alpha。

下一步：

- 不继续研究单个 Alpha158、TA 或 Alpha101 因子。
- 优先寻找下一批开源因子源和数据源：基本面、行业/风格暴露、风险暴露、其他 A 股公式库。
- 对现有 29 个 `new_source_alpha_probe` 增加更长 OOS、相关性/暴露和组合 smoke 验证后，再决定是否进入模型训练输入。

## 59. V3.27：Open Source Factor Expansion Audit V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/OPEN_SOURCE_FACTOR_EXPANSION_AUDIT_V1.md
```

新增文件：

```text
configs/open_source_factor_expansion_audit_v1.yaml
scripts/audit_open_source_factor_expansion_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_open_source_factor_expansion_v1.py --config configs\open_source_factor_expansion_audit_v1.yaml
```

完成结果：

```text
candidates: 8
direct_adapter_next: 1
data_audit_next: 1
reference_only_due_gpl: 2
reference_only_until_license_review: 4
top candidate: qlib_alpha360
second candidate: factortest_exposure_diagnostics
```

本阶段额外拉取到 `tmp/reference_repos/` 的参考仓库：

```text
GetAstockFactors
ChinaAShareEquityCharacteristics
techfactor
```

重要结论：

- `qlib_alpha360` 是下一步最适合直接做 adapter smoke 的来源：MIT、Qlib 原生、当前 OHLCV/amount 数据即可支持。
- `factortest_exposure_diagnostics` 是下一步最适合做数据能力审计的来源：MIT，适合补行业/风格/Barra 暴露，但要先映射本项目 provider 字段。
- `techfactor_gtja191` 和 `ChinaAShareEquityCharacteristics` 因 GPL-3.0 暂不复制代码，只保留公式/数据结构参考。
- `multi-factor`、`GetAstockFactors`、`AlphaTrading`、`Parsnip77` 因 unknown license 或外部数据假设，暂不直接接入。

下一步：

- 制定并执行 `qlib_alpha360` adapter smoke / batch 计划。
- 并行制定 FactorTest-style industry/style/exposure data capability audit。

## 60. V3.28：Qlib Alpha360 Source Audit 与 Adapter Smoke V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA360_ADAPTER_SMOKE_V1.md
```

新增文件：

```text
factor_research/qlib_alpha360.py
configs/alpha360_catalog_audit_v1.yaml
configs/alpha360_expression_adapter_smoke_v1.yaml
scripts/audit_alpha360_catalog_v1.py
scripts/build_alpha360_expression_frame_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_catalog_v1.py --config configs\alpha360_catalog_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
Alpha360 formulas: 360
missing provider fields: 0
smoke catalog entries: 24
smoke factor frame rows: 88,797
smoke instruments: 500
smoke factors: 24
readiness required_output_contracts: pass
readiness overall: ready
```

重要边界：

- Alpha360 公式直接来自 Qlib `Alpha360DL.get_feature_config`，不手写、不改公式。
- `alpha360_catalog_smoke.yaml` 仍是 disabled/non-runnable，不会绕过 V4 评价进入筛选。
- 本阶段只验证 adapter smoke；没有训练模型，没有策略优化，没有替换 Qlib baseline。

下一步：

- 基于 Alpha360 smoke factor frame 跑 V4 smoke。
- 若 smoke 通过，再生成 360 公式 batch candidate catalog 并走可恢复 V4 batch。
- promotion/holdout 后再接入 multi-source screening 和 judgement。

## 61. V3.29：Alpha360 V4 Smoke V1

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA360_V4_SMOKE_V1.md
```

新增文件：

```text
configs/factor_evaluation_v4_alpha360_smoke_v1.yaml
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_alpha360_smoke_v1.yaml
```

完成结果：

```text
evaluated factors: 22
raw rows: 232,881
tradable rows: 133,958
Alphalens Reloaded: 22 pass
Qlib eval: 22 pass
jqfactor_analyzer: 22 partial_pass
open_source_metric_index rows: 396
context_metric_index rows: 4,224
```

重要边界：

- 本阶段排除 `alpha360_CLOSE0` 和 `alpha360_VOLUME0`，因为它们是归一化恒等因子。
- jqfactor partial 来自其 `factor_returns` / `factor_alpha_beta` 对 MultiIndex 的已知约束，当前只记录，不改开源评价口径。
- 本次外部因子覆盖率约 25.3%，原因是 adapter smoke frame 只取 500 只股票；下一步全量 batch 需要完整 liquid2000 覆盖。

下一步：

- 生成 Alpha360 batch candidate / adapter holdout catalog。
- 对 358 个非恒等 Alpha360 因子生成完整 2021-2023 expression frame。
- 走 batch V4、promotion/holdout、multi-source screening 和 judgement。

## 62. V3.30：Alpha360 Batch Catalogs 与 Dry-Run V1

状态：已完成 dry-run。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA360_BATCH_CATALOGS_V1.md
```

新增文件：

```text
configs/alpha360_factor_batch_catalogs_v1.yaml
configs/alpha360_expression_adapter_batch358_v1.yaml
configs/alpha360_factor_evaluation_batch_base_v1.yaml
configs/factor_evaluation_batch_v1_alpha360_candidate358.yaml
scripts/prepare_alpha360_batch_catalogs_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha360_batch_catalogs_v1.py --config configs\alpha360_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358.yaml --dry-run
```

完成结果：

```text
source_all: 360
batch_candidate: 358
adapter_holdout: 2
dry-run planned batches: 72
batch size: 5
```

重要边界：

- `alpha360_CLOSE0` 与 `alpha360_VOLUME0` 已放入 adapter holdout。
- 358 个 batch candidates 仍是 disabled/non-runnable，未进入筛选或模型输入。
- dry-run 只生成计划，不执行 V4 batch。

下一步：

- 运行 `configs/alpha360_expression_adapter_batch358_v1.yaml` 生成 batch factor frame。
- 执行 `configs/factor_evaluation_batch_v1_alpha360_candidate358.yaml --max-batches 1` 小批验证。
- 小批通过后再 resume 全部 72 个 batch。

## 63. V3.31：Alpha360 Batch Frame 与 Smoke Batch1 V1

状态：已完成小批验证。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA360_BATCH_FRAME_AND_SMOKE_BATCH1_V1.md
```

新增文件：

```text
configs/factor_evaluation_batch_v1_alpha360_candidate358_smoke.yaml
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_batch358_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358.yaml --dry-run
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358_smoke.yaml
```

完成结果：

```text
batch358 factor frame rows: 88,797
batch358 factor count: 358
dry-run planned batches: 72
smoke batch_001 status: pass
smoke batch_001 factors: 5
smoke batch_001 metric rows: 90
```

重要边界：

- batch358 的 `factor_frame.pkl` 是缓存文件，不进入 Git。
- smoke batch1 独立 output root，避免覆盖 72 批 dry-run manifest。
- jqfactor partial 仍只记录，不改开源指标口径。

下一步：

- 后续 V3.32 已完成全部 Alpha360 execution batches、promotion/holdout、multi-source screening 与 judgement。
- 当前状态见 `docs/_archive/05_open_source_factor_batches/ALPHA360_BATCH_PROMOTION_AND_MULTI_SOURCE_V1.md`。

## 64. V3.32：Alpha360 完整 Batch Promotion 与 Multi-Source 接入

状态：已完成。

阶段文档：

```text
docs/_archive/05_open_source_factor_batches/ALPHA360_BATCH_PROMOTION_AND_MULTI_SOURCE_V1.md
```

新增文件：

```text
configs/alpha360_factor_batch_promotion_v1.yaml
configs/factor_evaluation_batch_v1_alpha360_candidate358_execution.yaml
scripts/promote_alpha360_batch_catalog_entries_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358_execution.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha360_batch_catalog_entries_v1.py --config configs\alpha360_factor_batch_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_judgement_v1.py --config configs\multi_source_judgement_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
Alpha360 execution batches: 72
Alpha360 source factors: 358
Alpha360 metric index rows: 6,444
Alpha360 batch promoted: 358
Alpha360 V4 batch holdout: 0
Alpha360 adapter holdout: 2
multi-source screening rows: 679
multi-source judgement board rows: 679
new-source alpha probes: 328
Alpha360 probes: 299
readiness total_runnable: 669
readiness new_source_runnable: 499
overall_status: ready
```

重要边界：

- `alpha360_CLOSE0` 与 `alpha360_VOLUME0` 继续作为 adapter holdout。
- jqfactor_analyzer 的 `factor_returns` / `factor_alpha_beta` partial 仍只记录，不改开源评价口径。
- Alpha360 promoted catalog 已 enabled/runnable，但 judgement 后仍只是研究 probes，不是默认模型或组合输入。

下一步：

- 为 328 个 `new_source_alpha_probe` 增加相关性、暴露、稳定性、分段 OOS 和组合 smoke 验证。
- 并行推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
- 继续接入更多开源因子源，但必须沿用 source audit、adapter、V4 batch、promotion/holdout、multi-source screening、multi-source judgement 的路径。

## 65. V3.33：New-Source Probe Diagnostics V1

状态：已完成。

阶段文档：

```text
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_DIAGNOSTICS_V1.md
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_DIAGNOSTICS_V1_PLAN.md
```

新增文件：

```text
configs/new_source_probe_diagnostics_v1.yaml
factor_research/new_source_probe_diagnostics.py
scripts/run_new_source_probe_diagnostics_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_diagnostics_v1.py --config configs\new_source_probe_diagnostics_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
all probes: 328
frame diagnostics selected: 120
portfolio smoke selected: 50
correlation pairs: 200
portfolio smoke executed rebalances: 4
new_source_probe_diagnostics: pass
readiness overall_status: ready
```

重要发现：

- 部分 TA / Alpha101 probes 高度冗余，例如 `ta_trend_sma_fast` 与 `ta_volatility_kcc` 的日均横截面 Spearman 相关接近 1。
- 部分 probes 与 liquidity / tradability 代理高度相关，例如 `kunquant_alpha101_alpha083` 与 `ta_volatility_atr`。
- portfolio smoke 只验证接口和风险，不作为策略结论；当前只覆盖 factor frame 可用的 2021 H1 有效调仓窗口。

下一步：

- 先复核 `redundancy_watch` 与 `tradability_exposure_watch`。
- 再推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
- 等 exposure 数据能力完成后，再决定哪些 probes 可以进入训练候选，而不是直接训练全部 328 个。

## 66. V3.34：New-Source Probe Review V1

状态：已完成。

阶段文档：

```text
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_REVIEW_V1.md
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_REVIEW_V1_PLAN.md
```

新增文件：

```text
configs/new_source_probe_review_v1.yaml
factor_research/new_source_probe_review.py
scripts/run_new_source_probe_review_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_review_v1.py --config configs\new_source_probe_review_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
review rows: 328
redundancy pairs: 200
redundancy groups: 4
tradability exposure watchlist: 19
strict OOS extension candidates: 3
new_source_probe_review: pass
readiness overall_status: ready
```

严格 OOS extension candidates：

```text
alpha360_HIGH36
alpha360_HIGH37
alpha360_HIGH40
```

重要发现：

- 最大 Alpha360 冗余组包含 80 个 close/high/low/open/vwap lag 窗口因子。
- TA / Alpha101 也存在混合高相关冗余组。
- 19 个 probes 需要先做 tradability / liquidity exposure review。

下一步：

- 为 3 个严格候选扩展 recent OOS factor frame。
- 并行推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
- 不直接训练全部 328 个 probes。

## 67. V3.35：Alpha360 Strict OOS Extension V1

状态：已完成。

阶段文档：

```text
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_EXTENSION_V1_PLAN.md
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_EXTENSION_V1.md
```

新增文件：

```text
configs/alpha360_expression_adapter_strict_oos_recent_v1.yaml
configs/alpha360_factor_evaluation_strict_oos_recent_base_v1.yaml
configs/factor_evaluation_batch_v1_alpha360_strict_oos_recent.yaml
configs/alpha360_strict_oos_extension_audit_v1.yaml
scripts/audit_alpha360_strict_oos_extension_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_strict_oos_recent_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_strict_oos_recent.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_extension_v1.py --config configs\alpha360_strict_oos_extension_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
strict candidates: 3
recent OOS expression rows: 286,944
min coverage: 0.996236
V4 batches: 1 pass
evaluator status rows: 9
metric index rows: 54
strict OOS contract rows: 8 pass
alpha360_strict_oos_extension: pass
readiness overall_status: ready
```

Recent OOS 指标摘录：

```text
alpha360_HIGH36 alphalens 10D mean IC: 0.063736, 20D mean IC: 0.072231
alpha360_HIGH37 alphalens 10D mean IC: 0.065477, 20D mean IC: 0.073073
alpha360_HIGH40 alphalens 10D mean IC: 0.065851, 20D mean IC: 0.072314
```

重要边界：

- 3 个因子仍然只是 strict-OOS research candidates。
- `jqfactor_analyzer` 保留已知 partial pass，只允许 `factor_returns` / `factor_alpha_beta` index-name 问题。
- 本阶段不训练模型、不调策略、不改开源评价体系。

下一步：

- 做 main vs recent OOS 稳定性对比。
- 对 19 个 `tradability_exposure_review` probes 做流动性/可交易性暴露归因。
- 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。

## 68. V3.36：Alpha360 Strict OOS Stability V1

状态：已完成。

阶段文档：

```text
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_STABILITY_V1_PLAN.md
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_STABILITY_V1.md
```

新增文件：

```text
configs/alpha360_strict_oos_stability_v1.yaml
scripts/audit_alpha360_strict_oos_stability_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_stability_v1.py --config configs\alpha360_strict_oos_stability_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
metric pairs: 54
summary rows: 3
recent Alphalens mean IC min: 0.063736
recent Qlib information ratio min: 5.025121
signal sign flips: 0
all sign flips: 3 beta-only flips
strict OOS stability contract rows: 8 pass
alpha360_strict_oos_stability: pass
readiness overall_status: ready
```

关键观察：

- 3 个因子 recent-OOS Alphalens mean IC 仍为正。
- 3 个因子 recent-OOS Qlib IR 仍为正，但较主窗口变弱。
- 3 个 sign flip 全部来自 beta 指标，不作为信号阻断。
- 3 个候选仍然只是研究候选，不进入训练输入。

下一步：

- 对 19 个 `tradability_exposure_review` probes 做流动性/可交易性暴露归因。
- 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。

## 69. V3.37：Tradability Exposure Attribution V1

状态：已完成。

阶段文档：

```text
docs/_archive/06_probe_and_tradeability_audits/TRADABILITY_EXPOSURE_ATTRIBUTION_V1_PLAN.md
docs/_archive/06_probe_and_tradeability_audits/TRADABILITY_EXPOSURE_ATTRIBUTION_V1.md
```

新增文件：

```text
configs/tradability_exposure_attribution_v1.yaml
scripts/audit_tradability_exposure_attribution_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_tradability_exposure_attribution_v1.py --config configs\tradability_exposure_attribution_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
watchlist rows: 19
attribution rows: 19
source families: 2
primary proxy present: 19/19
diagnostic exposure rows: 120
downstream default: 0
contract rows: 6 pass
tradability_exposure_attribution: pass
readiness overall_status: ready
```

行动汇总：

```text
holdout_before_residualization strong: 6
holdout_redundant_liquidity_proxy material: 7
holdout_redundant_liquidity_proxy strong: 1
manual_review_before_training moderate: 4
residualization_candidate_review material: 1
```

重要结论：

- 19 个 watchlist probes 的主暴露代理全部是 `liquidity_value`。
- TA 因子主要是正向流动性暴露，Alpha101 多为负向流动性暴露。
- 高暴露因子不能直接 raw training；应先 holdout、人工复核或进入 residualized evaluation。

下一步：

- 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
- 设计 residualized factor evaluation 的最小接口。

## 70. V3.38：Exposure Data Capability Audit V1

状态：已完成。

阶段文档：

```text
docs/_archive/06_probe_and_tradeability_audits/EXPOSURE_DATA_CAPABILITY_AUDIT_V1_PLAN.md
docs/_archive/06_probe_and_tradeability_audits/EXPOSURE_DATA_CAPABILITY_AUDIT_V1.md
```

新增文件：

```text
configs/exposure_data_capability_audit_v1.yaml
scripts/audit_exposure_data_capability_v1.py
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_exposure_data_capability_v1.py --config configs\exposure_data_capability_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

完成结果：

```text
reference capabilities: present=5/5
provider field probes: 14
project context: available
tradability/data_quality prefilters: available
size fields: 0/5 available
industry fields: 0/4 available
barra fields: 0/5 available
contract rows: 6 pass
exposure_data_capability_audit: pass
readiness overall_status: ready
```

重要结论：

- FactorTest / qlib_factor_platform 的行业、市值、Barra、中性化设计可作为模块边界参考。
- 当前项目已有 benchmark/universe/context、tradability 和 data_quality 前置能力。
- 当前 provider 缺少市值、行业和 Barra 字段，不能直接做 FactorTest-style industry/Barra neutralization。

下一步：

- 设计外部行业/市值数据接入 contract。
- 或先做 liquidity residualized factor evaluation 的最小接口。

## 71. V3.39：Liquidity Residualized Factor Evaluation V1

状态：已完成。

阶段文档：

```text
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1_PLAN.md
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1.md
```

阶段目标：

```text
对 19 个 tradability_exposure_review probes 做 liquidity/tradability residualized evaluation，
判断 raw 因子信号是否主要来自 liquidity_value / liquidity_bucket / tradability_score。
```

新增文件：

```text
configs/liquidity_residualized_factor_evaluation_v1.yaml
factor_research/liquidity_residualization.py
scripts/run_liquidity_residualized_factor_evaluation_v1.py
scripts/audit_liquidity_residualized_factor_evaluation_v1.py
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1.md
```

输入：

```text
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_board.csv
outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv
outputs/ta_factor_adapter_v1/smoke/factor_frame.pkl
outputs/alpha101_factor_adapter_v1/batch82/factor_frame.pkl
```

输出：

```text
outputs/liquidity_residualized_factor_evaluation_v1/current/residualized_factor_frame.pkl
outputs/liquidity_residualized_factor_evaluation_v1/current/residualized_factor_summary.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/daily_residualization_diagnostics.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/raw_vs_residualized_metric_comparison.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/residualized_candidate_actions.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_factor_evaluation_report.md
```

实现：

- 复用现有 tradability labels 和 factor frames。
- 每个交易日独立 OLS 残差化：`factor_z ~ intercept + liquidity_value_z + liquidity_bucket_z + tradability_score_z + residual`。
- 当前 tradability labels 中 `tradability_score` 多数情况下为常数，代码会按日自动剔除零方差 proxy，实际回归通常由 `liquidity_value` 与 `liquidity_bucket` 驱动。
- 残差化前对因子和代理做 MAD winsorization + robust z-score (clip ±3)。
- 残差列后缀 `__resid_liquidity`，不覆写原始因子列。
- 日度诊断：coverage、R²、raw-residual 相关性。
- 如 factor frames 或 feature cache 中有 label 列，则计算 IC/IR 比较；否则使用诊断指标。
- 候选动作分层：`residual_signal_survives`、`liquidity_proxy_confirmed`、`holdout`、`needs_manual_review`。

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_liquidity_residualized_factor_evaluation_v1.py --config configs\liquidity_residualized_factor_evaluation_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_liquidity_residualized_factor_evaluation_v1.py --config configs\liquidity_residualized_factor_evaluation_v1.yaml
```

边界：

- 不训练模型。
- 不进入策略优化。
- 不做行业/Barra 中性化。
- 不把 residualized 因子自动加入 downstream default。
- 不修改现有 evaluator 定义。

Contract（≥ 8 checks）：

```text
watchlist_rows >= 19
residualized_factor_count >= 19
residualized_coverage_min >= 0.80  # current: 0.1495, blocked
daily_diagnostics_rows > 0
raw_vs_residualized_metric_rows > 0
contract_status_rows >= 8
downstream_default_included == 0
```

完成后再决定：

- 对残差信号仍存活的少量因子做 recent-OOS residualized evaluation。
- 设计外部行业/市值数据接入 contract。
- 在外部行业/市值数据 ready 后，再实现 FactorTest-style industry/size neutralized evaluation。
