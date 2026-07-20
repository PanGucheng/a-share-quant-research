# Qlib Exchange / Executor 语义审计 V1

> 审计日期：2026-07-20  
> 阶段：PR #2 / Qlib Exchange Integration V1  
> 结论：环境与主要接口可用于集成；T+1、费用分项、标准化拒单原因和可审计输出必须由项目适配层实现。

## 1. 审计边界

本审计只回答 Qlib 当前源码实际提供什么，以及项目需要在哪里增加适配器。它不产生新因子、不改变筛选阈值、不运行 669 因子、不启动模型训练，也不修改 Qlib 源码仓库。

本地审计对象：

| 项目 | 已解析值 | 状态 |
| --- | --- | --- |
| Python | `3.10.19` | pass |
| pyqlib | `0.1.dev6` | pass |
| 安装方式 | editable install | pass |
| Qlib source | `E:/qlib_prj/qlib_clone` | pass |
| Qlib commit | `d5379c520f66a39953bad76234a7019a72796fd0` | pass |
| Qlib provider | `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived` | pass |
| provider calendars / instruments / features | present | pass |
| Qlib runtime code dirty | false | pass |
| Qlib source worktree dirty | true：仅 `examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158_csi500.yaml` | warning |

示例配置的用户改动不在 `qlib/**` 运行时代码中，不阻塞本次审计；后续不得覆盖、还原或提交该用户改动。PR #2 的环境 Manifest 必须同时记录完整 worktree dirty 和 runtime-code dirty，只有后者阻塞 readiness。

## 2. 当前调用链

Qlib 的公开日频回测入口为：

```text
qlib.backtest.backtest
  -> get_strategy_executor
  -> Account + Exchange + Strategy + SimulatorExecutor
  -> collect_data_loop
  -> strategy.generate_trade_decision
  -> executor.collect_data
  -> exchange.deal_order
  -> Account / Position / portfolio metrics / indicators
```

关键接口事实：

1. `SignalWCache` 接受 pandas Series/DataFrame，索引可转换为 `datetime × instrument`；策略按交易日历读取前一交易步 signal。
2. `WeightStrategyBase` 默认读取前一交易步 signal，并调用 order generator 把目标权重转换成订单。
3. `Exchange.generate_order_for_target_amount_position()` 使用 `target_amount - current_amount` 生成买卖差额订单，能够覆盖退出、减持、增持和新进入。
4. `SimulatorExecutor` 支持 serial / parallel 顺序；serial 模式允许先卖后买并复用现金。
5. `TradeCalendarManager` 使用 Qlib `Cal.calendar(..., future=True)` 构造完整交易步，不应只输出 signal date。
6. `backtest()` 返回 portfolio metrics 和 indicator metrics；逐笔原始请求、拒单原因和费用分项仍需额外捕获。

## 3. Exchange 原生语义

| 能力 | 源码行为 | 分类 | PR #2 决策 |
| --- | --- | --- | --- |
| deal price | 支持统一价格或买卖不同表达式 | 原生支持 | V1 固定 previous-day signal、next-day open execution |
| trade unit | `trade_unit`，中国市场默认可设 100 | 原生支持 | 买入整手；清仓既有零股单独审计 |
| 涨跌停 | float threshold 或 `(buy_limit_expr, sell_limit_expr)` | 原生支持 | 使用方向性显式字段，不使用全部 False 默认值 |
| 停牌 | `$close` 缺失会进入不可交易状态 | 原生支持 | 同时要求 suspended / volume / price contract 一致 |
| volume limit | 支持 current / cumulative、buy / sell / all | 原生支持 | 每股票每交易日累计参与率门禁 |
| cash clipping | 买入会按现金和费用裁剪 | 原生支持 | 标准化为 partial / unfilled / rejected |
| position clipping | 卖出不会超过当前持仓 | 原生支持 | 再叠加 T+1 sellable shares |
| target delta | 原生生成目标量与当前量的差额订单 | 原生支持 | Qlib 与 reference engine 统一使用 |
| open/close cost | 支持方向费率、最低费用和 impact cost | 配置可实现 | 不直接作为最终 A股分项费用模型 |
| portfolio metrics | 逐 bar 更新现金、持仓、收益和指标 | 原生支持 | 重新标准化并做守恒复核 |

### 3.1 价格与停牌

`Exchange` 查询 buy price、sell price、`$close`、`$change`、`$factor` 和 `$volume`。`$close` 缺失会被视为 suspension。执行价查询在部分模式下可回退到 close；本项目不得静默使用该回退：缺少配置的执行价时必须拒单并记录 `missing_execution_price`。

### 3.2 涨跌停

float threshold 会根据 `$change` 生成方向性 `limit_buy` / `limit_sell`，tuple expression 可直接提供买卖限制字段。由于 A 股不同板块和历史 ST 状态可能对应不同阈值，真实样本优先使用经过外部验证的 direction-specific flags。若只能使用统一阈值，只能作为 synthetic/reference approximation，并阻塞 `qlib_exchange_reference_ready`。

### 3.3 成交量

Qlib 能按 current 或 cumulative volume expression 裁剪成交量，并由 executor 维护当日已成交数量。项目 contract 仍需独立验证：

```text
sum(abs(executed_shares)) <= raw_volume * max_participation_rate
```

未成交部分必须保留原始 requested、executed 和 unfilled 数量，不能只依赖 fulfill-rate 汇总。

## 4. 必须由适配层实现的语义

### 4.1 股票 T+1

`BasePosition` 当前只有 `ST_CASH` / `ST_NO`，settlement 仅延迟现金，不维护股票的当日可卖数量。因此 Qlib 默认行为不能声明为严格 A 股 T+1。

PR #2 必须维护：

```text
opening_sellable_shares
intraday_bought_shares
intraday_sold_shares
closing_total_shares
```

卖单可成交数量上限为当日 opening sellable 减去当日已卖数量；当日买入只在下一交易日进入 sellable。超额部分记录为 `t_plus_one` rejected/unfilled。该逻辑必须有同日顺序订单测试，不能用 `hold_thresh` 代替。

### 4.2 费用分项

Qlib 原生交易返回单一 trade cost，无法直接证明：

- 最低佣金只作用于 commission；
- 印花税只作用于 sell；
- slippage 已计入成交价格且未被重复扣减。

项目适配层使用：

```text
commission = max(minimum_commission, gross_value * commission_rate)
stamp_tax = gross_value * sell_tax_rate if side == sell else 0
fill_price = base_execution_price * (1 +/- slippage_bps / 10000)
slippage_cost = abs(fill_price - base_execution_price) * executed_shares
cash_fee = commission + stamp_tax
implementation_cost = cash_fee + slippage_cost
```

Qlib Account 扣除 `cash_fee`，slippage 只通过 fill price 影响现金，不能再次扣除。

### 4.3 Prepared market quote

Qlib `extra_quote` 主要用于补充报价，不能可靠表达“用已校验表完全替换 provider 行情”。项目将使用 Exchange 子类接收经过 schema 校验的 prepared quote，并覆盖报价加载入口；不得 patch Qlib 源码。

prepared quote 必须包含价格、factor、volume、方向性 limit 和 suspension 状态。任何自动补默认值都必须在 contract 中可见。

### 4.4 审计型 Executor

标准 indicator 不包含完整的拒单原因和费用分项。项目 Executor wrapper 必须捕获：

- 原始目标和订单；
- 请求量、整手后数量、成交量和未成交量；
- base price、fill price、gross value；
- commission、stamp tax、slippage cost；
- partial / unfilled / rejected 状态及稳定 reason enum；
- 每日 opening/closing cash、position、NAV 和 accounting error。

## 5. 统一输入与时序

Signal 统一为：

```text
datetime, instrument, score, method, signal_artifact_id,
profile_name, profile_type, research_run_family_id
```

Market 统一为：

```text
datetime, instrument, open, close, volume, amount,
can_buy, can_sell, limit_up, limit_down, suspended,
factor, change, execution_price
```

项目 schema 中 price 为原始价格、volume/订单/持仓为原始股数；进入 Qlib 时按
`adjusted_price = original_price * factor`、`adjusted_amount = raw_shares / factor`
转换，离开 Qlib 后还原。参与率始终以原始股数复核，避免把复权数量与原始成交量混用。

规则固定为：

- 日期为无时区的中国交易日；
- instrument 规范为 `SH600000` / `SZ000001`；
- T 日 signal 只允许在下一交易日执行；
- tradable 行必须有有限且大于零的执行价、close、volume 和 factor；
- suspended 行必须 `can_buy=false` 且 `can_sell=false`；
- 同一 artifact 内 profile 和 run family 必须一致；
- 所有输入先验证 freshness 和 upstream artifact ID。

## 6. 估值与完整日历

Qlib calendar 是执行输出的权威日期轴。无 signal 日不下单，但仍必须输出 daily accounting 和 positions。

持仓估值规则：

1. 优先使用当日有效 close；
2. 否则使用最近有效 close；
3. 最多允许连续 20 个交易日陈旧；
4. 超出上限或从未有有效 close 时阻断；
5. 禁止零价估值。

## 7. 对账边界

无约束、无成本、固定价格场景中，Qlib 与 reference engine 的订单方向、数量必须完全一致；现金、持仓价值、NAV、换手和收益使用 `atol=1e-8`、`rtol=1e-10`。

受约束场景的差异只能归入：

```text
calendar_semantics
price_semantics
order_generation
trade_constraint
cost_model
rounding
valuation
unknown
```

任何 `unknown` 都阻断 `execution_reconciliation_ready`。

## 8. Readiness 结论

审计完成时的初始状态已由后续实现提升为：

```text
qlib_environment_resolved = true
qlib_exchange_infrastructure_ready = true
qlib_exchange_synthetic_ready = true
execution_reconciliation_ready = true
qlib_exchange_reference_ready = false
```

前三个 execution readiness 已由代码、合成场景和零 unknown 对账 contract 证明。30 股票真实小样本的执行关键契约已通过；完整 reference readiness 仍要求 PIT universe 和权威历史方向性 tradability 证据。

## 9. 实施约束

- 固定 Python 3.10，不升级环境。
- 固定并记录 Qlib commit，不把 mlfinpy 加入依赖。
- Qlib 源码仓库只读，所有扩展位于 `qlib_integration/`。
- PR #2 不产生优质因子、不调整研究阈值、不训练模型、不运行 669 因子。
- 先完成最小合成链，再逐项增加 A 股约束，最后进行真实样本试运行。
