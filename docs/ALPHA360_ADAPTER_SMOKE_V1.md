# Qlib Alpha360 Adapter Smoke V1

状态：已完成。

本阶段目标是把 Qlib 原生 `Alpha360DL.get_feature_config` 接入本项目的因子研究工具链，先完成 source audit 和 adapter smoke。它不替换现有 Qlib baseline，不训练新模型，不做实盘，不把 Alpha360 直接加入默认筛选或组合输入。

## 1. 来源

```text
source_project: qlib_alpha360
source_file: E:/qlib_prj/qlib_clone/qlib/contrib/data/loader.py
source_function: Alpha360DL.get_feature_config
source_commit: d5379c520f66a39953bad76234a7019a72796fd0
license: MIT
```

Alpha360 由 6 个字段族和 60 个窗口构成：

```text
CLOSE, OPEN, HIGH, LOW, VWAP, VOLUME
lag: 0..59
total formulas: 360
```

本项目不手写这些公式，而是从本地 Qlib 源码动态抽取，避免公式漂移。

## 2. 新增入口

```text
factor_research/qlib_alpha360.py
scripts/audit_alpha360_catalog_v1.py
scripts/build_alpha360_expression_frame_v1.py
configs/alpha360_catalog_audit_v1.yaml
configs/alpha360_expression_adapter_smoke_v1.yaml
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_catalog_v1.py --config configs\alpha360_catalog_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 3. 输出

```text
outputs/factor_catalog_alpha360_v1/alpha360_formula_inventory.csv
outputs/factor_catalog_alpha360_v1/alpha360_catalog_all.yaml
outputs/factor_catalog_alpha360_v1/alpha360_catalog_smoke.yaml
outputs/factor_catalog_alpha360_v1/alpha360_audit_report.md

outputs/alpha360_expression_frame_v1/smoke/expression_table.csv
outputs/alpha360_expression_frame_v1/smoke/expression_frame_summary.csv
outputs/alpha360_expression_frame_v1/smoke/expression_frame_sample.csv
outputs/alpha360_expression_frame_v1/smoke/expression_frame_manifest.json
outputs/alpha360_expression_frame_v1/smoke/expression_frame_report.md
```

`factor_frame.pkl` 是可复现的大体积缓存，已被 `.gitignore` 排除。

## 4. 验证结果

```text
source audit formulas: 360
missing provider fields: 0
smoke catalog entries: 24
smoke frame rows: 88,797
smoke instruments: 500
smoke factors: 24
date range: 2020-10-09 to 2021-06-30
```

smoke 选择覆盖 6 个字段族和 4 个窗口：

```text
CLOSE/OPEN/HIGH/LOW/VWAP/VOLUME
lag 0, 5, 20, 59
```

本次 24 个因子的覆盖率约为 99.31% 到 99.60%。缺失主要来自上市时间、停牌或窗口自然缺失。

## 5. Readiness Contract

V3.28 新增合同均已通过：

```text
alpha360_formula_inventory: pass, rows 360
alpha360_smoke_catalog: pass, rows 24
alpha360_smoke_expression_table: pass, rows 24
alpha360_smoke_expression_summary: pass, rows 24
overall readiness: ready
```

Alpha360 smoke catalog 当前是 disabled/non-runnable，因此不会绕过 V4 评价、promotion/holdout、multi-source screening 和 judgement。

## 6. 下一步

1. 基于 `outputs/alpha360_expression_frame_v1/smoke/factor_frame.pkl` 跑 Alpha360 V4 smoke。
2. 若 smoke 通过，生成 Alpha360 batch candidate catalog，覆盖 360 个公式。
3. 使用 batch runner 做可恢复 V4 批量评价。
4. 按既有规则生成 promoted/holdout catalog。
5. 仅把 promoted Alpha360 因子追加到 multi-source screening 和 judgement。

继续保持边界：不训练新模型，不调具体策略，不改变开源评价体系定义。
