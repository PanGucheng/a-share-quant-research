# Research Model Protocol V1.1 Closure

> 逻辑阶段：PR #5A.1
> 模型训练：未启动
> Test payload reads：0

## 修复范围

V1.1 在 V1 的 authority、split-specific allowlist、统计和 preprocessing
协议上完成以下闭环：

1. 模型入口只接受 hash-verified `artifact_manifest.json`；
2. 任意 readiness CSV 不能独立授权训练；
3. Canary 与正式协议绑定相同的 config、parent、selection 和 policy SHA；
4. target 只在最终合格模型样本内计算每日横截面排名；
5. 所有 development 日期均生成样本资格 receipt，包括零有效样本日期；
6. validation 使用 train-only preprocessing transform；
7. Matrix partition 从权威 Matrix v4 manifest 与 resolved config 解析；
8. 三个 split 完成完整 development-only dry-run。

## 分阶段验证

```text
5 factors × 20 train dates × 10 validation dates
→ split_001 full 45 factors × 20/10 dates
→ split_001/002/003 full train + validation
```

完整 dry-run 使用日期分批与 runtime spool。Runtime parquet 不提交 Git，仓库只保留：

```text
sample_eligibility_receipt.csv
validation_transform_receipt.csv
partition_source_receipt.csv
resource_summary.csv
access_audit.csv
contract_status.csv
```

## Readiness

只有下列入口可授权研究训练：

```text
outputs/research_model_protocol_v1_1/current/artifact_manifest.json
```

入口验证 stage、artifact status、lineage、code cleanliness、所有 output hash、
critical contracts、readiness experiment class 和研究/生产披露字段。

V1.1 完成后允许：

```text
experiment_class = post_observation_research
research_model_protocol_ready = true
research_model_input_ready = true
research_model_training_ready = true
```

继续禁止：

```text
authoritative_oos
production
paper
live
authoritative_execution
unbiased_final_estimate
```

PR #5B 仍需单独冻结 Ridge/Elastic Net candidate、solver receipt、资源预算与首次
fit review bundle；V1.1 readiness 不会自动启动模型。
