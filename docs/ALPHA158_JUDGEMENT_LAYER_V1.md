# Alpha158 Judgement Layer V1

本文档记录 Alpha158 全量筛选输入之后的判断层。它的目标是把 155 个 strict screening input 因子和 3 个 holdout 因子整理成可解释、可复查的研究分层，而不是训练模型或生成交易信号。

本阶段继续遵守项目边界：

- 不替换 Qlib baseline。
- 不修改 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 的原始评价口径。
- 不生成自研综合分。
- 不训练新模型，不做实盘。
- 不绕过 data_quality、tradability 和 factor context 约束。

## 1. 输入

```text
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_screening_input.csv
outputs/factor_screening_alpha158_v1/full158/alpha158_context_group_ic_summary.csv
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_correlation_summary.csv
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_correlation_top_pairs.csv
```

这些输入已经包含：

- Alpha158 first20 与 remaining138 的合并评价结果。
- 覆盖率、缺失率、Rank IC、ICIR、win rate。
- 分组收益、换手率、rank autocorrelation。
- context 分组 IC。
- 每日横截面 Spearman 相关性。

## 2. 实现文件

```text
configs/factor_judgement_alpha158_v1.yaml
factor_research/alpha158_judgement.py
scripts/run_alpha158_judgement_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_judgement_v1.py --config configs\factor_judgement_alpha158_v1.yaml
```

## 3. 规则口径

默认规则：

```text
min_coverage: 0.99
max_missing_rate: 0.01
weak_abs_rank_ic: 0.015
consistent_abs_rank_ic: 0.03
strong_abs_rank_ic: 0.05
consistent_abs_rank_icir: 0.20
strong_abs_rank_icir: 0.35
consistent_win_rate: 0.53
strong_win_rate: 0.58
redundancy_corr_threshold: 0.90
```

判断层输出两个层次：

- `signal_label`：只看原始信号证据，分为 `strong_signal`、`consistent_signal`、`weak_signal`、`review`、`holdout` 等。
- `judgement_label`：在 signal 之上优先标记问题，如 `redundant`、`high_turnover`、`unstable_context`。

这不是综合打分。代表因子的选择也不是加权评分，而是按以下可读顺序排序：

```text
signal_label
issue flags
direction agreement
Rank IC
ICIR
turnover
coverage
factor name
```

## 4. 当前结果

输出目录：

```text
outputs/factor_judgement_alpha158_v1/full158/
```

结果摘要：

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

Holdout 保持不变：

```text
alpha158_CNTN5
alpha158_IMAX5
alpha158_RANK5
```

## 5. 输出文件

```text
alpha158_judgement_board.csv
alpha158_redundancy_clusters.csv
alpha158_redundancy_cluster_members.csv
alpha158_judgement_report.md
```

最重要的下游入口：

```text
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_board.csv
```

## 6. 结果解释

`strong_signal` 和 `consistent_signal` 是下一步候选池冻结的优先研究对象。

`redundant` 表示该因子与某个代表因子高度相关，并不代表公式错误或完全无价值。它的作用是防止后续训练集被高度重复的价量因子污染。

`high_turnover` 表示信号可能需要更高交易频率或更强交易成本约束，暂不应直接进入组合回测。

`unstable_context` 表示不同指数分组下信号方向或强度不稳定，需要继续拆分研究。

`review` 和 `weak_signal` 暂时只保留观察。

## 7. 下一步

下一阶段建议做候选池冻结：

1. 从 `alpha158_judgement_board.csv` 读取 `strong_signal` 和 `consistent_signal`。
2. 保留每个 redundancy cluster 的代表因子。
3. 排除 `holdout`、`weak_signal`、`review`、`high_turnover`、`unstable_context` 和非代表 `redundant`。
4. 输出 Alpha158 candidate pool v1，作为后续小规模组合回测接口的输入。

在候选池冻结完成前，仍不建议继续扩张 `ta` 或 Alpha101。先把现有 Alpha158 的筛选闭环打稳，更适合当前项目节奏。
