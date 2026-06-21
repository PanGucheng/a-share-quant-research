# 因子研究上下文 V1

## 1. 目的

`factor_research.context` 为因子评价提供可复现、时点正确的市场上下文。它不替换 Qlib provider，也不改变现有 `data_quality`、`tradability` 和多套开源评价体系，只把 provider 中已经存在的数据转换为统一研究输入。

当前 V1 包含：

- point-in-time 股票池成员资格；
- 上市年龄代理与年龄分组；
- CSI300、CSI500、CSI1000 基准日收益和 T+1 前瞻收益。

## 2. 数据与时点规则

### 股票池成员资格

直接读取 Qlib `instruments/*.txt` 的 `instrument/start/end` 区间。某股票只在 `start <= date <= end` 时属于该股票池，区间两端均包含。不得用研究窗口末日的静态成分股回填历史。

V1 配置覆盖：

- `csi300`
- `csi500`
- `csi1000`
- `all_stock_shsz_liquid2000`

### 上市年龄

当前 provider 没有独立的官方上市日期字段，因此使用 `all_stock_shsz` 中每只股票最早的可用区间起点作为 `listing_date_proxy`。

该字段适合用于新股过滤和年龄切片，但存在左截断限制：如果 provider 的历史晚于真实上市日，代理年龄会偏小。后续接入可靠的 point-in-time 证券主数据后，应保留同一接口并替换数据源。

### 基准收益

基准收盘价仍由 Qlib `D.features` 读取。对日期 `t`：

```text
daily_return = close(t) / close(t-1) - 1
forward_10d_t1 = close(t+11) / close(t+1) - 1
forward_20d_t1 = close(t+21) / close(t+1) - 1
```

前瞻收益只作为评价标签，不可作为日期 `t` 的因子输入。构建器会在研究窗口后额外加载数据，使窗口末端在数据充足时仍能得到前瞻基准收益。

## 3. 运行与验证

配置：

```text
configs/factor_context_v1.yaml
```

构建：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_factor_context_v1.py
```

验证：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_context_v1.py
```

默认输出：

```text
outputs/factor_context_v1/main_research_2021_2023/
```

其中：

- `benchmark_returns.csv`：基准行情和收益；
- `universe_membership_counts.csv`：各交易日股票池数量；
- `universe_membership_asof.csv`：窗口末日成员快照；
- `listing_age_asof.csv`：窗口末日上市年龄快照；
- `factor_context_v1_report.md`：覆盖情况摘要；
- `context_run.json`：本次运行配置快照。

验证器检查区间端点、收益公式、重复键、末日快照一致性和上市年龄计算。它是构建后的必跑步骤。

## 4. 与现有主线的关系

推荐的数据流：

```text
Qlib provider
  -> data_quality
  -> tradability labels
  -> factor values and forward labels
  -> factor_research.context
  -> Alphalens / jqfactor / Qlib evaluate / current evaluator
  -> factor screening
  -> later portfolio backtest
```

硬约束保持不变：因子评价先使用 `tradability` 输出过滤不可交易样本，再附加 point-in-time 股票池、上市年龄和基准上下文。上下文适配器不能绕过数据诊断与可交易性约束。

## 5. 下一步

V4 evaluator 已接入 context V1。它直接调用 Alphalens Reloaded 和 jqfactor_analyzer 的 `by_group=True` 原始函数，并列输出：

- `index_segment` 和 `listing_age_bucket` 分组；
- 原始前瞻收益和基准超额前瞻收益；
- 分组 Rank IC、平均 Rank IC 和分位数组收益。
- `context_metric_index.csv` 可追溯长表索引，不包含综合分或自动排名。

快速验证：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_context_smoke.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_evaluation_context.py
```

当前 liquid2000 的可交易样本全部属于 `501_plus` 上市年龄组，因此该维度会标记为 `skipped_non_informative`，不会伪装成有效切片。换用包含新股且通过可交易性过滤的股票池后，同一接口会自动启用该维度。

下一步：

1. 调研有明确许可和时点语义的行业、市值数据源；在来源确认前不启用行业/市值中性化。
2. 将 context 输出纳入后续批量因子任务的统一结果索引。
3. 上下文切片验证完成后，再批量注册价量、技术和 Alpha158/Alpha101 因子。
