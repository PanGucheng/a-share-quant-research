# Alpha360 V4 Smoke V1

状态：已完成。

本阶段目标是验证 Alpha360 smoke 因子能进入现有 V4 多评价体系，并继续强制使用 data_quality 与 tradability 前置过滤。它不训练模型，不调整策略，不修改 Alphalens Reloaded、jqfactor_analyzer 或 Qlib eval 的指标定义。

## 1. 配置

```text
configs/factor_evaluation_v4_alpha360_smoke_v1.yaml
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_alpha360_smoke_v1.yaml
```

输出目录：

```text
outputs/factor_evaluation_v4/alpha360_smoke_v1
```

## 2. 输入边界

本次使用 V3.28 已生成的 adapter smoke frame：

```text
outputs/alpha360_expression_frame_v1/smoke/factor_frame.pkl
```

窗口：

```text
2021-01-01 to 2021-06-30
raw rows: 232,881
tradable rows: 133,958
external factor frame valid rows per factor: about 33,928 to 34,001
external factor coverage: about 25.33% to 25.38%
```

覆盖率低于未来 batch 的目标，是因为 adapter smoke frame 只取了 500 只股票。本阶段只验证评价链路是否可用；全量 batch 前需要生成覆盖完整 liquid2000 的 Alpha360 frame。

## 3. 因子范围

V4 smoke 从 24 个 adapter smoke 因子中排除了两个定义上恒等的归一化因子：

```text
excluded: alpha360_CLOSE0, alpha360_VOLUME0
evaluated factors: 22
```

排除原因：

- `alpha360_CLOSE0 = $close / $close`
- `alpha360_VOLUME0 = $volume / ($volume + 1e-12)`

这两个因子接近常数，不适合作为评价器 smoke。

## 4. 评价结果

```text
Alphalens Reloaded: 22 pass
Qlib eval: 22 pass
jqfactor_analyzer: 22 partial_pass
open_source_metric_index rows: 396
context_metric_index rows: 4,224
context_evaluator_status: 264 pass, 88 skipped_non_informative
```

`jqfactor_analyzer` 的 partial 来自 `factor_returns` 和 `factor_alpha_beta` 两个步骤：

```text
ValueError: The name date occurs multiple times, use a level number
```

本项目按“开源评价体系先共存”的原则记录该 partial，不改 jqfactor_analyzer 源码或指标口径。其 IC、mean IC、分组收益、换手等指标仍有输出。

## 5. Readiness Contract

V3.29 新增合同：

```text
alpha360_smoke_external_factor_summary rows: 22
alpha360_smoke_evaluator_status rows: 66
alpha360_smoke_metric_index rows: 396
alpha360_smoke_context_metric_index rows: 4,224
overall readiness: ready
```

## 6. 下一步

1. 生成 Alpha360 全量 batch candidate catalog。
2. 将 `alpha360_CLOSE0` 与 `alpha360_VOLUME0` 放入 adapter holdout。
3. 为剩余 358 个 Alpha360 因子生成完整 2021-2023 liquid2000 expression frame。
4. 使用 batch runner 做可恢复 V4 批量评价。
5. 通过 promotion/holdout 后再接入 multi-source screening 和 judgement。
