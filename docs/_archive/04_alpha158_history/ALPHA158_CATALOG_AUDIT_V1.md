# Qlib Alpha158 Catalog Audit V1

本文档记录 Qlib Alpha158 因子池扩张的第一步：只做来源抽取、字段审计和 catalog metadata，不直接进入因子评价。

## 1. 目标

本阶段服务于后续大规模因子筛选，但仍遵守当前项目边界：

- 不替换 Qlib baseline。
- 不改 Alphalens Reloaded 或 jqfactor_analyzer 的评价口径。
- 不训练新模型。
- 不绕过 `data_quality -> tradability -> factor evaluation`。
- 不把未经 adapter 审计的因子标记为可运行。

## 2. 来源

Alpha158 公式来自本地 Qlib 源码：

```text
E:/qlib_prj/qlib_clone/qlib/contrib/data/loader.py
```

抽取函数：

```text
qlib.contrib.data.loader.Alpha158DL.get_feature_config
```

当前审计时的 Qlib commit：

```text
d5379c520f66a39953bad76234a7019a72796fd0
```

license：

```text
MIT
```

## 3. 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha158_catalog_v1.py
```

输出目录：

```text
outputs/factor_catalog_alpha158_v1/
```

## 4. 审计结果

本轮抽取结果：

```text
Alpha158 formulas: 158
field_status=available: 158
field_status=missing: 0
```

分类分布：

| category | factor_count |
| --- | ---: |
| kbar | 9 |
| price_volume_lag | 4 |
| rolling_price | 75 |
| price_momentum_balance | 30 |
| price_volume_correlation | 10 |
| volume_liquidity | 30 |

字段使用与 provider 覆盖：

| field | factor_count | provider_presence_rate |
| --- | ---: | ---: |
| close | 117 | 1.0 |
| high | 28 | 1.0 |
| low | 28 | 1.0 |
| open | 9 | 1.0 |
| volume | 40 | 1.0 |
| vwap | 1 | 1.0 |

这说明当前 derived provider 已经具备 Alpha158 所需的价量字段。

## 5. 输出文件

```text
outputs/factor_catalog_alpha158_v1/provider_field_presence.csv
outputs/factor_catalog_alpha158_v1/alpha158_formula_inventory.csv
outputs/factor_catalog_alpha158_v1/alpha158_field_usage.csv
outputs/factor_catalog_alpha158_v1/alpha158_catalog_all.yaml
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first_batch.yaml
outputs/factor_catalog_alpha158_v1/alpha158_audit_report.md
```

`alpha158_catalog_first_batch.yaml` 包含首批 20 个 metadata 条目：

```text
KMID, KLEN, KMID2, KUP, KUP2, KLOW, KLOW2, KSFT, KSFT2,
OPEN0, HIGH0, LOW0, VWAP0,
ROC5, ROC10, ROC20, ROC30, ROC60,
MA5, MA10
```

这些条目当前设置为：

```yaml
enabled: false
runnable: false
compute_adapter: qlib_expression_adapter_pending
```

原因是字段审计通过只说明公式依赖可满足，还不代表表达式计算 adapter、缓存策略、标签对齐和 V4 输入转换已经验证。

## 6. Metadata Dry-Run

可以用 batch runner 只做 metadata 规划：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_metadata_smoke.yaml --dry-run
```

该命令生成 batch manifest，但不执行 V4 评价。

如果去掉 `--dry-run`，runner 会阻止执行 `runnable: false` 的 Alpha158 条目，这是预期行为。

## 7. 下一步

下一段应实现 Qlib expression adapter：

1. 从 `alpha158_formula_inventory.csv` 读取公式。
2. 使用 Qlib `D.features` 计算选定表达式。
3. 与现有基础字段、T+1 label、data_quality 和 tradability 输出对齐。
4. 只对首批 20 个 Alpha158 因子跑 V4 smoke。
5. smoke 通过后，再把对应 catalog 条目改为 `enabled: true` 和 `runnable: true`。

在 adapter 通过前，Alpha158 只处于“已审计 metadata 来源”，不能进入正式筛选。
