# Qlib Exchange Integration V1

## 状态

PR #2 已完成 Qlib Exchange / Executor 的正式执行基础设施、合成对账和本地真实小样本验证。当前门禁为：

```text
qlib_exchange_infrastructure_ready = true
qlib_exchange_synthetic_ready = true
execution_reconciliation_ready = true
qlib_exchange_reference_ready = false
model_training_started = false
```

前三项已满足 PR #2 → PR #3 的执行基础设施门槛。`qlib_exchange_reference_ready=false` 是真实能力阻断：当前样本股票池按区间完整覆盖筛选，并非 PIT universe；历史停牌和方向性涨跌停来自 `volume/change` 代理，而非权威 PIT 标签。

## 已实现范围

- 固定 Python 3.10、Qlib commit `d5379c520f66a39953bad76234a7019a72796fd0` 和 provider 的环境契约；不升级 Python，不引入 `mlfinpy` 仓库依赖。
- 统一 signal schema：日期、股票、score、method、artifact、profile 和 run family。
- 统一 market schema：原始价格、原始股数成交量、方向性可交易标记、复权因子和执行价格。
- adapter 边界将原始价格/股数转换为 Qlib 复权价格/数量，输出时再还原；公开 artifact 不混用两套单位。
- Qlib `Exchange`、`SimulatorExecutor`、等权 TopK target-delta strategy 和完整交易日账户链。
- 100 股买入整手、分项佣金/印花税/滑点、最低佣金、停牌/无量/无价格、方向性涨跌停、严格 T+1、成交量参与率、partial/unfilled/rejected 审计。
- 完整交易日历、现金非负、持仓/账户守恒和目标仓位主动增减。
- 独立 reference engine 与 Qlib 的无约束合成精确对账；unknown semantic difference 为 0。
- Manifest v2、上游 artifact id、配置/输出哈希、clean-code/freshness 校验和独立 readiness。
- GitHub Actions 保留原轻量门禁，并新增固定 Qlib commit 的真实运行时集成测试。

## 验证结果

合成链使用 5 只股票和 10 个交易日，覆盖 score → strategy → order → exchange → fill → position → account。订单、成交、现金、净值和持仓与 reference engine 在 `atol=1e-8`、`rtol=1e-10` 下完全一致。

本地真实样本使用 30 只沪深股票、80 个交易日、20 日透明动量信号，在 t 日收盘观察、t+1 日开盘执行。结果为 79 个账户日、993 笔订单、981 笔成交、473 笔部分成交和 12 笔拒单；执行关键 contract 全部通过。该运行用于执行语义证据，不用于声明信号有效性或投资收益。

## 复现顺序

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_qlib_environment_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_qlib_exchange_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\reconcile_execution_engines_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_qlib_exchange_reference_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\report_qlib_exchange_readiness_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\validate_execution_reconciliation_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\validate_qlib_exchange_v1.py
```

主要证据：

```text
outputs/qlib_environment_v1/current/
outputs/qlib_exchange_v1/synthetic/
outputs/execution_reconciliation_v1/current/
outputs/qlib_exchange_v1/local_reference/
outputs/qlib_exchange_readiness_v1/current/
```

## 下一阶段边界

下一阶段为 PR #3：50–100 个分层抽样因子的 full-research 特征矩阵试运行。必须复用本执行链，并补入真实 PIT universe artifact。权威历史可交易性标签未补齐前，不得把 `qlib_exchange_reference_ready` 强行改为 true。仍不得直接运行 669 因子或启动 Ridge、Elastic Net、LightGBM 训练。
