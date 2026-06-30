# Alpha360 Batch Promotion And Multi-Source V1

本阶段把 Qlib 原生 Alpha360 从 batch frame / smoke batch 状态推进到完整 batch V4、promotion/holdout、multi-source screening 和 multi-source judgement。范围仍然只限因子研究工具链：不训练模型、不改策略、不实盘、不修改 Alphalens Reloaded / jqfactor_analyzer / Qlib eval 的评价定义。

## 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358_execution.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha360_batch_catalog_entries_v1.py --config configs\alpha360_factor_batch_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_judgement_v1.py --config configs\multi_source_judgement_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## Alpha360 Batch V4

```text
batch manifests: 72
source factors: 358
metric index rows: 6,444
Alphalens Reloaded: 358 pass
Qlib eval: 358 pass
jqfactor_analyzer: 358 partial_pass
```

jqfactor_analyzer 的 partial 来自已知索引名冲突：

```text
factor_alpha_beta: The name date occurs multiple times, use a level number
factor_returns: The name date occurs multiple times, use a level number
```

该状态只记录为外部 evaluator 的局部失败，不改评价口径，也不阻断 Alphalens Reloaded 与 Qlib eval 已通过的 batch promotion。

## Promotion / Holdout

```text
batch promoted: 358
V4 batch holdout: 0
adapter holdout: 2
all holdout: 2
```

两个 adapter holdout 仍是前序识别出的恒等/近恒等因子：

```text
alpha360_CLOSE0
alpha360_VOLUME0
```

关键输出：

```text
outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml
outputs/factor_catalog_alpha360_v1/alpha360_catalog_holdout2.yaml
outputs/factor_catalog_alpha360_v1/alpha360_batch_promotion_audit.csv
outputs/factor_catalog_alpha360_v1/alpha360_batch_promotion_report.md
outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/alpha360_candidate358_metric_index.csv
```

## Multi-Source Screening

Alpha360 promoted catalog 已加入 `configs/multi_source_screening_v1.yaml`。当前通用筛选池结果：

```text
screening rows: 679
sources: 4
Alpha158 strict rows: 155
TA strict rows: 77
Alpha101 strict rows: 64
Alpha360 strict rows: 358
holdouts: 25
alpha candidates: 14
contract status: pass
```

新来源 promoted 因子在 screening 层仍保守放入 `monitor`，不会绕过 judgement 直接成为交易信号。

## Multi-Source Judgement

当前 judgement 输出：

```text
judgement board rows: 679
research candidates: 342
new-source alpha probes: 328
TA probes: 15
Alpha101 probes: 14
Alpha360 probes: 299
holdouts: 25
contract status: pass
```

`new_source_alpha_probe` 是后续研究队列，不是默认模型输入，也不是默认组合输入。Alpha360 的 299 个 probes 下一步需要经过相关性、暴露、稳定性、分段 OOS 和 portfolio smoke 后，才考虑进入训练或组合回测。

## Readiness

`factor_research_toolchain_readiness_v1` 已把 Alpha360 batch / promotion / multi-source 结果纳入 required output contracts，并把多源行数门槛提升到 600 行以上：

```text
overall_status: ready
total_runnable: 669
new_source_runnable: 499
multi_source_screening_input rows: 679
multi_source_judgement_board rows: 679
multi_source_new_source_alpha_probes rows: 328
alpha360_candidate358_metric_index rows: 6,444
alpha360_batch_promoted_catalog rows: 358
```

## 边界

- Alpha360 公式来自 Qlib `Alpha360DL.get_feature_config`，本项目不手写替代公式。
- 评价结果来自已有 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 共存体系。
- data_quality / tradability 仍是 V4 evaluator 的前置约束，不允许新因子绕过。
- 本阶段只处理因子研究工具链，不训练模型、不改 baseline、不做实盘。

## 下一步

1. 为 328 个 `new_source_alpha_probe` 增加相关性、暴露、稳定性和 portfolio smoke 诊断。
2. 继续参考 FactorTest、jqfactor_analyzer、qlib_factor_platform 等开源项目，补齐行业/风格/Barra 暴露数据能力。
3. 继续接入更多开源因子源，但必须沿用 source audit、adapter、V4 batch、promotion/holdout、multi-source screening、multi-source judgement 的路径。
