# TA Factor Adapter Smoke V1

本阶段开始接入第一个非 Alpha158 开源因子源：`bukosabino/ta`。

目标不是马上大规模筛选 TA 因子，而是先证明以下链路成立：

1. Qlib OHLCV 面板可以按 instrument 转换成 `ta` 所需的 pandas DataFrame。
2. TA 公式直接从本地开源仓库调用，不在项目内重写。
3. 产出的因子列可以回到项目统一的 `datetime / instrument / factor` 框架。
4. look-ahead 风险列和标签重叠列在进入评价前被排除。
5. 生成临时 catalog，但先保持 disabled / non-runnable，等待 V4 smoke 评价后再提升。

## 1. 来源

```text
source_project: ta
local_path: tmp/reference_repos/ta
source_file: ta/wrapper.py
source_function: add_all_ta_features
commit: a890410710a6e483c9ba08da7f3dd5089e4b9dff
license: MIT
```

## 2. 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_ta_factor_adapter_smoke_v1.py --config configs\ta_factor_adapter_smoke_v1.yaml
```

## 3. 输出

```text
outputs/ta_factor_adapter_v1/smoke/factor_frame.pkl
outputs/ta_factor_adapter_v1/smoke/ta_factor_inventory.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_frame_summary.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_frame_sample.csv
outputs/ta_factor_adapter_v1/smoke/ta_selected_smoke_factors.csv
outputs/ta_factor_adapter_v1/smoke/ta_adapter_manifest.json
outputs/ta_factor_adapter_v1/smoke/ta_adapter_report.md
```

## 4. 准入规则

当前第一版排除：

| pattern | reason |
| --- | --- |
| `ta_trend_visual_ichimoku*` | upstream `visual=True` 会向后平移值，不适合直接作为 point-in-time 因子。 |
| `ta_others_*` | 日收益、对数日收益、累计收益与项目 label / basic return 因子重叠。 |
| `ta_volume_vpt` | upstream 当前依赖 pandas `pct_change` 默认填充行为，先排除。 |
| `ta_volume_nvi` | upstream 当前依赖 pandas `pct_change` 默认填充行为，先排除。 |

当前保留：

- volume
- volatility
- trend
- momentum

所有 catalog entries 先保持：

```yaml
enabled: false
runnable: false
stage: ta_adapter_smoke_generated
```

只有 V4 smoke 评价通过后，才允许进入 promoted runnable catalog。

## 5. V4 smoke

最小 smoke 评价配置：

```text
configs/ta_factor_evaluation_smoke_v1.yaml
```

初始选择 5 个代表性因子：

```text
ta_momentum_rsi
ta_momentum_roc
ta_volatility_bbw
ta_trend_macd_diff
ta_volume_cmf
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\ta_factor_evaluation_smoke_v1.yaml
```

这个 smoke 仍然使用 data_quality 和 tradability 输出作为前置过滤，不改变现有开源评价口径。

## 6. Smoke promotion

V4 smoke 通过后，使用单独 promotion 脚本生成 smoke-level passed catalog：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_smoke_catalog_entries_v1.py --config configs\ta_factor_smoke_promotion_v1.yaml
```

输出：

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke_passed.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_smoke_promotion_audit.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_smoke_promotion_report.md
```

该 catalog 只说明 5 个 smoke 因子已经可作为后续批量评估接口样例，不代表 79 个 eligible TA 因子都已经通过评价。
