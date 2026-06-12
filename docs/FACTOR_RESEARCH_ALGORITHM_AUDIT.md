# Factor Research Algorithm Audit

本审计用于校准 `factor_research` 的最小实现，避免后续因子筛选因为指标口径错误而跑偏。审计对象只限因子研究与筛选模块，不替换现有 Qlib baseline，不训练新模型，不做实盘。

## 1. Reference Repositories

本轮临时拉取到 `tmp/reference_repos/`，该目录被 `.gitignore` 忽略，不作为项目依赖提交。

| repo | reference commit | purpose |
| --- | --- | --- |
| `cn-vhql/qlib_factor_platform` | `9611ac2d1392761af5988e8a571f2075c61c601e` | 借鉴因子注册、分析页面指标组织、IC/分层/相关性工作流 |
| `stefan-jansen/alphalens-reloaded` | `f0a07c22d554e4b4036983cc80320b432714fe7e` | 校准 factor data、Rank IC、分组收益、换手率等评价口径 |

## 2. Scope

本项目当前选择脚本化、可复现的研究管线，而不是引入复杂 UI 或替换 Qlib 主线。

```text
Qlib provider
  -> factor_library
  -> dataset merge tradability/data_quality
  -> tradable_only pre-filter
  -> diagnostics/metrics
  -> selector
  -> CSV/Markdown outputs
```

`qlib_factor_platform` 更偏交互式平台，本项目只借鉴模块组织方式和指标集合。Alphalens 的指标体系更适合作为算法口径参考，但本项目保留 A 股可交易性和数据质量前置过滤。

## 3. Metric Comparison

| topic | reference behavior | current project behavior | audit result |
| --- | --- | --- | --- |
| factor data schema | Alphalens 使用 `date, asset` MultiIndex，包含 factor、forward returns、factor quantile | `factor_data_schema.md` 和 `factor_data_sample.csv` 输出长表 schema，字段等价但更便于 CSV 检查 | acceptable |
| forward return | Alphalens 要求价格覆盖未来区间，买入价应在因子计算之后 | `label_10d_t1`、`label_20d_t1` 使用 T+1 到 T+N 的未来收益，避免同日收盘后不可成交假设 | acceptable |
| IC / Rank IC | Alphalens `factor_information_coefficient` 使用按日 Spearman | 本项目按日输出 Pearson IC 和 Spearman Rank IC，并有 `min_count` 防止样本太少 | aligned |
| ICIR / win rate | qlib_factor_platform 输出 IC 均值、标准差、IR、胜率 | 本项目输出 ICIR、Rank ICIR、方向调整胜率 | aligned |
| group returns | Alphalens `mean_return_by_quantile` 先按日/分位聚合，再汇总 | 已新增 `factor_group_return.csv` 和 `factor_group_return_summary.csv` | aligned |
| monotonicity | Alphalens 常用分位收益 spread 判断单调性 | 本项目输出 bottom/top、方向调整 spread、单调性分数 | aligned |
| turnover | Alphalens `quantile_turnover` 使用“本期分位中新进入标的数 / 本期分位标的数” | 已修正 `top_quantile_turnover` 分母为本期 top quantile count，并输出 previous/new/top count | aligned |
| factor correlation | qlib_factor_platform 将因子拉平成同一索引后计算相关性 | 本项目按 `datetime x instrument` 对齐后计算 Spearman 相关性，用于候选冗余过滤 | acceptable |
| tradability/data quality | 参考项目不负责本项目的数据诊断约束 | 本项目强制复用 `tradability` 和 `data_quality` 输出作为 `tradable_only` 前置过滤 | project-specific requirement |

## 4. Intentional Deviations

- 分位分桶使用 `pd.qcut(..., duplicates="drop")`。Alphalens 默认在重复边界过多时更倾向报错；A 股日频横截面中成交额、涨跌幅、停牌附近值容易出现大量重复，本项目选择降级输出并在分组结果中保留样本数。
- 相关性默认使用 Spearman，而 `qlib_factor_platform` 示例使用 DataFrame 默认 Pearson。因子筛选阶段更关注排序冗余，Spearman 更贴近 Rank IC 体系。
- `factor_data_sample.csv` 只输出样本，不输出全量 factor data。全量数据可由 runner 复现，默认避免生成过大的中间文件。

## 5. Fixes From This Audit

1. `top_quantile_turnover` 改为 Alphalens 风格的本期分母，并增加 `previous_top_count`、`new_top_count`。
2. 新增逐日分位收益输出 `factor_group_return.csv`。
3. 新增聚合分位收益输出 `factor_group_return_summary.csv`。
4. V2 报告新增 Main Research Group Returns 小节。

## 6. Next Guardrails

- 新增因子前先在 `registry.py` 写清 `expected_direction` 和说明。
- 新增筛选规则前先输出诊断 CSV，再决定是否进入 `selector`。
- 任何候选因子必须同时查看 `tradable_only`、OOS、分组收益、换手率、相关性，不能只看单个 Rank IC。
- 在候选池稳定前，不进入 XGBoost/CatBoost 或深度模型对照。
