# Factor Screening V3.3 Plan

本计划承接 factor research V3.1/V3.2。目标不是新增模型、策略或实盘模块，而是在现有因子研究输出之上建立一个可解释的因子筛选层。

## 1. Goal

把 V3 因子研究输出转成候选池决策：

```text
factor_research outputs
 -> factor_screening
 -> factor_candidate_board.csv
 -> factor_screening_report.md
 -> 后续组合回测候选输入
```

筛选层只消费现有 CSV，不重新读取 Qlib 数据，不重新计算基础因子。

## 2. Inputs

默认输入目录：

```text
outputs/factor_research_v3/liquid2000_core
```

读取文件：

```text
factor_neutralized_summary.csv
factor_neutralized_group_return_summary.csv
factor_slice_ic.csv
factor_slice_group_return_summary.csv
factor_exposure_correlation.csv
factor_neutralized_correlation.csv
factor_candidate_changelog.csv
```

## 3. Metrics

筛选指标围绕以下维度：

- raw directional Rank IC
- raw directional Rank ICIR
- IC win rate
- OOS directional Rank IC
- 分组收益 directional spread
- 切片稳定性
- 覆盖率和缺失率
- 中性化后信号保留率
- 暴露相关性
- 与已有因子的冗余相关性

## 4. Candidate Status

每个基础因子输出一个状态：

```text
portfolio_test_candidate
research_candidate
risk_exposure
redundant
watch
reject
```

含义：

- `portfolio_test_candidate`: 主窗口、OOS、切片、分组收益和中性化保留均较好，可进入后续组合测试。
- `research_candidate`: 有一定信号，但还需要继续研究定义、稳定性或中性化。
- `risk_exposure`: raw 表现较强，但主要来自波动率、流动性或成交额暴露。
- `redundant`: 与更强候选高度相关，暂不单独推进。
- `watch`: 方向未定义或证据不足，保留观察。
- `reject`: 覆盖率、OOS、稳定性或方向性明显不满足。

## 5. Minimal Implementation

新增：

```text
factor_research/screening_v3.py
scripts/run_factor_screening_v3.py
```

新增输出：

```text
outputs/factor_screening_v3/liquid2000_core/factor_candidate_board.csv
outputs/factor_screening_v3/liquid2000_core/factor_screening_report.md
```

## 6. Acceptance Criteria

- [x] 不重算 Qlib 特征和因子。
- [x] 可直接读取 V3 默认输出。
- [x] 对 `amplitude_20`、`std_20`、`rev_5` 给出符合当前研究结论的解释性状态。
- [x] 报告中展示状态分布、候选看板、风险暴露和冗余信息。
- [x] 通过 smoke run。

## 7. Execution Result

完成时间：2026-06-13。

验证命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe -c "from pathlib import Path; [compile(Path(p).read_text(encoding='utf-8'), p, 'exec') for p in ['factor_research/screening_v3.py','scripts/run_factor_screening_v3.py']]; print('syntax ok')"
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_screening_v3.py
```

默认输出：

```text
outputs/factor_screening_v3/liquid2000_core/factor_candidate_board.csv
outputs/factor_screening_v3/liquid2000_core/factor_screening_report.md
```

默认筛选结果：

```text
rev_5          -> research_candidate
amplitude_20   -> risk_exposure
std_20         -> risk_exposure
ret_20         -> watch
amount_mean_20 -> watch
```
