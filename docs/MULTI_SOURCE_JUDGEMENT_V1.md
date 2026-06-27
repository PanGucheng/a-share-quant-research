# Multi-Source Judgement V1

本文档记录 V3.26：在现有 multi-source screening 之后增加通用研究分层。目标是让 Alpha158、TA、Alpha101 和后续开源因子源共用一个 judgement board，但不替换已有 Qlib 主线、不训练新模型、不改 Alphalens / jqfactor / Qlib eval 的评价定义。

## 定位

本阶段只做因子研究工具链：

- 读取已有 `multi_source_screening_input.csv`。
- 保留 Alpha158 已有 candidate-pool 角色。
- 对 TA / Alpha101 promoted monitor 因子增加 `new_source_alpha_probe`、`new_source_monitor`、`new_source_data_watch`、`new_source_mixed_signal` 等研究分层。
- `new_source_alpha_probe` 只是后续研究队列，不是交易信号，也不会成为默认组合或模型输入。

## 输入

```text
outputs/multi_source_screening_v1/current/multi_source_screening_input.csv
```

该输入已经复用了 data_quality、tradeability、source audit、adapter、V4 batch、promotion/holdout 和 open-source evaluator metric index。

## 配置与脚本

```text
configs/multi_source_judgement_v1.yaml
factor_research/multi_source_judgement.py
scripts/run_multi_source_judgement_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_judgement_v1.py --config configs\multi_source_judgement_v1.yaml
```

## V1 规则

规则只使用现有开源评价输出，不重新定义 evaluator：

```text
IC-like metrics: Alphalens Reloaded mean_information_coefficient, jqfactor_analyzer mean_information_coefficient
IR-like metrics: Qlib eval information_ratio
data gates: coverage, missing_rate
status gates: upstream screening_gate and promotion/holdout
```

默认阈值：

```text
min_probe_coverage: 0.90
max_probe_missing_rate: 0.10
weak_abs_ic: 0.015
consistent_abs_ic: 0.03
strong_abs_ic: 0.05
consistent_abs_qlib_ir: 3.0
strong_abs_qlib_ir: 4.0
min_direction_agreement_ratio: 0.67
strong_direction_agreement_ratio: 0.83
```

## 输出

```text
outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv
outputs/multi_source_judgement_v1/current/multi_source_research_candidates.csv
outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_monitor.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_holdouts.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_contract_status.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_pool.json
outputs/multi_source_judgement_v1/current/multi_source_judgement_report.md
```

## 当前结果

```text
judgement board rows: 319
research candidates: 43
new-source alpha probes: 29
TA probes: 15
Alpha101 probes: 14
holdouts: 23
contract status: pass
readiness generic_multi_source_judgement: pass
```

角色分布：

```text
alpha158 alpha_candidate: 14
alpha158 excluded/monitor/holdout: 144
ta new_source_alpha_probe: 15
ta new_source_data_watch: 43
ta new_source_mixed_signal: 13
ta new_source_monitor: 6
ta holdout: 2
alpha101 new_source_alpha_probe: 14
alpha101 new_source_data_watch: 16
alpha101 new_source_mixed_signal: 7
alpha101 new_source_monitor: 27
alpha101 holdout: 18
```

合同检查：

```text
row_alignment: pass
alpha158_role_preserved: pass
new_source_probe_count: pass
holdout_not_research_included: pass
new_source_not_downstream_default: pass
strict_new_source_metrics: pass
```

## 与后续阶段的关系

这一步完成后，后续扩张因子池时可以走统一路径：

```text
source audit -> adapter smoke -> V4 batch -> promotion/holdout -> multi-source screening -> multi-source judgement
```

只有当 `new_source_alpha_probe` 经过更多时段、更多数据源、相关性/暴露/组合 smoke 后，才考虑进入训练或组合回测输入。
