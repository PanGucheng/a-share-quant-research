# Canary 结果

本轮没有 portfolio 策略研究。A/B/C 使用官方 `run_func`、DataProxy、Account、Broker、Matcher、
order API 和 settlement；D/E/F 使用原生账户/持仓事件组件。期望现金与数量为独立标量断言。
`sys_analyser` 关闭；无 NAV/CAGR/Sharpe 输出。RQAlpha 内部仍会维护其账户价值字段，这是原生账户运作所需。

源数据通过 [verify_inputs](../../experiments/rqalpha_poc/verify_inputs.py) 只读核验。
固定 C1 五个输出哈希均一致；三条 SH600000 事件由限定证券/日期的 parquet filters 提取；
原始全期扫描完全未运行。A 的真实数值只取 2020-08-24，意图来自 2020-08-21 的固定100股工程指令，
周边 idle rows 和 instrument master 为 synthetic。D/E 用真实事件条款及 synthetic price，不冒充真实经济路径。

| Canary | 观察与独立断言 | 接管结论 |
|---|---|---|
| A 普通股票/跨夜 | 8月21日close保存固定100股意图，8月24日open=10.57成交，commission5+transfer0.02，现金10000→8937.98，持股100，close mark10.46；settlement保持 | 与现有C1/CoreSession标量oracle一致；本次未重跑旧CoreSession |
| B T+1/lot | 请求150股由native API规整为100，当日再卖被拒（返回None），非可卖今仓100/closable0；次日卖出，最终现金9988.96 | 通用机制通过 |
| C 母单费用 | 原生LimitOrder同一订单两次各100股，commission5/0，transfer总0.04；收盘剩余100股拒绝，释放冻结后cash7994.96 | 费用/冻结释放通过；close时available cash较低是尚冻结残单，不是资金丢失 |
| C 累计及restore | 100/100/2800股、价10，同母单佣金5/0/2.5，过户费总0.60；无order_id试算不写ledger；中间保存恢复后结果一致 | 自定义费用桥通过；未自动注册到原生持久化 |
| C insufficient cash | 2500现金请求1000股，native partial模式成交200，cash494.96，残量CANCELLED | 原生部分成交通过；无本金/费用负现金 |
| C volume | 独立合成capacity100，请求1000，成交100并取消残量 | 代理容量接线通过，不证明真实开盘深度 |
| C 多卖后买 | 2500现金首日买200，次日卖100+卖100后买100，最终cash1477.90 | 不需新写通用cash release状态机 |
| D 普通真实条款 | SH600000，公告2020-07-16，登记07-22，除息/支付07-23，每股税前0.60；100股得到60现金，synthetic成本10→9.4 | 普通相邻登记/除息、同日支付子集通过 |
| D 延迟支付/卖尽 | synthetic payable改为次日：ex应收60，现金未增加；卖尽原股仍应收60；Account状态restore后支付只入账一次 | 应收持久性通过，不能把应收用于买单 |
| D 税/登记反例 | opt-in短持仓派税事件12；若登记与ex隔一交易日且中途卖尽，native漏掉60登记权益 | 税只验一条synthetic事件；record-gap必须guard |
| E split/fractional | synthetic100×1.1=110，成本15/1.1；101×1.5原生152，项目无allocation证据应拒绝 | 整数即时拆股机制可接管；fractional不可直接接受 |
| E 真实bonus | SH600000 2016-06-23 ex、06-24上市，10%红股；映成split会在23日closable110，而项目应100可卖+10pending | **直接迁移不通过**；独立guard正确拒绝。现金分红同时存在，本测试只隔离bonus语义 |
| F identity | synthetic100股、成本8、mark10，ratio2→新证券200股、成本4、mark5；原生Account SETTLEMENT现金不变 | 简单转换通过；真实R2和混合权益迁移仍pending |
| F terminal反例 | 无successor时默认退市返1000并清股；关闭返现也会清股（源码） | settlement前保留外层账户guard，不可当作无损自动退市 |
| 状态/限价 | 停牌和开盘触及涨停均无成交；adapter拒绝未知状态、NaN open/limit/capacity | guard通过；ST/special历史映射未全路径验收 |
| 费用日期 | 2022-04-28/29过户费、2023-08-25/28印花税分量正确；early2015继续拒绝 | 接口够用，原证据缺口不被掩盖 |
| 默认日频next_bar反例 | signal当日open10/close12，以next_bar配置在当日12成交 | 不接受该配置为next-open方案 |

27 项 PoC 全通过（含参数化负例），7条原生 `warn` 弃用警告不影响会计断言。
另在固定官方 checkout 中禁网运行 matcher、ETF/stock commission、price-limit 三个 synthetic test 文件，
26项通过；未运行其 bundle-backed integration tests。所有测试单进程，BLAS/OMP/MKL限制1线程。

[机器结果](CANARY_RESULTS.json)来自工作树运行
`outputs/rqalpha_poc/ed1fc4f3-d96b-4645-9e4c-e718e6b932f4/results.json`，以成功的完整测试运行导出。
开发中暴露的 harness import名、float精度断言、资金足额前置与残单现金冻结取样时点问题均已修正；
不是修改原生撮合/模型数据以消除不兼容反例。最终保留全部上述不兼容现象。

复跑只需在独立 worktree 执行：

```powershell
Set-Location -LiteralPath 'E:\qlib_prj\qlib_rqalpha_audit'
& .\experiments\rqalpha_poc\run.ps1
```

每次输出到独立 UUID 目录；不覆盖报告冻结结果。入口先验主run contract/25文件和限定原始证据，
再运行秒级 PoC；断言失败立即停止。完整生产接线、真实特殊事件路径、完整恢复和实盘资格未验收。

开盘/状态读取另以当日 close/high/low/volume/amount 均为NaN的负例验证，开盘不依赖尚未形成的日终字段。
仓库fast层46项与Ruff通过；共99项（27 PoC+26官方+46仓库）。
