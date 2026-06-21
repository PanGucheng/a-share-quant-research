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
docs/FACTOR_RESEARCH_MODULE_PLAN.md
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
docs/FACTOR_RESEARCH_ALGORITHM_AUDIT.md
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
docs/FACTOR_RESEARCH_V3_REFERENCE_SURVEY.md
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

状态：已完成。

新增计划文档：

```text
docs/FACTOR_RESEARCH_V3_1_PLAN.md
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
docs/FACTOR_SCREENING_V3_3_PLAN.md
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
docs/FACTOR_CANDIDATE_POOL_V3_4_PLAN.md
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
docs/FACTOR_EXPANSION_V3_5_REFERENCE_SURVEY.md
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
docs/FACTOR_EXPANSION_V3_5_IMPLEMENTATION.md
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
docs/FACTOR_EVALUATION_OPEN_SOURCE_COEXISTENCE_PLAN.md
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
docs/FACTOR_EVALUATION_SOURCE_MANIFEST.md
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
docs/FACTOR_EVALUATION_V4_SMOKE_TEST.md
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
