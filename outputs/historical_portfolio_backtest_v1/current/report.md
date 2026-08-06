# Historical Portfolio Backtest V1 Report

## 结论

- 冻结 LightGBM 信号在两个 development split 的平均净收益为 `29.10%`；结果是已观察历史 test 上的个人研究证据。
- 固定开发规则选中 `P01`（Top K `50`，每 `5` 个交易日调仓）。
- development 平均年化超额收益为 `61.70%`，平均成本拖累为 `7.01%`。
- split_003 holdout 净收益 `3.57%`、年化超额 `-30.24%`、最大回撤 `-4.33%`。
- holdout 对 development 方向结论的支持：`false`；无论结果正负，参数均未改变。
- 高换手是否是主要问题：`true`。当前优先优化方向：数据与可交易性，其次是组合换手和成本。

## 分层解释

模型预测质量由既有 prediction-level Rank IC 证明，本 PR 未重训或重建 prediction。
组合构建只比较预注册的六组等权 Top K/调仓间隔；执行成本包含佣金、印花税和
10 bps 滑点。gross return 是在同一次执行上把累计实现成本加回 NAV 的近似值，
不是另跑的零成本组合。

历史可交易性仍来自代理字段；stale valuation 只用过去最后有效 close 保持研究 NAV
连续，不恢复交易资格。SH000985 的相对指标只使用双方收益同时有效的 common dates。
因此 `historical_execution_approximate=true`、`unbiased_final_estimate=false`、
`production_model_selected=false`、`live_trading_ready=false`。

## 下一步

可以把冻结的 `P01` 组合规则作为 PR #20B forward prediction 的初始
paper-portfolio 候选，但必须另行冻结 forward 组合协议，并等待真实新日期；本报告
本身不构成生产或实盘授权。
