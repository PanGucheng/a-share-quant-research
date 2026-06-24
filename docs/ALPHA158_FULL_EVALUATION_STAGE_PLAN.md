# Alpha158 Full Evaluation Stage Plan

本文档规划 Alpha158 全量 158 个因子的评价扩张阶段。它延续 first20 阶段的工程原则：优先复用 Qlib 原始表达式和开源评价体系，不手写公式、不改指标口径、不训练模型。

## 1. 当前状态

已完成：

- Alpha158 158 个公式来源审计，字段全部可用。
- First20 expression adapter、V4 smoke、context validation 和 batch runner 已通过。
- First20 catalog 已晋升为 `enabled: true`、`runnable: true`。

待完成：

- 生成覆盖 158 个因子的 full expression frame。
- 将 remaining138 因子分批进入 V4 评价。
- 将 first20 与 remaining138 的评价结果合并成 Alpha158 全量候选池输入。

## 2. 阶段目标

```text
alpha158_catalog_all.yaml
  -> full158 expression frame
  -> first20 runnable catalog + remaining138 pending catalog
  -> remaining138 resumable batch evaluation
  -> remaining138 promotion
  -> full158 compact metric index and screening input
```

本阶段完成后，应具备：

- 一个可复现的 full158 expression frame。
- remaining138 的可恢复 batch 评价配置。
- first20 不重复跑，remaining138 单独补齐。
- 全量结果仍保留 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 和 context 多体系并列输出。

## 3. 非目标

- 不做模型训练。
- 不新增自研综合评分。
- 不改 Alphalens Reloaded、jqfactor_analyzer 或 Qlib eval 的指标口径。
- 不做行业/市值中性，直到 point-in-time 行业和市值数据源确认。
- 不进入实盘或自动下单。

## 4. 新增文件

```text
configs/alpha158_expression_adapter_full_v1.yaml
configs/factor_evaluation_v4_alpha158_remaining_batch_base.yaml
configs/factor_evaluation_batch_v1_alpha158_remaining138.yaml
scripts/prepare_alpha158_full_stage_catalogs_v1.py
docs/ALPHA158_FULL_EVALUATION_STAGE_PLAN.md
```

预计输出：

```text
outputs/alpha158_expression_frame_v1/full158_main_research/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_pending.yaml
outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_mixed.yaml
outputs/factor_evaluation_batch_v1/alpha158_remaining138/
```

## 5. 执行顺序

1. 生成 remaining138 pending catalog 和 full158 mixed catalog。
2. 构建 full158 expression frame，按 5 个因子一批调用 Qlib 表达式，避免一次性宽表计算过重。
3. 运行 expression validation，继续用 `KMID` 和 `KLEN` 做手工公式核对，并检查 158 列覆盖率。
4. 对 remaining138 batch runner 做 dry-run，确认 batch 切分、配置生成和断点续跑 metadata。
5. 真实运行 remaining138 batch evaluation。
6. 用 context validator 检查每个完成 batch。
7. 通过后再晋升 remaining138 catalog，不覆盖 first20 runnable catalog。
8. 最后生成 full158 compact summary，供后续 screening 使用。

## 6. 验收标准

- [x] remaining138 pending catalog 生成成功，数量为 138。
- [x] full158 expression frame 生成成功，因子数量为 158。
- [x] full158 expression validation 通过。
- [x] remaining138 batch dry-run 生成 14 个 batch，每批最多 10 个因子。
- [x] remaining138 batch_001 真实 smoke 通过。
- [ ] remaining138 真实 batch 可断点续跑。
- [ ] 每个完成 batch 的 context validator 无 failed。
- [ ] 通过评价后再生成 remaining138 runnable catalog。
- [ ] full158 汇总只合并原始评价结果，不生成综合分。

## 7. 本阶段风险

| risk | mitigation |
| --- | --- |
| full158 expression frame 体积较大 | `expression.batch_size: 20`，并忽略 `factor_frame*.pkl` |
| remaining138 运行时间长 | batch size 10，resume true，中断后跳过已完成 batch |
| 重复评价 first20 浪费时间 | first20 结果复用，只跑 remaining138 |
| catalog 状态混乱 | first20 runnable、remaining138 pending、full158 mixed 三份 catalog 分开 |
| 单窗口结果被误用 | 只作为候选筛选输入，不直接用于实盘或模型训练 |

## 8. 当前执行状态

已完成：

```text
remaining138 pending catalog: 138 factors
full158 mixed catalog: 158 factors
full158 expression frame rows: 1,603,860
full158 expression factors: 158
full158 expression validation: pass
coverage min: 0.994231
coverage median: 0.996867
remaining138 dry-run batches: 14
remaining138 batch_001 real run: pass
batch_001 elapsed: 912.061 seconds
batch_001 open-source metric rows: 180
batch_001 context metric rows: 1,920
batch_001 context validation: pass
```

工程调整：

- `expression.batch_size` 已加入 expression adapter。
- full158 配置使用 `batch_size: 5`，每个 chunk 有 stdout 进度。
- batch runner 增加 `--max-batches`，支持先跑一个真实 smoke batch。
- remaining138 配置显式使用 `execution.allow_non_runnable_external: true`，仅用于外部 adapter 因子的预晋升评价。

已验证的真实 smoke：

```text
batch_001 factors:
  alpha158_MA20, alpha158_MA30, alpha158_MA60,
  alpha158_STD5, alpha158_STD10, alpha158_STD20, alpha158_STD30, alpha158_STD60,
  alpha158_BETA5, alpha158_BETA10

evaluator status:
  alphalens_reloaded: pass 10
  jqfactor_analyzer: partial_pass 10
  qlib_eval: pass 10

context status:
  pass: 120
  skipped_non_informative: 40

known jqfactor partial steps:
  factor_alpha_beta: 10
  factor_returns: 10
```

下一步：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_remaining138.yaml
```

runner 会跳过已完成的 `batch_001`，继续执行 `batch_002` 到 `batch_014`。
