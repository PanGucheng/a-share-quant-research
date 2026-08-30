# Historical Frontier Admission V1

> 状态：`MARKET-LEVEL QUALIFICATION COMPLETE / EXTENDED MATRIX NOT GENERATED`。本轮把前一阶段的代表性 probe 扩展为按上市 cohort 与存续状态分层的市场 canary；未读取 model outcomes，未修改 Research Protocol V2、Factor Universe V2 definitions、frozen Matrix、Strategy V1 或 Forward Track。

## 数据源与方法

- Tushare `stock_basic`（listed/delisted active canary）、`daily_basic`、`moneyflow`、`daily`、`adj_factor` 与四类 statements；每次请求均保留 network receipt。
- Community Qlib `instruments/all.txt` 用作 lifecycle interval 对照；不是把当前 stock_basic 快照冒充历史 vintage。
- 28 个 issuer 按 listing cohort × listed/delisted 分层抽样；48 个 2010–2021 季度代表交易日用于市场横截面 coverage。
- 复权审计只对 pre-2010 cohort 做 bounded canary，检查 daily/adj_factor overlap、正值、重复日期与 factor-change events。

## 观测 frontier 与 blockers

- `daily_basic`：稳定连续尾部候选 `2016-07-01`；全窗口最低 coverage `0.849`，因此早期低覆盖仍不能整体准入。
- `moneyflow`：稳定连续尾部候选 `2016-07-01`；全窗口最低 coverage `0.489`（2010-01-04 明显缺口）。
- Fundamental PIT：按 issuer listing date 修正分母后 2010–2017 period coverage 的 p10 为 `1.000`，但 `13` 个 issuer 的 `fina_indicator` response 触及 100-row cap；revision/duplicate rows 普遍存在，故 PIT vintage 仍 blocked。
- Lifecycle/survivorship：Qlib 与 stock_basic 交集最低 `0.892`；且 stock_basic 是 current snapshot，历史 vintage 未被证明，故 gate blocked。
- Corporate-action/adjustment：12 个 pre-2010 issuer 的 factor 均为正、无重复日期且 daily overlap 完整；该 bounded pass 不能抵消 PIT/lifecycle blocker。

## Factor Universe V2 与 Matrix 决策

`factor_family_frontier.csv` 将每个定义映射到 price-volume、daily_basic、moneyflow 或 fundamental PIT 依赖。Qlib technical price history 仍可追溯至 2000-01-04，但这只是 long-history core 的能力证据，不是 Full V2 的 admitted start。Full Factor Universe V2 common frontier 必须取所有依赖层、PIT、lifecycle 与 adjustment 的交集；本轮结论为 `not_admitted`。因此没有生成 extended Matrix，也不存在需要与旧 2021+ Matrix 做 overlap 一致性声明的新 artifact。

## 复现与治理

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_historical_frontier_admission_v1.py --stage all
```

网络 receipts 保存在 `network_receipts.csv`，token 不写入任何 artifact；失败请求原样保留。`qualification_decision.csv` 是机器可读 gate 结果。

```text
extended_matrix_generated = false
formal_structured_ml_competition_started = false
research_protocol_v2_changed = false
factor_universe_v2_definitions_changed = false
frozen_matrix_changed = false
strategy_v1_changed = false
forward_track_changed = false
model_outcomes_read = false
```
