# RQAlpha Integration Migration Audit / PoC

2026-09-16；独立基线 `main@e06f9d1`；分支 `audit/rqalpha-poc-20260916`。

本轮用户授权是迁移审计和小型 PoC，不是正式迁移。附件中的预研能力清单按待验证假设处理。
主目录 `E:\qlib_prj\qlib_baseline` 的 LightGBM 长跑保持运行；不修改其代码、配置、环境或输出。
工作仅在 `E:\qlib_prj\qlib_rqalpha_audit`，环境为 `E:\qlib_prj\rqalpha_poc_env`。

**RQALPHA INTEGRATION FEASIBLE WITH ADAPTERS / PRODUCTION MIGRATION NOT ACCEPTED。**

交付入口：

- [审计结论与十五项问题](../reports/rqalpha_integration_audit_v1/REPORT.md)
- [Replace / Adapt / Keep Matrix](../reports/rqalpha_integration_audit_v1/MATRIX.md)
- [Canary 结果与限制](../reports/rqalpha_integration_audit_v1/CANARIES.md)
- [环境、许可证与 Ricequant Skills](../reports/rqalpha_integration_audit_v1/ENVIRONMENT_SKILLS.md)
- [独立 PoC 代码](../experiments/rqalpha_poc/adapter.py)及[运行入口](../experiments/rqalpha_poc/run.ps1)

采用顺序是：固定官方版本和源码 → 读源码及 tests → 复用封存输入做 bounded fixture →
原生 RQAlpha account/broker/matcher canary → 独立标量断言与反例 → 迁移边界结论。
没有为了通过而修改 RQAlpha core，也没有引入 RQData / RQAMS。

推荐职责划分：Qlib 继续负责数据、因子、训练、预测、时间边界与研究 receipts；现有 portfolio policy
产生带 signal-session 的意图，跨夜队列在下一 session 的 open 阶段提交。执行 adapter 先做已有
identity/state/event/evidence 检查，再向 RQAlpha DataSource 和费用接口提供允许消费的数据。
RQAlpha 管理订单、成交、现金、持仓与日终记账。外层保留 R1/R2/R3、未结权益和完整 checkpoint。
这是一项架构建议，不是已发布的 authoritative economic backend。

本轮不读取模型、prediction 或收益，不运行策略候选，不访问 2024+ 研究值。
源码、软件版本与公告元数据日期不属于开启 2024+ 市场研究。所有实际市场值只来自固定
2020-08-24 已验 canary；事件条款为已封存 2016/2017/2020 SH600000 记录；其余价格与账户为 synthetic。
禁止以工程现金/股数断言推断策略经济表现。完成后只推送独立分支，停止等待审核，不合并 main。
