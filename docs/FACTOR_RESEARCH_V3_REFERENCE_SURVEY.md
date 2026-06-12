# Factor Research V3 Reference Survey

本文件记录因子研究 V3 的开源参考调研。目标是先借鉴成熟项目的指标口径和模块组织，再做本项目的最小实现；不替换现有 Qlib 主线，不引入复杂 UI，不训练新模型，不做实盘。

## 1. Search Scope

调研关键词：

- factor analysis, IC, Rank IC, quantile returns, turnover
- A 股 因子分析, 中性化, 分层收益, RankIC
- Qlib factor analysis, cross-sectional normalization, group return
- Barra neutralization, double sorting, Fama-MacBeth

临时参考仓库放在：

```text
tmp/reference_repos/
```

该目录已被 `.gitignore` 忽略，不作为项目依赖提交。

## 2. Reference Repositories

| repo | local snapshot | license note | relevance |
| --- | --- | --- | --- |
| https://github.com/JoinQuant/jqfactor_analyzer | `69e677dc0dd9bed9fece02a70b9c81ce3d0afc53` | MIT | A 股单因子分析、预处理、中性化、分组收益、换手率 |
| https://github.com/jltxzxy/FactorTest | `98cb0e0310a50adc1ca1a34fdd89e18caa03381f` | MIT | Barra 中性化、因子相关性、IC 相关性、双重排序、分组 IC |
| https://github.com/Jensenberg/multi-factor | `d86618d8d62ca4d70a283957be6c64003c7bf2c6` | no license file found | 简洁的 MAD 去极值、z-score、行业+市值残差中性化、分层测试 |
| https://github.com/jerryxyx/AlphaTrading | `5e73923786297faeadb27c76f83ec81fad74af51` | no license file found | 多因子研究流程、Spearman 冗余过滤、Fama-MacBeth 思路 |
| https://github.com/stefan-jansen/alphalens-reloaded | `f0a07c22d554e4b4036983cc80320b432714fe7e` | Apache-2.0 | factor data、Rank IC、分组收益、换手率标准口径 |
| https://github.com/cn-vhql/qlib_factor_platform | `9611ac2d1392761af5988e8a571f2075c61c601e` | no license file found | Qlib 因子模块组织、分析工作流、可视化指标组织 |
| https://github.com/microsoft/qlib | local `E:/qlib_prj/qlib_clone` | MIT | Qlib 原生分组收益、IC、横截面标准化处理器 |

## 3. What To Borrow

### jqfactor_analyzer

可借鉴：

- `winsorize`、`winsorize_med`、`standardlize`、`neutralize` 的模块边界。
- `neutralize(data, how=[industry, mktcap], date=...)` 的接口思想：待中性化因子和中性化暴露分离。
- `factor_information_coefficient(group_adjust, by_group)` 的口径：按日横截面 IC，并支持分组去均值。
- `mean_return_by_quantile`、`mean_return_spread_by_quantile`、`quantile_turnover` 的 tear-sheet 指标组织。

不直接采用：

- 聚宽数据接口、行业/市值数据获取层。
- 绘图 tear sheet UI。
- 面向 `jqdatasdk` 的缓存结构。

适合本项目的落地方式：

- 只复用思想，不复制依赖。
- 新增 `factor_research/preprocess.py`，实现本地 DataFrame 版本的 `winsorize_mad`、`cross_sectional_zscore`、`residual_neutralize`。

### FactorTest

可借鉴：

- `calcCorrMatrix` 同时输出因子值相关性和 IC 序列相关性。
- `calcCorrBarra` 的“因子 vs 风格暴露相关性”思路。
- `calcPureFactor` / `calcNeuBarra` 的横截面残差中性化流程。
- `doubleSorting` 和 `calcGroupIC` 的控制变量分组诊断。

不直接采用：

- 月频框架和本地数据表约定。
- 旧式 Barra 数据依赖。
- 直接用收益表现做复杂组合评价。

适合本项目的落地方式：

- 在 V3 中增加 `factor_exposure_correlation.csv`。
- 增加 `factor_ic_by_control_bucket.csv`，扩展当前 bucket IC。
- 中性化先用本项目已有的 `liquidity_bucket`、`std_20`、`amplitude_20`、`amount_mean_20` 作为代理暴露，不等待完整 Barra 模型。

### multi-factor

可借鉴：

- 简洁的预处理顺序：MAD 去极值 -> z-score -> 行业/市值回归残差。
- 分层测试不仅看单调性，也看 top-bottom、净值、相对收益等。
- 因子打分规则：IC、ICIR、胜率、单调性综合判断。

不直接采用：

- 代码依赖私有数据库。
- 没有明确 license，不能复制实现代码。
- 月频收益口径不适合当前日频 Qlib 数据。

适合本项目的落地方式：

- 采用“预处理流水线”设计，不复制代码。
- 将中性化前后的 IC、Rank IC、分组收益、相关性放在同一张对照表。

### AlphaTrading

可借鉴：

- Spearman 相关性用于因子冗余过滤的解释。
- Fama-MacBeth 作为后续“多因子解释力”工具，而不是当前 V3 第一优先级。
- 多因子研究工作流：pretest -> screening -> combination。

不直接采用：

- notebook 形态和图片报告。
- AdaBoost、Kalman Filter、完整 Barra 风险模型。
- 无 license 文件，不复制代码。

适合本项目的落地方式：

- 当前继续保留 Spearman 相关性作为默认冗余过滤。
- Fama-MacBeth 放到 V4/V5，等中性化和分层诊断稳定后再做。

### Qlib Native

可借鉴：

- `CSZScoreNorm` 和 `CSRankNorm` 的横截面标准化口径。
- `analysis_model_performance._group_return` 的 Group1 到 GroupN、long-short、long-average 输出。
- 保持 Qlib baseline 不动，只在独立 `factor_research` 中做诊断。

不直接采用：

- Qlib report 主要面向模型 score，而本项目需要单因子和候选池诊断。
- 不把 V3 写成 Qlib processor 配置，避免和 baseline 训练管线耦合。

## 4. Recommended V3 Design

### 4.1 New Modules

```text
factor_research/
  preprocess.py       # 去极值、横截面标准化、残差中性化
  slices.py           # 年份、流动性桶、波动率桶、市场状态切片
  neutralization.py   # 中性化任务配置和批量运行
  changelog.py        # 候选池版本差异记录
```

### 4.2 New Outputs

```text
outputs/factor_research_v3/<run_name>/
  factor_preprocess_summary.csv
  factor_slice_ic.csv
  factor_slice_group_return.csv
  factor_slice_summary.csv
  factor_neutralized_summary.csv
  factor_neutralized_group_return.csv
  factor_neutralized_correlation.csv
  factor_exposure_correlation.csv
  factor_candidate_changelog.csv
  factor_research_v3_report.md
```

### 4.3 Neutralization Methods

第一版只做轻量、可解释的中性化：

| method | implementation idea | purpose |
| --- | --- | --- |
| `liquidity_bucket_zscore` | 每日、每个 `liquidity_bucket` 内 rank/z-score | 判断因子是否只来自流动性分层 |
| `volatility_bucket_zscore` | 每日按 `std_20` 或 `amplitude_20` 分桶后标准化 | 判断低波动因子是否只是波动率分层 |
| `amount_proxy_residual` | 每日对 `log(amount_mean_20)` 回归取残差 | 近似规模/流动性中性化 |
| `liquidity_volatility_residual` | 每日对流动性桶、波动率桶、成交额代理联合回归取残差 | 最小版多暴露中性化 |

暂缓：

- 真实行业中性化，除非 provider 或外部数据稳定接入。
- 完整 Barra 风险模型。
- Fama-MacBeth 多因子回归。

### 4.4 Slice Diagnostics

V3 默认切片：

- `year`: 自然年。
- `liquidity_bucket`: 复用 `tradability_labels.csv`。
- `volatility_bucket`: 基于 `std_20` 或 `amplitude_20` 每日分桶。
- `market_state`: 用可交易股票池等权未来/过去收益近似分为 up/down/sideways。

每个切片输出：

- IC、Rank IC、ICIR、Rank ICIR。
- IC win rate。
- 分组收益 top/bottom/spread。
- 覆盖率、缺失率。
- 样本日期数和样本股票数。

## 5. Implementation Order

1. 新增 `preprocess.py`，实现本地 DataFrame 版去极值、标准化、残差中性化。
2. 新增 `slices.py`，生成 year/liquidity/volatility/market_state 切片标签。
3. 在 V2 runner 旁新增 `run_factor_research_v3.py`，不要破坏 V2 输出。
4. 只对当前 promote/watch 核心因子先跑 V3：`amplitude_20`、`std_20`、`rev_5`、`ret_20`、`amount_mean_20`。
5. 输出中性化前后对照报告。
6. 再决定是否扩展因子库，不进入模型训练。

## 6. Acceptance Criteria

V3 完成后必须能回答：

- `amplitude_20` 中性化后是否仍然有稳定 Rank IC。
- `std_20` 与 `amplitude_20` 是不是完全冗余。
- `rev_5` 弱于 promote 门槛，是因为换手、样本期、流动性桶，还是波动率暴露。
- 哪些 watch 因子在特定切片里稳定。
- 因子候选池变化是否可追溯。

## 7. Current Decision

推荐下一步执行 V3 最小实现：

- 不新增模型。
- 不调组合策略。
- 不做 UI。
- 不复制外部项目代码。
- 借鉴 `jqfactor_analyzer` 的预处理/中性化接口、`FactorTest` 的控制分组诊断、`multi-factor` 的预处理顺序、Qlib 的横截面标准化口径。
