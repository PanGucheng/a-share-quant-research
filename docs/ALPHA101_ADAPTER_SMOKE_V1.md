# Alpha101 Adapter Smoke V1

本文档记录 KunQuant Alpha101 从 metadata source audit 进入可运行 smoke adapter 的最小闭环。本阶段目标是验证外部公式源接入工具链，而不是研究这 5 个因子的策略效果。

## 定位

- 复用 KunQuant pandas reference 实现，不手写 Alpha101 公式。
- 不替换 Qlib baseline。
- 不训练新模型。
- 不调整具体策略。
- 不修改 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 的评价口径。
- 因子评价仍必须经过现有 `data_quality` 和 `tradability` 前置过滤。

## 来源

```text
tmp/reference_repos/KunQuant
source commit: d4b9e61f729df347730aa921b539b9df3c3fe36d
source file: tests/KunTestUtil/ref_alpha101.py
license: Apache-2.0
```

当前使用 `outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml` 中已审计的 metadata。KunQuant 当前可解析 82 个 Alpha101 公式；本 smoke 只选择 5 个字段依赖较简单的公式验证工具链。

## 运行

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\alpha101_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_smoke_catalog_entries_v1.py --config configs\alpha101_factor_smoke_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 输出

```text
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_inventory.csv
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_catalog_smoke.yaml
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_catalog_smoke_passed.yaml
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_smoke_promotion_audit.csv
outputs/factor_evaluation_v4/alpha101_smoke_v1/evaluator_status.csv
outputs/factor_evaluation_v4/alpha101_smoke_v1/open_source_metric_index.csv
outputs/factor_evaluation_v4/alpha101_smoke_v1/factor_evaluation_v4_report.md
```

大体积 `factor_frame*.pkl` 只作为本地可再生成缓存，不进入 Git。

## 当前结果

```text
selected smoke factors: 5
adapter rows: 89,000
adapter coverage: 94.23% to 99.37%
V4 Alphalens status: pass for 5 factors
V4 Qlib eval status: pass for 5 factors
V4 JQFactor status: partial_pass for 5 factors
promotion: 5 promoted
```

JQFactor 的 partial 来自已知 `factor_returns` / `factor_alpha_beta` index-name 兼容问题；这两个步骤被记录在 `factor_failure_reasons.csv`，不会中断批量流程。Promotion 仍要求 Alphalens Reloaded 和 Qlib eval 通过。

## Multi-Source 影响

Alpha101 smoke-passed catalog 已进入 `configs/multi_source_screening_v1.yaml`：

```text
source_count: 3
screening rows: 242
Alpha158 strict rows: 155
TA strict rows: 77
Alpha101 strict rows: 5
new source strict rows: 82
alpha candidates: 14
```

Alpha101 因子当前和 TA 一样保守放入 `monitor`，不会直接当作 alpha signal。下一阶段应扩展 Alpha101 batch 和更多开源因子源，并在 multi-source 输出上建设通用 judgement 层。
