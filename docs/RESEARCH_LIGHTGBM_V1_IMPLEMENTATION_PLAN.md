# Research LightGBM V1 实施计划

> 逻辑阶段：PR #5C
> 实验类别：`post_observation_research`
> Historical test：已被历史研究观察
> Production model selection：禁止

## 1. 输入与边界

唯一训练入口为 `research_model_protocol_v1_1` 的 pass/complete artifact；PR #5B
的 3/3 Ridge、3/3 Elastic Net、零提前 test read 与 prediction schema 是阶段父证据。
辅助 Qlib 执行的 `SZ300280` 长期停牌估值阻断不进入 LightGBM 选参，也不授权
完整历史 NAV 比较。

本阶段不改变 45/46/52 split-specific feature order，不重新选择因子，不扩展
候选表，不使用 test 进行 early stopping、特征筛选或二次调参。

## 2. 冻结候选

机器配置为 `configs/research_lightgbm_v1.yaml`。四个结构行精确覆盖小/大叶子、
浅/深树、两档学习率、叶子最小样本、L1/L2、feature fraction 和 bagging
组合。每个结构行只在固定 checkpoint `[100, 200, 400, 800]` 评价：

```text
4 structural rows × 4 checkpoints = 16 candidates per split
```

每个候选 ID 同时绑定结构参数和 `num_boost_round`。禁止 early stopping；
trainer L2 只作健康诊断。官方选择顺序固定为：

```text
mean_daily_rank_ic
→ daily_rank_ic_ir
→ prediction_coverage
→ lower num_leaves
→ shallower max_depth
→ fewer boosting rounds
→ canonical candidate SHA
```

## 3. 分阶段运行

```text
静态配置/候选表测试
→ split_001 × 5 factors × 20 train dates × 2 structural rows canary
→ split_001 × 5 factors × 20 train dates × 16 candidates resource canary
→ split_001 全特征 × 16 candidates
→ 3 split 全特征 × 16 candidates
→ train+validation final refit
→ 3 份 pre-test freeze
→ single test release
```

首个 canary 只读 train；两个结构行各重复两次，要求 model string 与 train
prediction hash 完全一致、test read=0、峰值 RSS 不超过 4096 MiB。每个扩大步骤
均须先通过上一阶段资源、lineage、hash 和访问审计，不得直接跳到全量。

## 4. Test 与解释

开发完成前 test feature/label read 为 0。每个 split 的结构参数、轮数、环境、
训练数据、validation search、final model 和 preprocessing 全部进入
`pre_test_freeze_manifest.json`，之后只允许一次 test release。

Gain/split importance 或 SHAP 只能在 test release 后作为只读解释，不得反馈
候选、轮数、feature order 或同一历史 test 的模型重训。

## 5. 能力状态

PR #5C 完成只表示：

```text
LightGBM 3/3 split complete
lightgbm_model_research_complete = true
unknown_leakage_difference = 0
production_model_selected = false
authoritative_execution = false
unbiased_final_estimate = false
```

在长期停牌估值能力缺口解决前，五方法 prediction-level 科学比较可继续，但五
方法完整组合/NAV 比较必须保持 `blocked_execution_capability`。

## 6. Train-only Canary 回执

2026-07-26 首个 canary 已通过：

```text
split                    split_001 train only
samples / factors        39,886 / 5
structural rows          structure_01, structure_02
checkpoint / repeats     100 / 2
model hash stable        true
prediction hash stable   true
validation reads         0
test reads               0
peak RSS                 275.9 MiB
```

下一门禁是同一小样本上的完整 16 候选资源 canary；只有其通过后才允许
`split_001 × full features × 16 candidates`。

完整候选资源 canary 随后通过：

```text
candidate runs          16/16
samples / factors       39,886 / 5
validation reads        0
test reads              0
finite predictions      16/16
peak RSS                278.6 MiB
environment lock        exact match
```

因此下一步获准进入 `split_001 × 45 frozen features × 16 candidates` 的
train/validation 开发搜索；仍不得读取 test。

在正式运行前又完成 development pipeline smoke：

```text
scope                    split_001
train / validation       20 / 10 dates
factors / candidates     5 / 2
candidate frozen first   true
Rank IC selection        pass
validation mutation      pass
train+validation refit   pass
test reads               0
peak RSS                 242.2 MiB
```

至此数据投影、选参、mutation、final refit 和 freeze 路径均在小样本验证通过，
可以开始首个单 split 全量开发运行。该授权只覆盖 `split_001 × 45 frozen
features × 16 candidates`。
