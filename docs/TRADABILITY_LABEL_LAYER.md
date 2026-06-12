# 统一 A 股可交易性标签层

本模块是后续因子研究、组合约束、回测约束的统一可交易性入口。它只读取 Qlib provider 和数据质量诊断输出，不修改 Qlib 源码、不修改原始数据、不训练模型、不回测。

## 输入

默认配置：

```text
tradability/config.yaml
```

默认数据源：

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
```

默认股票池和时间：

```text
market: all_stock_shsz_liquid2000
start: 2021-01-01
end: 2023-12-29
```

模块还读取数据质量诊断输出目录：

```text
outputs/data_quality_tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29
```

核心数据质量文件缺失时直接报错；可选文件缺失时记录 warning。

## 输出

固定输出目录：

```text
outputs/tradability/<market>_<start>_<end>/
```

固定文件：

```text
tradability_labels.csv
summary.csv
instrument_scores.csv
date_coverage.csv
reason_counts.csv
tradability_report.md
resolved_config.yaml
run.log
```

## 字段

主表包含：

```text
datetime
instrument
is_suspended
suspension_status
is_limit_up
is_limit_down
is_one_price_limit_up
is_one_price_limit_down
limit_status
liquidity_source
liquidity_value
liquidity_bucket
is_low_liquidity
listed_days
is_new_listing
has_price_anomaly
has_volume_anomaly
has_core_missing
data_quality_status
can_buy
can_sell
tradability_score
disabled_reason
```

`disabled_reason` 使用 `|` 分隔，允许多个原因并存。

## 运行

先确保对应数据质量输出存在，然后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_tradability_labels.ps1
```

验证：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\validate_tradability_outputs.py --output-dir outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29
```

## 与其他模块关系

- 数据质量模块负责发现异常，本模块消费其结构化输出。
- 因子研究模块后续应使用 `can_buy`、`can_sell`、`tradability_score` 做样本过滤。
- 组合约束模块后续应使用 `disabled_reason` 和流动性标签做可买卖约束。
- 回测约束后续应统一读取本模块输出，不再重复实现停牌、涨跌停、流动性和数据异常过滤。
