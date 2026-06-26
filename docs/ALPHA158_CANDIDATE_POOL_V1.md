# Alpha158 Candidate Pool V1

本文档是 V3.13 的具体计划与执行记录。它承接 Alpha158 judgement layer，将可解释判断结果冻结成后续组合回测可以读取的候选池快照。

本阶段目标是接口固化，不是训练模型、调策略或做实盘。

## 1. 目标

建立如下链路：

```text
alpha158_judgement_board
  -> alpha158_candidate_pool
  -> 后续 Alpha158 portfolio smoke
```

候选池必须满足：

- 可版本化。
- 可复现。
- 保留排除原因。
- 下游可直接读取 `alpha_candidate`。
- 不改写 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 原始指标。
- 不引入自研综合分。

## 2. 输入

```text
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_board.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_redundancy_clusters.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_redundancy_cluster_members.csv
```

## 3. 入池规则

纳入 `alpha_candidate`：

```text
judgement_label in {strong_signal, consistent_signal}
evaluation_gate == strict_screening_input
is_redundant == false
high_turnover == false
unstable_context == false
```

排除或观察：

```text
holdout             -> holdout
redundant           -> excluded_redundant
high_turnover       -> excluded_high_turnover
unstable_context    -> excluded_unstable_context
weak_signal         -> monitor
review              -> monitor
```

说明：

- `low_monotonicity` 仅作为 warning 保留，不在 V1 中单独剔除。
- 冗余簇代表因子可以入池，非代表因子不能入池。
- 当前 candidate pool 是研究候选，不是交易信号。

## 4. 实现文件

```text
configs/factor_candidate_pool_alpha158_v1.yaml
factor_research/alpha158_candidate_pool.py
scripts/run_alpha158_candidate_pool_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_pool_v1.py --config configs\factor_candidate_pool_alpha158_v1.yaml
```

## 5. 输出

```text
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.json
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool_report.md
```

## 6. 验收标准

- [x] 候选池完整角色表包含 158 行。
- [x] `alpha_candidate` 只来自 `strong_signal` 和 `consistent_signal`。
- [x] `alpha_candidate` 不包含 holdout。
- [x] `alpha_candidate` 不包含非代表冗余因子。
- [x] `alpha_candidate` 不包含 high_turnover 或 unstable_context。
- [x] 输出 CSV、JSON 和 Markdown 报告。
- [x] README 和总计划文档记录当前状态。

## 7. 当前结果

角色分布：

```text
alpha_candidate: 14
excluded_redundant: 55
excluded_high_turnover: 33
excluded_unstable_context: 16
monitor: 37
holdout: 3
```

当前 `alpha_candidate`：

```text
alpha158_MIN60      strong_signal
alpha158_QTLD60     strong_signal
alpha158_ROC60      strong_signal
alpha158_MIN30      strong_signal
alpha158_ROC30      strong_signal
alpha158_QTLD30     strong_signal
alpha158_IMIN60     strong_signal
alpha158_MIN10      strong_signal
alpha158_IMIN30     strong_signal
alpha158_MIN5       strong_signal
alpha158_IMIN20     consistent_signal
alpha158_QTLD10     consistent_signal
alpha158_VSUMN60    consistent_signal
alpha158_ROC10      consistent_signal
```

说明：

- `alpha158_MIN5`、`alpha158_QTLD10`、`alpha158_VSUMN60`、`alpha158_ROC10` 带有 `low_monotonicity` warning，V1 暂保留为候选，但后续 portfolio smoke 必须在报告中显式标记。
- `alpha158_CNTN5`、`alpha158_IMAX5`、`alpha158_RANK5` 继续保持 holdout。
- `excluded_redundant`、`excluded_high_turnover`、`excluded_unstable_context` 仍保留在完整角色表中，便于回溯，不作为下游默认 alpha 输入。

## 8. 下一步

V3.13 完成后进入：

```text
V3.14 Alpha158 Candidate Portfolio Smoke
```

下一步只验证接口和约束：

```text
candidate pool
  -> signal construction
  -> low-frequency portfolio smoke
  -> report
```

不急着训练模型，不急着扩展 `ta` 或 Alpha101。
