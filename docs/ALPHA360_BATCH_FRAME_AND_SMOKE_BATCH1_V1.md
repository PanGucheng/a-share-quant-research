# Alpha360 Batch Frame and Smoke Batch1 V1

状态：已完成小批验证。

本阶段目标是生成 Alpha360 358 因子的 batch factor frame，并执行一个真实 batch runner 小批次，验证从 candidate catalog 到 V4 子进程的端到端路径。

## 1. 运行命令

生成 batch factor frame：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_batch358_v1.yaml
```

恢复 dry-run 计划：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358.yaml --dry-run
```

执行独立 smoke batch1：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358_smoke.yaml
```

## 2. Batch Factor Frame

```text
output_dir: outputs/alpha360_expression_frame_v1/batch358
factor count: 358
rows: 88,797
instruments: 500
date range: 2020-10-09 to 2021-06-30
chunk count: 18
chunk size: 20
```

`factor_frame.pkl` 仍是大体积缓存，已由 `.gitignore` 排除。Git 只保留：

```text
expression_table.csv
expression_frame_summary.csv
expression_frame_sample.csv
expression_frame_manifest.json
expression_frame_report.md
```

## 3. Dry-Run Root

```text
output_root: outputs/factor_evaluation_batch_v1/alpha360_candidate358_batch1
status: planned
planned batches: 72
selected factors: 358
```

该目录只保存 dry-run manifest、selected catalog 和 generated configs。

## 4. Smoke Batch1 Root

```text
output_root: outputs/factor_evaluation_batch_v1/alpha360_candidate358_smoke_batch1
batch_id: batch_001
status: pass
returncode: 0
factor_count: 5
factors: alpha360_CLOSE59, alpha360_CLOSE58, alpha360_CLOSE57, alpha360_CLOSE56, alpha360_CLOSE55
evaluator_status_rows: 15
failure_rows: 10
metric_rows: 90
context_metric_rows: 0
```

`failure_rows` 仍来自 jqfactor_analyzer 的已知 partial，和 V3.29 smoke 一致。本阶段不修改开源评价体系定义。

## 5. Readiness Contract

新增合同：

```text
alpha360_batch_expression_table rows: 358
alpha360_batch_expression_summary rows: 358
alpha360_batch_smoke_manifest rows: 1
alpha360_batch_smoke_output_summary rows: 1
overall readiness: ready
```

## 6. 下一步

1. 继续以 resume 模式执行 Alpha360 剩余 batch。
2. 每次可先限制 `--max-batches`，避免长任务中断后难以定位。
3. 批量完成后生成 Alpha360 batch metric index summary。
4. 按既有 promotion/holdout 规则生成 promoted catalog，再进入 multi-source screening 和 judgement。
