# Multi-Source Screening V1

本文档记录 V3.22 的通用多来源因子筛选契约。目标是让 Alpha158、TA、Alpha101 和后续因子源共用同一套筛选入口，而不是每接一个开源项目就写一条专用链路。

## 定位

本模块只做工具链 contract：

- 不训练模型。
- 不调整具体交易策略。
- 不替换 Qlib baseline。
- 不修改 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 等开源评价口径。
- 不把 TA 因子直接判成 alpha，只把 promoted 新来源放入 `monitor`，等待后续通用 judgement 规则。

## 输入

```text
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_screening_input.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.csv
outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_holdout2.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_frame_summary.csv
outputs/factor_evaluation_v4/ta_smoke_v1/open_source_metric_index.csv
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/ta_remaining74_metric_index.csv
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_catalog_smoke_passed.yaml
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_inventory.csv
outputs/factor_evaluation_v4/alpha101_smoke_v1/open_source_metric_index.csv
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_smoke_promotion_audit.csv
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_promoted64.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_holdout18.yaml
outputs/factor_evaluation_batch_v1/alpha101_candidate71_batch1/alpha101_candidate71_metric_index.csv
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_batch_promotion_audit.csv
```

## 配置与脚本

```text
configs/multi_source_screening_v1.yaml
factor_research/multi_source_screening.py
scripts/run_multi_source_screening_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
```

## 输出

```text
outputs/multi_source_screening_v1/current/multi_source_screening_input.csv
outputs/multi_source_screening_v1/current/multi_source_candidate_board.csv
outputs/multi_source_screening_v1/current/multi_source_candidate_pool.csv
outputs/multi_source_screening_v1/current/multi_source_alpha_candidates.csv
outputs/multi_source_screening_v1/current/multi_source_holdouts.csv
outputs/multi_source_screening_v1/current/multi_source_contract_status.csv
outputs/multi_source_screening_v1/current/multi_source_candidate_pool.json
outputs/multi_source_screening_v1/current/multi_source_screening_report.md
```

## 当前结果

```text
screening rows: 319
sources: 3
Alpha158 strict rows: 155
TA strict rows: 77
Alpha101 strict rows: 64
holdouts: 23
alpha candidates: 14
contract status: pass
```

角色分布：

```text
alpha158 alpha_candidate: 14
alpha158 monitor/excluded/holdout: 144
ta monitor: 77
ta holdout: 2
alpha101 monitor: 64
alpha101 holdout: 18
```

## 设计边界

Alpha158 已有完整 judgement 和 candidate-pool 输出，因此 V1 直接复用其角色。TA 已通过 adapter、V4 batch 和 promotion，Alpha101 已通过 82 公式 adapter、candidate71 V4 batch 和 promotion，但它们还没有与 Alpha158 等价的时序 ICIR、稳定性、冗余和主观 judgement 层，因此 V1 保守地把新来源 promoted 因子放入 `monitor`。

这一步的价值是让后续来源都能进入统一表结构：

```text
source manifest -> adapter audit -> V4 batch -> promotion/holdout -> multi-source screening -> candidate pool
```

## Readiness

V3.22 后，`factor_research_toolchain_readiness_v1` 的关键结果为：

```text
overall_status: ready
generic_multi_source_screening: pass
required_output_contracts: pass
total_runnable: 311
new_source_runnable: 141
```

这表示工具链已经可以支撑大规模多来源因子研究。下一阶段应继续接入更多开源因子源，例如更多公式库、基本面因子、行业/风格暴露数据，或者在现有 multi-source 输出上建设通用 judgement 层，而不是继续围绕 Alpha158 个案细调。
