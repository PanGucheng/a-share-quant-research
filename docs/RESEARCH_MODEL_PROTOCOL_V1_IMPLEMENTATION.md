# Research Model Protocol V1 实施说明

> 逻辑阶段：PR #5A  
> 实验类别：`post_observation_research`  
> 正式模型训练：未启动

## 实施范围

本阶段只发布统一模型输入、统计、预处理和防泄漏协议，不训练 Ridge、
Elastic Net 或 LightGBM。权威直接上游固定为：

```text
date_split_semantics_v1
research_selection_lineage_closure_v1
full_research_feature_matrix_v4
full_research_labels_v2
point_in_time_universe_v2
```

旧 `purged_walk_forward_v1/full_research_669` 只保留为日期包装层登记的 legacy
payload，禁止成为模型 artifact 的直接 parent。

## 已冻结协议

- 三个 split 独立使用 45、46、52 个因子，不生成 union 或 intersection；
- 训练目标为 `daily_cross_sectional_rank_centered`；
- 主验证指标为 `mean_daily_rank_ic`；
- 选参 tie-break 固定为 ICIR、coverage、低复杂度、canonical SHA；
- 搜索阶段 preprocessing 只 fit outer train；
- 最终模型必须在 outer train+validation 重新 fit；
- 线性模型使用 daily-equal weighted median 与 scaler；
- 全空列、近零方差列和 feature-order 变化全部 fail-closed；
- Ridge `solver=auto` 禁止进入正式 candidate；
- LightGBM 禁用 early stopping，轮数只允许 100/200/400/800 checkpoint；
- test runner 必须先验证 immutable pre-test freeze。

## Canary

Canary 范围固定为：

```text
split_001
5 factors
20 train dates
10 validation dates
0 test reads
```

Canary 验证 canonical feature order、exact key join、train-only preprocessing、
row-order invariance、feature-order fail-closed、fold overlap 拒绝和 pre-freeze
test loader 拒绝。详细机器证据位于：

```text
outputs/research_model_protocol_v1/canary/
outputs/research_model_protocol_v1/current/
```

## Readiness 边界

PR #5A 完成时只允许研究级模型入口：

```text
research_model_protocol_ready = true
research_model_input_ready = true
research_model_training_ready = true
research_model_hard_stop_active = false
```

以下状态继续保持：

```text
production_model_hard_stop_active = true
production_model_selected = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
authoritative_execution = false
unbiased_final_estimate = false
```

PR #5B 在首次真实 fit 前仍需独立冻结 Ridge/Elastic Net candidate、solver receipt、
资源预算、run review bundle 和 pre-test release 机制。
