# Output, Artifact And Report Policy

## 1. 目的

本政策定义未来新增内容的默认边界，目标是停止 `.gitignore` 随每个实验阶段继续
增长，同时完整保留既有研究证据。

Phase 4 已将该政策落实到 `.gitignore`，并建立 Git-tracked `reports/` 入口。变更只
影响未来新增文件；没有迁移、删除或停止跟踪任何历史文件。

## 2. 目录语义

### `outputs/` — Runtime And Generated Results

用于可重新生成的运行结果，包括：

- dataframe、intermediate matrix 和 batch partitions；
- logs、runtime manifests、临时图表；
- smoke、canary 和一次性诊断输出；
- 非冻结模型运行目录；
- 本地运行状态和中间输入。

未来默认不进入 Git。需要长期保存的内容应先判断其性质，再进入 `reports/`、
`artifacts/` 或明确的 Forward evidence 例外。

### `artifacts/` — Frozen Machine Objects

用于不可变、content-addressed、需要长期保存的机器对象，例如：

- frozen model binary；
- frozen preprocessing 参数；
- 模型读取所必需的固定 schema 或 metadata；
- 与内容 hash 和 size 绑定的关键研究对象。

Artifact 应通过内容地址或明确版本保持不可覆盖。普通 dataframe cache、完整运行
目录和一次性报告不应进入这里。

### `reports/` — Human-readable Evidence

Git-tracked 报告目录，用于：

- Markdown 结论与限制；
- 小型 CSV/JSON 汇总；
- 必要的小图和索引；
- 能解释已冻结 artifact 或 runtime output 的 compact evidence。

报告不能替代冻结模型、prediction receipt 或其 hash contract。

### `tmp/` — Cache And Scratch

用于：

- feature/factor cache；
- 下载、解包和构建 stage；
- 第三方参考仓库；
- 临时重放和等价测试；
- 可安全丢弃的 scratch files。

该目录始终默认忽略，不作为权威研究证据。

## 3. 特殊例外：Forward Evidence

Strategy V1 的 genuine forward evidence 具有不可回填的时间属性，不能简单视为可
重新生成的 output。现有路径继续作为兼容 authority：

```text
outputs/forward/predictions/<date>/prediction.csv
outputs/forward/predictions/<date>/prediction_receipt.json
outputs/forward/paper_portfolio/decisions/<date>/decision.json
outputs/forward/paper_portfolio/decisions/<date>/target_weights.csv
outputs/forward/status.json
outputs/forward/paper_portfolio/status.json
```

后续实际产生的 trades、positions 和 NAV 是否跟踪，继续服从已冻结 Paper Portfolio
定义和 append-only 要求。

以下 Forward 内容仍属于 runtime，不因为位于 `outputs/forward/` 就自动跟踪：

- `raw.csv`；
- `features.csv`；
- `prediction_pending_receipt.json`；
- `dry_run/`；
- 可重新计算的临时 metrics 或 adapter 文件。

## 4. 历史内容处理

仓库当前约 80% 的 tracked files 位于 `outputs/`。其中混合了 compact reports、
manifests、lineage、receipts 和历史运行结果。

处理原则是：

```text
Preserve historical evidence
+ Simplify future policy
```

明确禁止：

- 对历史 outputs 执行 `git rm --cached`；
- 批量 untrack、move、rename 或 delete；
- 仅为了目录整洁修改历史 manifest 中的路径或 hash；
- 将已观察结果重新包装为新的 OOS/forward evidence；
- 在本轮工程优化中做历史数据大扫除。

修改 `.gitignore` 不会让 Git 自动停止跟踪现有文件。Phase 4 必须先记录
`git ls-files outputs artifacts`，修改后验证集合完全一致。

## 5. 新内容的判断顺序

生成新文件时按以下顺序判断：

1. 是否可重新生成或只是运行中间结果？放入 `outputs/` 或 `tmp/`，默认忽略。
2. 是否为人类需要长期阅读的 compact conclusion？放入 `reports/`。
3. 是否为运行冻结策略所必需的不可变机器对象？放入 `artifacts/`。
4. 是否为真正当时生成、不可回填的 Forward evidence？使用现有 append-only
   Forward 路径和 receipt contract。
5. 如果以上均不满足，不应仅为了“留证”新增 tracked manifest 或 receipt。

## 6. Manifest、Receipt 与 Lineage

现有机制继续保留：

- frozen Strategy 和 Forward evidence 必需的 manifest/receipt/hash；
- Matrix v4、Labels v2 与历史研究依赖的 lineage；
- 已跟踪 outputs 中的历史证据。

未来普通研究默认使用简单 YAML、CSV/JSON、Markdown 和 Git。只有出现现有方法无法
解决的具体 correctness 或 durability 问题时，才增加新的治理对象。

## 7. Phase 4 验收结果

Phase 4 已完成以下验收：

- 删除 Alpha158/Alpha101/Alpha360/TA 等 stage-specific ignore 例外；
- 普通 outputs 与 tmp 默认忽略，无需为每个新实验修改 `.gitignore`；
- artifacts、reports 与 official Forward evidence 保持可跟踪；
- Forward raw/features/pending receipt/dry-run/metrics/runtime 继续忽略；
- `git check-ignore` 回归测试覆盖关键目录分类；
- 修改前后 tracked outputs/artifacts 集合完全一致，没有 delete、move 或 untrack。
