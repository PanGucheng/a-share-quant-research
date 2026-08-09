# Historical Portfolio Backtest V1

> ARCHIVED / HISTORICAL：历史回测已完成，不是当前 Forward 运行入口。

## 1. 目标与证据边界

PR #24 只把已经冻结的三份 LightGBM historical test prediction 接入仓库现有
Qlib Exchange / SimulatorExecutor，回答信号在固定费用和基本 A 股约束下能否转化为
组合收益。证据等级固定为：

```text
personal_research_grade
post_observation_research
non_authoritative_historical_execution
```

历史 test 已被观察，且历史停牌、涨跌停与证券生命周期并非完整权威数据，因此
`unbiased_final_estimate`、`authoritative_historical_execution_ready`、
`production_model_selected`、`live_trading_ready` 始终为 false。这些边界不阻止个人
研究级组合回测完成，也不授权实盘。

## 2. 冻结输入与禁止事项

唯一预测入口是
`outputs/research_lightgbm_v1/current/prediction_receipt.csv` 中的 split_001—003
parquet。运行前必须复验文件存在、SHA256、schema、LightGBM method、唯一主键、
prediction coverage 与对应 split 的精确 test dates。缺失或哈希错误立即停止；禁止
重训模型、重建预测、改变因子或扩大候选参数。

市场数据直接复用 Market Cache V3，保留已修正的 Community volume/amount 单位、
动态 A 股整手、方向性涨跌停代理、停牌、参与率与现有 terminal approximation。
Qlib 固定 Python 3.10、commit `d5379c5...` 和现有 provider。基准固定
`SH000985`，不存在时阻断，不自动替换。

## 3. 冻结组合实验

组合只允许 long-only、Top K、等权、95% risk degree 与 target-delta。信号在 t 日
收盘后可见，仅在 t+1 开盘执行。每个 split 独立使用 1,000 万元初始资金，不继承
持仓。候选仅为：

| Portfolio | Top K | 调仓间隔 |
|---|---:|---:|
| P01 | 50 | 5 |
| P02 | 100 | 5 |
| P03 | 200 | 5 |
| P04 | 50 | 20 |
| P05 | 100 | 20 |
| P06 | 200 | 20 |

调仓序号从每个 split 的第一个可执行日算起：索引 0、N、2N……生成新 Top K；
非调仓日保持上次调仓后的实际持仓，不生成新目标订单，也不读取新 score 改变股票
集合。费用、10 bps 滑点、
5% 参与率、T+1 与整手参数固定，不做搜索。

split_001、split_002 是 development；按两段平均净超额收益信息比率、平均净年化
超额收益、更低换手、更少持仓、portfolio_id 字典序选择唯一规则。split_003 是
holdout，只运行被选规则一次，不参与选择，结果为负也不得改规则。

## 4. 历史估值与基准缺口

严格 stale 估值若因已持仓股票超过 20 日无有效价格而中断，允许仅为保持研究净值
连续而把该股票最后一个历史有效 close 向后携带。该 fallback 不恢复交易资格，
也不改变 signal；必须报告日期、股票数、最大 stale days 和股票名单，并继续标记
`historical_execution_approximate=true`、`tradability_source_complete=false`。

SH000985 在 provider 中必须真实存在。若 split 内部分日期缺 close，禁止未来值
回填；基准相对指标只使用 portfolio 与基准收益同时有效的 common dates，并报告
coverage/common-period 起点。组合自身全区间净收益仍按完整 split 报告。

## 5. 实施顺序与输出

```text
冻结输入审计
→ split_001 前20交易日 P02 smoke
→ 6规则 × 2 development splits
→ 冻结 selected_portfolio_rule.json
→ selected rule × split_003 单次 holdout
→ 汇总、图表、普通语言报告
```

根目录只保存配置、输入回执、development/holdout/性能/成本/估值汇总、daily/monthly
结果、三张图和报告；订单、成交、持仓等明细放入 ignored runtime。报告必须区分
模型预测质量、组合构建、执行成本和历史数据近似，不因正收益宣称可实盘。

## 6. Definition of Done

```text
historical_portfolio_backtest_complete = true
portfolio_candidate_scan_complete = true
portfolio_rule_selected = P01
portfolio_holdout_evaluated = true
portfolio_holdout_supported_relative_advantage = false
historical_execution_approximate = true

model_retrained = false
predictions_regenerated = false
features_changed = false
unbiased_final_estimate = false
production_model_selected = false
live_trading_ready = false
```

阶段成功标准是冻结输入、固定扫描、holdout 和报告完整，而不是收益必须为正。

## 7. 完成回执（2026-08-06）

输入审计、20 日 smoke、12 个 development 场景、开发选择冻结与唯一一次 holdout
均已完成。286 项仓库测试与 25 个既有 validator 在实现冻结前通过。开发集只使用
split_001/002，按预注册排序选中 P01（Top 50、5 日调仓）；冻结回执明确记录
`holdout_execution_count_at_selection=0` 和
`holdout_performance_read_count_at_selection=0`。

P01 的 development 平均净收益为 29.10%、平均年化超额为 61.70%，平均成本拖累
7.01%。单次 split_003 holdout 的净收益为 3.57%，但相对 SH000985 的年化超额
为 -30.24%、信息比率 -1.86、最大回撤 -4.33%，成本拖累 5.80%。因此 holdout
没有支持开发期相对优势；结果已原样保留，没有改规则或增加候选。
即使把记录成本近似加回，holdout gross return 约 9.37%，仍低于基准 19.19%；
成本不是相对失利的唯一原因。实际持仓的 stale fallback 日期数为 0，因此首要后续
研究方向是市场状态稳定性与风格暴露，第二方向才是换手和成本；历史可交易性数据
继续作为可信度限制保留，但当前没有证据表明它是 holdout 相对失利的主要原因。

最终 artifact 为
`historical_portfolio_backtest_v1:de86a138a69854bed9a0810465e1a791e63d902fe356c124b6d1c414332f5e93`，
所有完成合同为 pass。历史可交易性代理仍不完整，故本阶段只形成 approximate、
post-observation 的个人研究证据，生产选择、无偏最终估计和实盘资格继续为 false。
