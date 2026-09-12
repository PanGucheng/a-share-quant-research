# Economic Translation MVP：研究与实施计划

状态：**E1 COMPLETE / PREDICTION STRUCTURE VERIFIED；E2 BLOCKED BY EXECUTION / DATA GAP**。状态更新：2026-09-12。
用户正式运行完成，见 [E1完成复核](../reports/economic_translation_mvp/e1_completion_v1/REPORT.md)；本次不修改参数或解除E3/E4边界。
实施交付与真实数据缺口见 [E1/E2报告](../reports/economic_translation_mvp/REPORT.md)；运行见 [runbook](ECONOMIC_TRANSLATION_E1_E2_RUNBOOK.md)。
初版审计基线 `main@99ff157`；本次人工意见基线 `main@bd2a060`。
本轮先独立提交计划修订，再实施 E1、E2；E3 正式冻结、E4 组合评价未授权。

### 2026-09-11 人工审核修订（优先于初版的未来阶段建议）

用户要求评估并吸收《给 Codex：修改 Economic Translation MVP 计划并实施 E1 + E2.md》，
并实施其中授权的任务。附件 SHA256：`24d5d20750456c197be7c6e13b7b1e0b05da71a89cad7127480981eb391ef0f7`。
采纳 E1/E2 的范围授权、九类执行 blocker、单候选和人工停止点；附件的结果状态是验收目标，不能在真实运行或数据未齐时预先宣告完成。

- **B494 是治理选择，不是统计 winner**：它是 reference incumbent；D3-A 没有授权新的 representation winner。
  因 R/H 点估计略高改信号将新增 post-outcome selection。R218 仅留 future engineering robustness hypothesis，本轮不读 R/S/C/H prediction。
- E1 仅四类：固定 lag **1/2/5/10/20** 的交集内 Spearman（另列全池 percentile Pearson，区分 estimand）；
  Top10% primary、Top5/20% context-only membership；Top10 向 Top10/10–20/20外/absent 的固定 **1/5/10/20** lag migration；
  daily Top10 rebuild 与唯一 **entry10/hold20** membership 状态机。含 Jaccard、age、duration、删失、年度/三段描述，不做显著性检验。
- 10/20 是 **single pre-specified structural candidate**，不自动成为 E3 authority。只评估过短、几乎全重建、过黏和异常状态；
  不存在 pathology 可建议审议，存在则最多提出一个非收益驱动修订，不运行 buffer grid。若证据不足，结论 `inconclusive`。
- E1 的 reader 只允许固定 B score、keys、开发日历；E2 不导入 B score reader。两个 access role 分离，
  不读取 label/旧策略结果，不联算价格与 B 形成 P&L，不输出真实 NAV/Sharpe/CAGR，不访问 2024+ 项目值。
- E2 是 execution/data readiness 工作，不以配置和测试通过替代真实数据覆盖。
  正式 blocker：field-level availability、严格 next-open 无 close fallback、raw sellable T+1、唯一 corporate-action 会计、
  dated directional limits、全期 dated fees/母单最低费、真实 quote units、离池持仓连续覆盖、2023 terminal boundary。
- 价格分 A（下单前已知）、B（开盘成交确认）、C（日终估值/诊断）。C 不进入开盘候选、数量或容量。
  缺 open/有效开盘成交证据直接 NO FILL；production adapter 必须在任何父类 fallback 前拦截。
- 采用 raw prices + raw shares + explicit corporate actions 作为执行会计方向；adjusted price/factor 不再同时计算收益或另加同一分红。
  股息记录日权益、ex-date receivable、pay-date cash、送转可交易日期分别处理；事件覆盖不足即 E4 blocker。
- AUM、ADV、fee/slippage、benchmark **延迟至 E3 审议**。E2 可仅以 lot/最低费/容量检验 100万/500万/1000万三个数量级，
  不生成全期 reference NAV，不按收益选择。ADV20/1% 仍是唯一待审议容量候选，不自动冻结。
- 复用 Qlib Exchange/Account/Position/SimulatorExecutor 与现有 integration；TopkDropout 仅合成序列工程核验，
  特别验证 preview 对 live ledger 的副作用，不建设新的独立 production backtester。
- 新证据仅写 `reports/economic_translation_mvp/`、`outputs/economic_translation_mvp/`；绑定 source/code hashes、
  canonical identity、B prediction hashes、精确日期/字段白名单、规则来源与证据等级。源文件 hash 不代表 PIT 或制度已验证。
- 顺序：计划独立提交 → E1 实现/验证 → E2 合同、真实有限数据核验与 synthetic oracle → 报告 → 人工审核。
  长扫描仍交用户 PowerShell 执行；如尚待用户运行，明确 `IMPLEMENTED / AWAITING USER RUN`，不冒称 E1 COMPLETE。
  E2 可诚实以 `BLOCKED BY EXECUTION / DATA GAP` 收尾；本轮不进入 E3/E4。

### 2026-09-12 E2数据闭环审计

用户授权系统核查十类E2 blocker、有限真实canary、必要适配和规则验证；不修改策略候选或冻结E3。
最新结果见 [E2 Readiness V2](../reports/economic_translation_mvp/e2_readiness_v2/REPORT.md) 与 [19项分类矩阵](../reports/economic_translation_mvp/e2_readiness_v2/MATRIX.md)。
结论仍为E2 BLOCKED：独立源采集路径和部分缺值解释得到解决，但raw单位/身份、全期PIT与事件、warmup、费用与benchmark仍不满足冻结条件。
此前E1/E2交付和source receipts保持原样；新证据另存e2_readiness_v2 / e2_closure_v1。

## 1. 建议与授权边界

建议将下一阶段收敛为：**一个 frozen B494 signal、两个 long-only portfolio protocols、一个共同执行合同、一个共同 weighting policy**。
首先用 prediction-only 研究解释信号变化，再补齐交易数据与执行语义，最后一次冻结并打开开发期组合结果。
不再以五臂 representation 竞争为主线。MVP 的问题是：在明确的成交近似与成本下，冻结排名是否仍有经济价值，而非寻找最高 Sharpe 的参数组合。

初版用户提供的《给 Codex：Economic Translation MVP 研究规划任务.md》是参考建议；当时请求为“参照文档规划，允许更正”。
本文的参数均为**待审议提案**，不是已获授权的正式回测合同。文献结论、仓库事实、研究者选择分别标记，附件中的例子不自动升级为正式参数。
本轮参考文档文件 SHA256：`34d886fdc17e0620de42e9d0c02d80d03ef0eded9082a25aec5b85a3d94b1202`；原文件保留在用户 Download 目录，不复制或修改。

既有权威保持不变：

- [D1 freeze](../reports/literature_factor_representation_d1/FORMAL_FREEZE.md)、[D2 完成](../reports/literature_factor_representation_d2/COMPLETION_REPORT.md)、[D3-A 完成审阅](../reports/literature_factor_representation_d3a/COMPLETION_REVIEW.md)。45 个年度模型、五条预测流与 replay 已完成，无需重跑。
- D3-A 六项 HAC20/Holm 检验均未拒绝零差异；不代表等价、非劣或无损压缩。B494 mean daily Rank IC 约 0.1391，不能由此推算策略收益率。
- D3-A 在 `2026-09-11T02:25:42.352763+00:00` 已揭封。本文及后续设计均属于 **post-outcome economic research**；即使 E1 不读价格，也不能恢复为整个研究的 outcome-blind 状态。
- 既有 factor pool/representation 还带有 2010–2023 回顾性设计/筛选背景；年度 past-only purged fitting 不消除这层选择偏差。九年 economic backtest 只能称 retrospective development / pseudo-OOS，不能因模型逐年训练就称完全无偏历史 OOS。
- canonical identity：`canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423`。
- B/S precompute 合同：`f45bc6e4aab96d8d5897fcf69ee59c1e62ab2b12a53c8cf911ad217bd92e2130`；D3-A 合同：`57da47d77dbd5efba627020fdc57fdfacd1173394a411d2f7f4f7ed889f94212`。
- 2024+ 项目研究值、旧策略结果、Strategy V2、模型调参与 frozen pool 修改均不在本轮范围。新文献/官方规则的出版年份不等于项目 recent 数据访问授权。

## 2. 对参考建议的评估与更正

| 建议或前提 | 评估 | 本计划的处理 |
|---|---|---|
| 20D horizon 不等于每 20 日换仓 | 接受 | 区分信息时点、signal 更新、决策、交易、最短持有与退出规则；不强制 20D 持有 |
| 月度策略与“每 20 个交易日”近似等价 | 更正 | 月末信号、下一月首个交易日执行；固定 20D 会漂移到不同日历相位，不作为同一个 baseline |
| persistence 可决定 alpha decay / 最优 buffer | 收紧 | 它能描述排名稳定性和假想成员迁移，不能测收益衰减或证明某宽度最优 |
| 全 A 扩容使本项目 fixed K 显著改变 percentile | **当前输入不支持** | sealed daily 的 canonical_count 为 1,998–2,000；2,029 日为 2,000，144 日为 1,999，16 日为 1,998。不是全 A 总股票数 |
| percentile 必然比 TopK 更合理 | 不接受必然性 | 使用 percentile 表达研究假设、动态 K 执行；当前约 2,000 池中 top decile 与 K≈200 几乎一致，不宣称创新或已证明更优 |
| Buy/Hold Spread 总能改善净收益 | 不接受 | 文献提供待检验假说；降低交易可能同时损失毛收益，见第 3 节 |
| Qlib native 等于已满足 A 股执行约束 | 不接受 | 复用框架，补齐 dated rules、lot、价格缺失、T+1 与数据可得时点；不能直接复用旧配置 |
| hold_thresh 即 T+1 | 不接受 | 它是持仓 bar count 门槛；T+1 必须独立约束真实可卖股数 |
| 主板新股前五日不限幅可用于全部历史 | **错误** | 旧规则配置存在这一历史错配，E2 新合同必须修正；不改写旧证据 |
| 论文支持月度 top-decile | 接受但注明差异 | LWZ 正文主表 value-weighted，亦有 equal-weight 检验；MVP 的 EW 月度组合叫 literature-inspired baseline，不叫论文复制 |
| 长期收益可由 20D 标签连乘 | 禁止 | 用连续现金/股数账本形成 daily NAV；重叠标签既不是每日收益，也不是可直接投资的 sleeve |
| R218 可作为本轮正式策略模型 | 暂不采用 | 唯一信号用原 incumbent B494；R 留待独立 robustness 提案，避免 outcome 后再次扩大模型选择 |
| 原生 Enhanced Indexing/MVO 推迟 | 接受、补充理由 | 不仅是 score 未校准，还缺已认证的逐日风险数据与 benchmark 权重；优化器并非一定要求精确 μ，但需明确 score 尺度/风险惩罚合同 |
| 日线回测可以证明“真实可成交” | 收紧 | 只能给出受约束的成交近似；开盘竞价容量、排队与盘中停牌不能从日 OHLCV 完整恢复 |

每日候选数量来自已有 D3-A aggregate CSV 的 `canonical_count`，本轮未重新读取个股 prediction 或 label。
历史 universe 配置采用流动性 Top 2,000（250 日 lookback、180 日有效、120 日上市龄），但新执行池必须由 sealed keys 与 dated membership 精确核对，不能直接以旧配置替代逐日权威。
股票池的市值、行业和板块组成尚未做本轮数值审计，不以“约 2,000 只”推断其等同于 CSI500 或 CSI1000。

## 3. 文献依据：可借用什么，不能推出什么

下列来源在 2026-09-11 查阅。仅把查到的原文/摘要内容作为证据，不将检索片段当成完整复现。
较新论文只作方法讨论；不能据它们重写历史 factor 的 publication availability。

| 来源与核查深度 | 已核查的相关内容 | 对本项目的影响与限制 |
|---|---|---|
| Leippold, Wang, Zhou (2022), JFE 145, 64–82，[期刊正文](https://www.sciencedirect.com/science/article/pii/S0304405X21003743)；本地 `paper/1-s2.0-S0304405X21003743-main.pdf`，重点 §4.1、4.4、4.5，印刷页 76、79–81 | 月末预测、decile sorts、月度重构；正文主组合 value-weighted，long-only 持有 top decile；脚注 14 有 EW 附录；成本表 0/20/40/60/80 bps，文字讨论 round-trip；首个交易日前 30 分钟 TWAP/VWAP 相对 open 的滑点诊断 | 支持月度 top-decile 经济解释基准及成本报告；不能把其历史成本直接移植为九年 dated 费表。§4.5 以 rebalance 日收盘涨跌停状态筛买/延卖的处理，不能直接用于本项目 next-open 因果执行。本文不复制其收益或模型选择 |
| Novy-Marx & Velikov (2016), RFS 29, 104–147，[期刊摘要](https://academic.oup.com/rfs/article-abstract/29/1/104/1844518)，DOI `10.1093/rfs/hhv063` | 比较 anomaly trading costs；买入条件严于持有条件的 spread，在其样本中有较强成本缓解效果 | 支持一条 buffer 假说；美国 anomaly 结果不证明中国 ML signal 的最优宽度或净收益改善 |
| Novy-Marx & Velikov (2019), Financial Analysts Journal 75(1), 85–102，[作者机构摘要](https://pure.psu.edu/en/publications/comparing-cost-mitigation-techniques/)，DOI `10.1080/0015198X.2018.1547057` | 比较低成本证券过滤、降低频率与 banding | 不能把过滤、频率、banding 全部交叉搜索；MVP 只保留两个规则包 |
| Gârleanu & Pedersen (2013), Journal of Finance 68(6)，[作者公开全文](https://pages.stern.nyu.edu/~lpederse/papers/DynamicTrading.pdf) | 有可预测收益和交易成本时，动态交易取决于信号变化及成本，不能只追逐即时无摩擦目标 | 支持 horizon 与交易频率解耦；其模型假设下的最优交易解不能等同于本项目未校准 rank buffer |
| Gu, Kelly, Xiu (2020), RFS，[NBER 工作论文入口](https://www.nber.org/papers/w25398)及[作者机构期刊介绍](https://www.aqr.com/insights/research/journal-article/empirical-asset-pricing-via-machine-learning) | 预测与组合经济意义是不同的检验对象 | 不以 IC 接近或预测 MSE 改善替代实施后 NAV；本轮不复制其模型竞争 |
| Azevedo, Hoegner, Velikov，*The Expected Returns on Machine-Learning Strategies*，[AEA 2025 会议工作论文全文](https://www.aeaweb.org/conference/2025/program/paper/TihddefB)，尤其引言 pp.4–5 | 文中成本缓解方法减少换手/成本，常伴随 gross return 下降；其特定样本中的某些净改善幅度有限 | 与参考建议第五节相符，但应标为工作论文与特定样本证据，不是“ML buffer 普遍无效”的定论 |
| Patton & Weller (2020), JFE，[期刊摘要](https://www.sciencedirect.com/science/article/pii/S0304405X20300453) | 区分纸面 anomaly 与实际实现成本 | 需要展示 fill、现金滞留、容量与数据缺口，而非只从毛收益减统一 bps |

本轮没有发现能为本项目直接提供“唯一正确的 p、hold band、AUM、权重”的论文。
EW 的建议来自参数少、现有代码容易审计，以及便于隔离 rank-to-holdings；不是声称文献证明 EW 优于 cap weight。
value weight 仍带显著 size 配置，EW 也不是 size-neutral。score weight 的平移、负值及年度尺度问题使其不适合作为当前 MVP；rank weight 又会新增曲线选择。

## 4. 代码审计与复用清单

实际 import 的 Qlib 是 `E:/qlib_prj/qlib_clone/qlib`，版本字符串 `0.1.dev6`，git commit `d5379c520f66a39953bad76234a7019a72796fd0`。
该 checkout 有用户修改的 example YAML；本轮未修改它。实施时绑定所用源码文件 hash 与环境，不以一个版本字符串证明所有行为。
下表是静态审计结论，不是本轮真实 market runtime 验收。

| 组件 | 已有能力/实际语义 | 下一阶段处理 |
|---|---|---|
| Qlib `BaseSignalStrategy` / `WeightStrategyBase`，`qlib/contrib/strategy/signal_strategy.py` | signal 接口、calendar 上前一 bar 取信号（`shift=1`），目标权重/订单生成 | 复用 signal/calendar；严格传入单列 B score，防止 DataFrame 只取首列掩盖 schema 错误 |
| Qlib `TopkDropoutStrategy` | top/bottom 方法；候选与老仓合并排序再选卖出，不是每天必卖 n_drop；先模拟卖出、再按现金分配新增买入；保留老仓不每日等权重置 | 仅做合成数据工程 benchmark；不是第三个正式收益臂 |
| Topk `only_tradable` / `forbid_all_trade_at_limit` | 会在策略生成中查询执行区间 tradability；默认双向限制可能阻止涨停卖/跌停买 | 不能让当日 close/change/整日量进入开盘选股；必须按方向过滤、按时点隔离 |
| Topk `hold_thresh` | 检查持仓 bar count；`n_drop/K` 仅等权且完整替换时近似单边 replacement 比率，双边 traded notional 约 `2*n_drop/K` | 真实 turnover 按成交金额统计；持有门槛不是严格 T+1 股数账本 |
| Topk 的 `deal_order(... position=current_temp)` 预模拟 | 调用的是同一个 Exchange | 现有 Exchange 有可变 T+1/audit 状态，直接组合可能产生预模拟污染或重复记录；E2 用合成 case 验证，不能直接 drop-in |
| Qlib `Exchange`，`qlib/backtest/exchange.py` | `limit_threshold` 接受 float 或 `(buy_block_expression, sell_block_expression)`；volume threshold 支持字段表达式；deal_price 可分买卖侧；默认成本是静态比率 | 用 prepared quote 的逐日 buy/sell masks；无需重写完整 engine，但不依赖 0.095 |
| Qlib `get_deal_price` | 缺失/无效指定价格时会 fallback 到 close | next-open 合同必须在调用前拒绝，并覆盖/隔离 fallback；现有子类在 `super()` 后检查不能单独保证此点 |
| Qlib `SimulatorExecutor`、`Account`、`Position` | serial execution、cash/position/NAV、订单结果；settle_type 默认 ST_NO，cash settlement 也不等于股票 T+1 | 日级 simulator 足够；复用账户和成交结果，单独保留 opening sellable ledger；NestedExecutor/分钟撮合延期 |
| [exchange_adapter.py](../qlib_integration/exchange_adapter.py) | PreparedQuoteExchange、component_costs、TPlusOneLedger、raw/adjusted 换算、动态 lot 和订单审计 | 优先复用，经新 synthetic oracle 验证；补齐面额费基、真实可得字段、corporate actions 与纯预演 |
| [market_semantics.py](../qlib_integration/market_semantics.py) | dated fee resolver、board/limit/lot resolver、timing validator、有限 stale valuation | 复用纯函数；现费表只有 2022-04-29 起，主板 IPO 历史错误、旧创业板/ST 分支缺失；新增专用原语和参考表，保留旧配置 |
| [instrument_state_evidence.py](../qlib_integration/instrument_state_evidence.py) | published_at、effective_from、来源等级与冲突检查 | 复用 event/availability 逻辑；代码有能力不代表 2015–2023 逐日官方状态已齐全 |
| [strategy_adapter.py](../qlib_integration/strategy_adapter.py) | PeriodicEqualWeightSelector 在非 rebalance 日返回 None，避免每天重置权重 | 复用这一语义，新增真正月末日历与 buffered membership；不可把固定 20D schedule 改名 monthly |
| [runner.py](../qlib_integration/runner.py) / [result_normalizer.py](../qlib_integration/result_normalizer.py) | prepared quote、executor、orders/fills/rejects/partials、cash fees、position raw shares | 复用输出与账本检查；runner 当前写死 EqualWeightTargetStrategy 和旧配置参数，不能原样跑新两臂 |
| [reference_data.py](../qlib_integration/reference_data.py) | 旧日 change 和统一 threshold 生成 masks | 不作为开盘执行权威；须重做有时间边界的输入准备 |
| [historical_portfolio_backtest.py](../qlib_integration/historical_portfolio_backtest.py) | 有 audit、报告、选策略、holdout orchestration；整块 parquet loader、stale carry fallback、gross_return_approx | 只复用可独立检查的帮助函数；禁止运行旧总入口、select_portfolio_rule、holdout；gross≈net+累计费用不是可投资无成本反事实 |
| `portfolio/execution_engine.py` / `reference_engine.py` | 另有简化账本实现 | 作为小型独立 oracle 候选，不再建设第三套生产执行框架 |
| Qlib `risk_analysis` | 默认 mode=sum，年化是均值×252，drawdown 基于累加；product 模式又使用 log-return std | NAV/CAGR/simple-return volatility/Sharpe 按第 10 节独立定义，不盲用默认报表字段 |
| EnhancedIndexingStrategy | 需 dated factor_exp、factor_cov、specific_risk、benchmark weights；缺 risk data 时可能跳过优化 | 本次定向检索未找到覆盖九年的认证 risk package；proxy exposure 不等于 Barra。MVO/校准/风险模型延期 |

已有测试覆盖 T+1、lot、fee、timing、raw unit、账本等，但本轮未运行这些历史测试套件；其中部分 fixtures/默认 provider 指向近期。
E2 必须使用独立临时 provider 和 2015–2023 范围合成交易日历，真实 recent provider 的存在不授权读取它。

## 5. 数据缺口与 E2 最小执行合同

canonical Matrix READY 是**研究特征权威**，不是九年 executable quote/state/event 数据集已认证。
现 `raw_market_data_snapshot_v1.yaml` 主要是 2021+ 历史工程配置，`historical_instrument_state_v2.yaml` 记录 scope/canary 及 readiness false。
不能将其旧近年 Market Cache V3 整块装载后再过滤成 development。

### 5.1 必需数据及准入

| 数据 | 本轮确认 | E2 输出/缺失时行动 |
|---|---|---|
| B494 frozen prediction、年度 identity、canonical keys | 已封存、replay 已验；预测约 2,000/day | 锁定每折 hash、score 时间与年度接续；不重训，不扩池 |
| 日历和 PIT membership | 有 canonical/practical PIT 合同与历史 universe 代码 | 对 sealed keys 精确映射；记录 universe 新进/退出，禁止用未来存续条件过滤 |
| 原始 OHLC、交易量股数、成交额元、复权因子 | 有 community provider/换算代码，九年成交语义未在本轮实测 | date/column predicate 在 I/O 前执行；先查 manifest/schema，再有限 2015–2023 事件样本、单位/corporate-action oracle |
| board、交易所、上市日、ST/退市状态、停复牌 | 有推断及 evidence 框架；全期 PIT 完整度未证 | 建按日有效且含 published_at 的状态；unknown 不当 false；不得按 2026 名称反推历史 ST |
| 当日 up_limit/down_limit、除权参考价、tick、特殊交易日 | 尚无本轮认证的九年执行输入 | 优先 dated 官方/可靠供应商涨跌停价及状态，规则交叉检查；否则严格 dated board/state 计算；无法辨别时保留缺口 |
| 分红、送转、拆并股、配股、终止上市现金/股份处置 | adjustment factor 不能代替完整现金事件账本 | 至少形成可核验的持仓/现金桥；未知 held terminal event 阻断完成声明，不能 0 元假卖/永久无风险 ffill |
| 市值、行业、ADV/amount | 有历史字段/辅助诊断代码；当前池画像未计算 | PIT 描述分布；不通过事后收益选择 cutoff。市值不作为 EW 核心权重依赖 |
| benchmark total-return、risk-free | 原有指数 close loader，不保证 TR 与现金率 | 核实口径；无 rf 时报告 zero-cash-return Sharpe proxy，不能暗示已含真实无风险收益 |
| auction/minute volumes、订单队列 | 本轮未发现可直接认证的数据输入 | 日线 MVP 不假装具备；opening fill/capacity 只能标明近似，真实竞价容量未证 |

数据缺口分为不可妥协的 correctness（时间、单位、现金/股数、未知终止事件）和允许显式近似的 microstructure（报价范围内的小额开盘成交）。
仅有日线不必建设订单簿平台，但不能以“先做 MVP”为由消除缺失状态、跳过损失日期或伪造成交。
若 mandatory 数据不足，交付具体缺口、可采购/补采来源与范围；本次规划不下载新市场数据，不扩大到全 A/2024+。

### 5.2 推荐执行时序：日线 open-reference proxy

当前 `label_20d_t1` 的权威代码读取 `$close`，对应 **close(t+21)/close(t+1)-1**，不是开盘到开盘收益。
建议 primary 采用 **t 收盘后固定信号，下一交易日开盘参考价**，因为它避免同收盘成交与日内未来字段；明确与训练标签的 entry price 不同。
不是因为 open 能获得更高收益而选择它。VWAP 日字段不是前 30 分钟 VWAP，日线不能重建 TWAP；本轮不添加执行价收益臂。

1. t 日收盘及相关输入发布后形成 rank、持仓目标与次日意图；monthly 只使用当月最后交易日信号，daily buffer 每日更新。
2. 次日盘前仅使用届时已知的状态、公司行为及价格上下界做安全检查；不能用次日 close/high/low/全日 change/量修改选股。
   E2 同时检查 score 所有输入的 practical information-availability；“daily bar 日期为 t”不等于该输入一定在 t 收盘瞬间发布，无法支持次日盘前可得性的输入需要列为因果证据缺口。
3. 下单数量由已知 NAV/昨收及价格界限决定，按 raw shares/board lot 取整；买单按限价和最坏显式费用预留资金，不用事后 open 反算完美等权股数。
4. MVP 的**同一开盘批次买入预算只使用批次前可用现金**，不预支同次卖单尚未确定的收入；卖出所得从下一次决策可用于买入。这是保守工程选择，不是 A 股法律禁止当日资金再投资。
5. Exchange 读取执行侧 raw open 决定 fill reference，买上限/卖下限触及时分别拒单。日线无法判断排队，触限拒单是统一保守假设，不代表现实每笔必不成交；涨停卖出/跌停买入不因另一方向限制而自动禁掉。
6. spread/slippage 作为单独 adverse execution charge 记录，避免声称以超过涨跌停界的虚构价格成交；等效成交价可作诊断但不能再重复扣费。基准价成交额、税基与 charge 的约定一并冻结。
7. 缺开盘价不 fallback 到当日 close。已知全日停牌拒单；临时停牌/首笔晚于开盘的日 bar 不足以证明 auction fill，标识无法辨识的执行近似。
8. full-day volume=0 可在执行侧作为“无成交”的否决证据，不能用于盘前选股/重新排序。full-day 正成交量也不能证明开盘竞价有足够容量。
9. 收盘后才使用当日 close 估值、记录成交额参与度；不把这些字段回传给同日已生成订单。

最简容量保护提案：初始资金 **人民币 1,000 万**、委托上限为截至信号日最近 20 个交易日平均成交量的 **1%**，均是研究者的可审计工程数值，不是已估计容量。
零量日按 0 纳入，缺数据与真实零量分开；不足 20 个有定义交易日则不允许新增仓。pretrade cap 是风险限制，不能证明 opening capacity。
这个 AUM 不是用户实盘规模承诺；E2 可在收益打开前因 lot feasibility 调整一次并记录理由，否则不做 AUM grid。

### 5.3 T+1、状态与 corporate actions

- sellable = 当日 opening 可卖股数 − 当日已卖；今日新买不增加 sellable。原有 1,000 股＋今日买 500 股，最多卖原有 1,000 股；周末/假期按交易日推进。售出资金与股数 settlement 是两回事。
- 不融资、不卖空；同股票同批次合并意图，不做买卖对敲；部分成交后的费用、lot、现金上限再校验。失败卖单的股票、价值与风险都保留。
- 主板通常 100 股整手买入；科创板最小申报/增量不同，必须由 dated lot 表生成，不能全市场统一 `lot_size=100`。公司行为后的零股退出要有明确规则。
- 提议禁止**新买**盘前已知 ST/退市整理股票；已有仓位从信息可得后的下一合法机会减持，卖不掉继续记账；这不是回溯删除股票。IPO 只沿用 canonical 的 dated eligibility，不另调上市龄。若无法确认特殊新股规则，拒绝新增并报告。
- 股票离开 prediction universe 后仍须有 quote/状态/估值：市场缓存范围应覆盖过去可能建仓的股票及其后续持有日，而非只与当日 prediction 做 inner join。
- 单票意外缺 score 与合法 universe 退出分开：前者记录数据异常、禁止新增；整日/整个年度分数缺失阻断；后者可按预定退出意图处理。不得把 future label NaN 用作今天选股过滤。
- raw price × raw shares 与 Qlib adjusted price × adjusted amount 必须逐事件对账。分红应收、到账、税、送转及配股处理需单独记录；只改变 factor 不能宣称现金分红已正确再投资。
- MVP 优先定义“个人证券账户税前投资收益、扣交易费用，股息税口径另列”；若不实施逐 lot 股息红利税，必须称为 **before dividend income tax**，不能称为个人税后净收益。历史差别税制见第 12 节。
- 停牌估值用已知 last valid close 并记录 stale age；长期未定价允许冻结估值作 provisional ledger，但触发质量停止/单列不确定性，不能输出完整通过的业绩结论。终止上市有明确事件才做现金/股份结算；未知不强制清零，也不永远当成可变现资产。

### 5.4 Dated rules 与费用

规则优先级：**可靠逐日价格上下界/交易状态 → 当时有效的正式规则 → 明确标识的待确认缺口**。
不能只用前收×10%：ST/board、IPO、退市整理、重新上市、除权参考价、分币舍入及特殊交易日均可能影响结果。
不能用 observed close change 推断当天法律限幅，更不能把它用于开盘决策。

| 区间/制度 | 推荐合同内容 | 来源/确认状态 |
|---|---|---|
| 主板普通/ST | 历史通常 10% / 5%，特殊日期和 IPO 另分支 | 按历史正式规则；现 repo 主板 IPO 前五日不限幅从 1996 起的配置不可继承 |
| 创业板 2020-08-24 前后 | 改革前普通 10%、风险警示规则按当时制度；改革后普通与风险警示 20%；新股前五日不设涨跌幅限制；旧退市整理有过渡例外 | [深交所 2020-08-21 答问](https://www.szse.cn/aboutus/trends/news/t20200821_580924.html)、[风险警示过渡通知](https://www.szse.cn/disclosure/notice/general/t20200710_579459.html) |
| 科创板 | 20% 与新股前五日安排，ST 不能简单套主板 5%；另有 lot 语义 | E2 锁正式规则条文/版本，不能只采用征求意见稿 |
| 主板注册制新股 | 2023 新制度的前五日安排不能向前套用；旧 IPO 首日有特殊价格控制 | [2023 正式规则发布通知](https://www.sse.com.cn/lawandrules/sselawsrules2025/repeal/rules/c/c_20250612_10824490.shtml)、[旧首日机制说明](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20150912_3988762.shtml)。2023 条文实际实施挂钩首只注册制主板新股上市，不机械用网页元数据的发布日期 |
| 印花税 | 卖方：2015–2023-08-27 为 0.001；2023-08-28 起 0.0005；买方 0 | [税务总局 2023 第39号](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html)；旧 10bps 亦有 LWZ §4.4 核查 |
| 过户费：2015-08-01–2022-04-28 | 双向成交金额×0.00002（0.02‰ = 0.2bps） | 2015 中国结算公告公开转载全文，原站凭据在 E2 补齐；勿误写为 2bps |
| 过户费：2022-04-29–2023 末 | 双向成交金额×0.00001（0.01‰ = 0.1bps） | [中国结算通知的政府转载](https://jrj.sh.gov.cn/SCDT197/20220429/f715759a877b4158812eb6df70ccb49e.html)；E2 留存原通知或可靠档案 |
| 2015-08-01 前过户费 | 公告列沪市成交面值×0.0003，深市成交金额×0.0000255，双向；**面值不等于市价** | [中国结算 2015-07-09 公告全文转载](https://finance.sina.com.cn/stock/y/20150709/222322641178.shtml?from=wap)。面值、最低收费/舍入及券商计收方式待 E2 原始资料确认，不能以今天费率回填 |
| 佣金 | 建议双向 `max(5元, 成交额×0.0003)`，按每股票/方向/交易日合并母单口径 | 研究者假设，非“法律统一佣金”。约定其已含经手/监管费用、未含印花税与过户费；避免规费重复计收。实际 broker 合同可在 E2 冻结前替换 |
| 隐含摩擦 | base 10bps/side；stress 20、40bps/side，显式 dated 费表不变 | 研究者压力假设，未通过个股真实报价校准。spread、slippage、impact 合并为一个费用桶，MVP 不再叠加另外三项同义成本 |

base/stress 与论文 round-trip 口径不相同，报告必须写每边还是双边。例如 10bps/side 的买卖隐含摩擦合计 20bps，再另加显式费用。
费用 resolver 必须对每个交易日期、交易所、security type 恰好命中一个规则，新增 `fee_base` 支持成交额/成交面额；费用表有断档即不通过 E2。
stress 只用于已定规则的描述性稳健性，不能因某个成本下赚钱而更换 base。

## 6. E1：prediction-only persistence 设计

### 6.1 输入与读取白名单

只读取 B494 年度封存 prediction 的 `datetime, instrument, score` 和必要 provenance/日期元数据，以及不含收益的 canonical keys/membership。
范围 2015–2023。**不读取 labels、price、future returns、IC 明细、portfolio NAV、成交后成本或旧组合结果**；不构建 cash/真实股数账户。
可以复核已有 D3-A aggregate 的日期/数量，不把其 finite-label common sample 当 persistence universe。
不读其他四臂数值来选择“更稳定模型”。先冻结诊断代码、lag/percentile 列表、输出列，合成测试通过后才运行真实 E1。

### 6.2 统计定义与固定输出

| 指标 | 固定定义 | 容易误解处 |
|---|---|---|
| Rank persistence | 交易日 lag 1/2/5/10/20，先各日在完整有限 score universe 排名，再在两日 ID 交集上做 Pearson correlation of percentile ranks；另列该交集内重新排序的 Spearman | 两种 estimand 不混名；不先保留整个九年都存在的股票 |
| 单日排名 | 有限 score 降序；统计使用平均并列名次，选择使用固定 instrument ID tie-break；输出 tie rate | 不使用 score 水平跨年度拼接；年度模型切换另列标记 |
| Membership persistence | descriptive p∈{5%,10%,20%}，`K=ceil(p*N)`；retention=`|S_t∩S_t-l|/|S_t-l|`，entry=`|S_t\S_t-l|/|S_t|`，exit=`|S_t-l\S_t|/|S_t-l|` | universe 进入/退出、NaN、排名迁移分开，分母写明；非空全覆盖规则不意味着未来有 label |
| Rank migration | 前期Top10向Top10/10–20/20外/absent的固定迁移表，lag=1/5/10/20 | 相邻日 pairwise complete 与连续生存 cohort 都报告覆盖；不隐去 disappeared stocks |
| Natural membership churn | 对每日 Top10 的等权**抽象成员权重**，`0.5*sum|w_t-w_t-1|`；成员进入/退出数量另报 | 未含价格漂移、lot、cash、fill，命名 membership churn proxy，不能称真实 turnover |
| Buffer structural proxy | 只演示一组待审议关系 `p=0.10, h=2p`，与同 p 无 buffer 对照；入池严格、老仓可留宽带，最多 K 名 | 数值只用于有文献形状依据的结构演示，不是已批准策略；禁止添加 10/15、10/30 等网格 |
| 持有时长 | membership spell 的中位数、分位数、已退出 duration、右删失数；年界不断仓，切模单列 | 不能丢掉未结束长持仓只平均 closed spells；不是最优持仓期 |

结果按全期、逐年及既定 2015–17/2018–20/2021–23 三段描述；不逐年挑选规则、不做显著性排名。
首日冷启动另列，不从 churn 平均中悄悄消失；缺日不压缩时间轴，lag 必须按 canonical trading calendar。
年底换模型包含在真实结构中，并单独报告跨 fold 与同 fold pair；保留持仓 proxy 连续性。

### 6.3 如何不变成新的搜索

E1 输出是 feasibility/解释报告，**不输出 best frequency、best percentile、best buffer、estimated alpha half-life**。
计划倾向 monthly 与 daily-buffer 两条规则；5/10/20% 是描述尺度，不是候选菜单。
E3 默认继续审议 top-decile、hold-band=2×entry 这一组文献形状示例，不能按 E1 turnover 最低点另挑阈值。
若结构完全不符（例如大量 ties、同日 universe 不完整、年度拼接失效），先停下修复输入/明确 estimand。
若仅发现 buffer 的 churn 与 baseline 类似，应保留“不支持降低成员迁移”的结论，不为了制造改善而增加参数。
任何修改必须在 portfolio outcome 前写入 design amendment、陈述非收益理由，仍标 post-outcome research；没有自动“看到结构→通过”的隐藏规则。

## 7. E3：最多两个正式组合规则包

这里只定义可审议状态机；E2 数据/执行合同完成后再生成唯一可执行 YAML 与 hash。
**B494 唯一信号**因其是事前 broad incumbent，而非 IC 点估计获胜者。选择它减少新的 selection freedom，却不能消除已发生的历史选择偏差。

### 7.1 共同规则

- long-only、无杠杆、同 AUM/费用/执行/eligibility，建议 capital fraction 0.95，5% cash buffer 是研究者工程假设，不优化。
- p 暂拟 10%，选择分母为**信号时点可知 eligible 且有 B score 的候选**；与原 canonical N 同时报告。ST 等前置限制先于排序，但不能先知道次日是否涨停再扩大选股范围。
- `K=ceil(p*N)`，先前持有且不可卖的证券计入槽位，不能“删掉老仓、额外买 K 只”。若 N 变小导致超 K，按预定最差排名先减仓；冻结这一容量例外并单列其 turnover。
- 确定性 tie-break、订单合并、lot、资金预留规则统一；缺乏可买候选可不足 K，现金不强行再投资。
- EW 是**目标/入仓资金权重**，不是每天成交后保证完全等权；真实权重受漂移、lot、现金、失败卖单影响，全部记录。
- 禁止凭行情异常前瞻地剔除最终亏损股票；数据品质评审能看到价格的阶段也不能自行查看策略 NAV 来决定删样本。

### 7.2 A：Literature-inspired Monthly Baseline（次要对照）

以每月最后交易日的 B score 选 top-decile，下一交易日形成 EW 目标；在随后一个月内目标成员不因 daily score 更新而变化。
只交易新旧目标的净差额，**不是每月先全部清仓再买回来**。
未完成的减仓/初始建仓意图按合法交易日重试、在下一月目标更新时替换；普通已完成持仓不因价格漂移每天再平衡。
ST/终止等安全退出仍可打破月度等待，明确属于共同 execution policy。
没有 2014 sealed score，因此 2015 第一条可用 B signal 作为统一冷启动信号；此后进入真正月末计划，首个 stub month 标识。
不为月度 baseline 另跑 cap-weight arm；报告“借用 decile/monthly 结构、采用 EW”，不称为 LWZ 精确复现。

### 7.3 B：Buffered Daily-Rank（主要待检验假说）

每日收盘更新 rank；新仓只来自 entry 区间；现有仓位只要仍在较宽 hold 区间就可保留。
暂拟 `entry p=10%, hold h=20%`，作为一组待审议提案，非本轮正式冻结参数。只放宽持有要求，不自动给所有 top20% 建仓。

状态顺序：

1. 应用已知 corporate action 与合法状态变化，读取实际持仓和未完成意图。
2. 标记跌出 hold band / 合法 universe 退出 / 安全退出的仓位；根据实际 sellable 发卖出意图。
3. 计算最多 K 个槽位；pending sale 未成交仍占槽位，禁止以预计卖出作为已腾空。已保留老仓不因排名小变动卖出，也不每天按新 NAV 重置份额。
4. 只在 entry 区内按固定 rank 顺序选未持有股票补空槽。新增资金单票不超过 `0.95*NAV/K`，并受盘前可用现金、lot、ADV cap 限制；欠配不提高其他股票到超预算。
5. 未成交买单当天失效；下次按最新 signal 重算资格，**当天不因事后成交失败替补下一个候选**。部分成交形成真实持仓，剩余买量不自动每日 top-up。
6. 下一个交易日再依据真实 position/cash 重做状态机；只有合法成交改变股数。

这是一条 practical rank-hysteresis 假说，不是论文最优 no-trade region 的估计。
monthly 的月度权重重置与 buffer 的老仓自然漂移不同，因此 B−A 比较的是**两个完整 implementation packages**，不能因差异显著就声称单独识别了 buffer 的因果作用。
若要隔离 buffer 机制，需要另行注册同频率同权重对照，不能临时加第三臂。

### 7.4 TopkDropout 的位置

用原生策略在 synthetic quote 上固定一组方便手算的小 K/n_drop，与手工轨迹核对 rank、卖买顺序、held count、方向限制、partial fill、预演副作用。
不以 official demo `50/5` 作为投资参数，不为其生成真实 NAV，不参与 economic winner selection。
MVP 优先复用 Exchange/Executor/Position，而不是为了“全原生”保留第三个高度重叠的策略臂。

## 8. Benchmark、容量与资金口径

primary benchmark 建议为 **eligible strategy-universe 月度 EW reference account**：使用与月度基准相同的时点、资金、费用、成交规则，持有全部 eligible universe，无 score 排序。
它是一个固定参考账户，**不计入两个 signal-strategy arms，但确实增加一条需运行和审核的现金/股数账本**；禁止通过更换其 universe/权重让策略超额变大。
每月再平衡而非每日全池重置，缺状态/退出持仓同样真实记账。若 AUM/lot 使全池 EW 严重不可实现，在 E2 先提出更换 benchmark 的书面修订，不在收益后更换。

另列全池理论 EW total-return index 可用于区分基准实施成本，但只能作为不可交易描述参考。
官方指数不默认用 CSI300。E2 若完成 PIT size/board/liquidity 画像，可在收益前指定**一个**官方 total-return index 作为背景；没有合适数据则不加，不能扫描指数择优。
CSI300/500/1000 的 price index 与 total-return index 不得混用；与 index 的差值不自动叫 alpha，更不等于已剔除 size/sector risk。

容量输出：pretrade ADV20（量、额）、请求/成交金额除以 ADV、当日实际 amount participation（仅事后）、position/ADV、隐含清仓交易日、持仓数/最大权重/HHI、现金占比、板块/size 分布、reject/partial 比率、冻结卖不出市值、lot 未能建仓比例。
不在 E4 看过收益后重新定义 liquidity filter。ADV cap 触发次数和被裁剪金额必报；不同 AUM 的简单线性容量外推只能叫 diagnostic approximation，不能称实盘容量。

## 9. 时间边界、年度拼接与终点

E4 建议连续运行 2015 首个可执行 signal 之后至 **2023-12-29**，只用 2015–2023 已有 frozen score。
同一账户跨年延续，年度模型按原 folds 切换，不逐年清仓、不把九次独立冷启动的收益平均成组合表现。
2023 年 12 月 predictions 虽无截至年末成熟的 20D label，仍可在边界内执行/估值；经济评价不要求未来 label 成熟。
最后一个信号若只能在 2024 执行则丢弃并登记 `out_of_execution_boundary`；不读取 2024 来结算。
最后日正常 mark-to-market，保留未平仓库存、现金、应收和不可卖余额；不假装末日全部能平仓。可报告预定税费下的 liquidation reserve 近似，不能称真实清算净值。

E2 允许为 ADV 最多 20 个交易日、状态/事件追溯所需的 2014 尾部历史输入（只在另行授权 E2 后，列出精确日期）；不读取 2014 新模型 score、不生成新预测。
价格/状态需要覆盖当期及过往持仓股票。严禁使用 D3-A future finite-label mask 挑选可投资股票，这会排除未来缺价/停牌风险。
数据上界检查在打开文件前；混有 2024+ 的 parent parquet 不整表读取、不整份 numerical checksum，绑定 metadata 与批准 slice hash。

## 10. 经济评价与统计合同提案

### 10.1 真实每日账本

没有外部出入金时，`NAV_t = cash_t + Σ raw_shares_i,t * raw_close_i,t + receivables_t`。
`r_t = NAV_t/NAV_t-1 - 1`，初始资金作为首个分母；现金、股数、应收逐日对账，分红/配股事件不可重复进入调整价和现金。
日 P&L 必须覆盖 overnight 老仓价格变化、当天 fill 后持仓变化、公司行为、显式费用及隐含摩擦扣款；不能只算成交股票。
无交易日也计 NAV/return；未知估值不置零，不压缩为相邻可用日。

当前 20D label **不需要 sleeve**。一条共享现金的组合可持有来自不同日期的股票；只有另行设计固定 20 日 cohort 策略才需要 sleeve 资金分配与聚合，本 MVP 不新增这一维度。
严禁重叠 20D forward return 连乘、把每个 cohort 当满额资金、或对各年度 Sharpe 简单平均。

### 10.2 指标定义

| 指标 | 固定公式/解释 |
|---|---|
| Primary economic metric | 主要 Buffered account 相对固定 universe benchmark 的 **net CAGR 差**，单位百分点/年；同时展示两个账户的 absolute net CAGR，防止把熊市“少亏”写成正盈利 |
| CAGR | `(NAV_T/NAV_0)^(252/n)-1`，n 为完整日收益数量；按共同日历。额外可列实际年数 CAGR，但不换 primary 年化 convention |
| Volatility | `std(simple daily r, ddof=1)*sqrt(252)` |
| Sharpe | `mean(r-rf_daily)/std(r-rf_daily, ddof=1)*sqrt(252)`；rf 来源/单位/date alignment 冻结；没有可靠 rf 只报明确命名的 rf=0 proxy，不把 CAGR/std 当 Sharpe |
| Active return / IR | `d_t=r_strategy,t-r_benchmark,t`；IR=`mean(d)/std(d,ddof=1)*sqrt(252)`；不是 beta-adjusted alpha |
| Relative wealth | `NAV_strategy_normalized/NAV_benchmark_normalized`；与 CAGR 差、逐日 active return 均分开，不互相连乘代替 |
| Drawdown | `NAV_t/running_max(NAV_0..t)-1`，MDD 报负最小值或正幅度并统一符号；包括初始 NAV，另列峰值/谷值/恢复日 |
| 真实 turnover | 买入 notional/NAV_t-1、卖出 notional/NAV_t-1 分列；双边=`(buy+sell)/NAV_t-1`；half-turnover=`(buy+sell)/(2*NAV_t-1)`；不把两者混称“单边” |
| 成员替换比例 | 成交新/退出股票数与持仓数的比率，单列；与 dollar turnover、E1 proxy 不同 |
| 费用 | commission、stamp、transfer、implicit charge 分桶；元、占 NAV、每成交金额 bps 并列；没有 fill 不收成交费，minimum commission 按合同聚合 |
| Gross / cost drag | 同一真实交易路径的 pre-cost P&L bridge 用于归因；如另跑零成本可投资 shadow account，会改变现金/股数，只能作预注册描述性反事实，不能用 net NAV+累计费用伪造它 |

secondary：monthly account 的净收益、paired B−A 差、vol/Sharpe/IR、MDD、逐年/era 收益、负收益年份、费用、turnover、持有期、cash drag、容量与失败成交率。
不排序选择年度赢家，不以持有期最长或换手最低当目标。

### 10.3 检验与多重性

primary metric 是经济量级；建议以以下**两项** paired daily net-return mean contrasts 作唯一推断 family：

1. Buffered − 固定 universe reference（主要经济意义）。
2. Buffered − Monthly（buffer implementation package 相对月度对照）。

两侧 HAC Bartlett lag20，Holm family=2、α=0.05；lag40 仅 sensitivity。HAC 针对 daily mean difference，**其 p-value 不能标在 CAGR 差上声称检验了 CAGR**。
此处重新注册 family=2，不能复用 D3-A 的 `holm_six` 或假装继承六项 pool contrasts。
MBB 20/40、固定 1,000 次与一个事前 seed，三账户共享 block indices；对缺日不跨段、对无可用 support 的 CI 标 unavailable。
这是从已生成 daily return 上做条件不确定性分析，不是把价格路径重抽样后宣称生成了可交易账户。
Sharpe/CAGR/MDD 可以给描述性区间，均不能事后升级 primary；有限样本、regime dependence 与 post-selection 偏差不由 HAC/Holm 自动消除。

cost stress 只有相同两个策略＋固定 benchmark 的 20/40bps 费用情景，完整保留费用对资金/成交的影响；最多 **3 个摩擦水平×3 条账户=9 条账本路径**，不是 9 个可选择策略。
若仅静态从 base fills 加扣费用，标明 fixed-trade-path stress，不称为可投资 stress backtest；正式实施前二者选定其一，建议采用各自完整账本。
stress 不新增显著性结论、不改变 primary，不与 weighting/execution/model 交叉。
“值得 Forward 验证”的正面判断至少需要净经济差为正、统计与执行限制同时披露；显著性不足不是等价，也不自动从两臂挑一点估计赢家。

## 11. 分阶段交付与停止点

| 阶段 | 输入与允许读取 | 禁止内容 | 输出/冻结点 | 人工审核与停止条件 |
|---|---|---|---|---|
| **E0 已完成** | 附件、仓库源码/config、已有 authority 与 D3 aggregate、论文及官方制度 | 新 prediction scans、price values、真实 portfolio/persistence、2024+ 项目值 | 本文、代码缺口与来源；git commit 固定本轮方案 | 初版停止点已被本次 E1/E2 授权取代；E3/E4 仍关闭 |
| **E1 结构诊断** | B sealed scores/keys/calendar/membership，2015–2023；合成 fixture | labels、prices、其他四臂排名择优、真实收益/费用 | 固定诊断列表、访问日志、rank/membership 报告、可复现 hash；不产生账户 NAV | 用户审核结构解释；缺日/identity 不符/不明 universe 转换则停止；完成不自动授权经济评价 |
| **E2 执行合同** | 经批准日期/字段的 OHLCV、量额、PIT state、corporate actions、fees、本轮不读 2014，warmup 缺口另记；**可看价格做质量审计但不与策略收益联算** | 策略 NAV、参数 performance search、旧holdout、2024+ | dated rule/fee table、field timing、单位/事件证据、最小 prepared quote、synthetic execution oracle、data readiness；recommend execution assumptions，E3 才冻结 | 审核数据缺口和近似；mandatory gap/终止事件无解/时间错配不得通过。不得靠削掉表现差的年份完成 |
| **E3 策略冻结** | E1、E2 报告与批准数值、合成数据；可读 sealed metadata | 开发期 portfolio return、参数收益试跑 | 2 strategies＋固定 benchmark、假说/参数来源表、账户/推断合同、code/runtime/input hashes、runbook；全部决定具体化 | 审核唯一 execution packet；所有 p/h/AUM/rf/fee/权重/重试/终点/缺失规则必须 resolved，才可申请下一阶段 |
| **E4 开发期经济评价** | 冻结 B、执行数据与 benchmark，2015–2023 | 调参、增臂、改 base cost、recent、V2 | 用户运行正式长任务；append-only outcome marker、3/9账户输出、独立 replay/账本与统计重算、单一报告 | 完成或失败均保留证据并停止；不能因亏损/不显著反复试参数，bug fix 新版本保留旧结果 |
| **E5 Held recent diagnostic（可选）** | 仅单独授权的精确 recent 日期/字段与事前冻结的新预测生成方案 | 据近期结果改模型/策略再称 holdout；自动追加2024+ | 若需要，先独立规划缺失模型/预测再一次性执行；报告 historical exposure inventory | D3 只覆盖至2023，不能假定已有等价2024+ predictions；未获新授权一直关闭，且不叫 untouched final OOS |
| **E6 新 prospective track** | 新 freeze timestamp 之后才可得的信息/执行状态；成熟后才能评价 | 回写 V1、追溯优化、用未来标签生成信号 | 独立候选身份、前瞻决策/订单/账户与成熟标签证据；新的运行与评价时点协议 | 可在 E4 审阅后直接启动，不必先打开 E5；须单独授权模型续接/冻结，不能自动建 Strategy V2 |

分阶段不是七套新框架。E0/E1 轻量；E2 是主要风险工作量，先做 data gap inventory 和最小事件样本，不先承诺“全九年保证真实可成交”。
E1 与 E2 已于本次明确授权下顺序实施；E3 仍需人工审议，E4 必须有具体 frozen packet 与单独运行许可。
维持此前习惯：长任务由用户运行 PowerShell；实现阶段先交付通过有意义测试的命令，本轮不提供会打开经济结果的命令。

### 11.1 最小实施清单（本轮仅第 1–3 项及第 5 项合成执行验证；其余延期）

1. 新建独立 `economic_translation_mvp` 研究输出目录；简单 YAML/JSON/Markdown 即可。不要重命名全仓，也不要构造机构级 manager/registry 服务。
2. 一个 bounded B prediction reader＋E1 CLI，复用已有 hash/日期守卫；它无法访问 label/price 路径。
3. 在既有 Qlib integration 边界增加经济研究专用 prepared quote/dated fee/state 配置；冻结老配置，补足第 4–5 节缺口。
4. 一个 monthly selector、一个 buffer selector；共用订单、cash、lot、T+1 和审计输出。保留真实 membership 与 actual holdings 区别。
5. 一个独立 cash/raw-shares oracle，在短合成路径上逐笔比较；真实运行后的 replay 读取冻结订单/quote 重建 ledger，不能只比较同一函数输出两次。
6. 一份经济结果汇总脚本，从 ledger 计算指标；另一个最小独立公式 oracle 检查 daily NAV、费用、turnover、HAC/Holm。
7. 单入口 PowerShell：preflight → 先写 outcome access marker → 用户正式运行 → 封存 → verify。失败不擦 marker，不自动新 run-id 规避停止点。

### 11.2 必须覆盖的高风险测试

- t close signal 不能 t close fill；次日 close/high/volume 改变不能改变盘前 rank/订单量；open 缺失必须无成交，不能 close fallback。
- 2015 过户费制度边界、2022 费率边界、2023 印花税边界；佣金最低额、部分成交母单聚合、无 fill 无费、面额/金额及 bps 单位。
- 创业板改革前后/ST、主板新股历史分支、科创板 lot、除权后限价分币舍入、未知状态 fail-closed。
- T+1 老仓与新仓混合、多次 partial sale、跨周末；模拟预演不改变 live ledger/audit。
- 拒卖保留仓位、拒买保留现金、pending sale 占槽、无 intraday rerank 补位；buffer 不每天重置老仓权重；monthly 非月末无 score 换仓。
- 年度换模型不断仓；prediction universe 退出不丢 held quotes；缺 label 不影响订单；终点不读2024。
- 分红/送转/配股的 NAV 桥、quantity/factor/amount 单位；无交易日估值、停牌及 terminal unresolved 的停止行为。
- 独立 cash conservation、NAV、CAGR、turnover 两种口径、固定 family=2；不能把20D标签复利或报告 default Qlib sum-drawdown。

## 12. 官方制度来源、证据缺口与参数权限

| 编号 | 官方/原始来源 | 本轮使用与下一步 |
|---|---|---|
| O1 | [财政部/税务总局 2023 第39号](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html) | 已核查 2023-08-28 减半；写入 dated 卖出税率 |
| O2 | [中国结算 2022 通知的上海金融部门转载](https://jrj.sh.gov.cn/SCDT197/20220429/f715759a877b4158812eb6df70ccb49e.html) | 已核查0.02‰→0.01‰双向；不是佣金 |
| O3 | [中国结算2015公告全文转载](https://finance.sina.com.cn/stock/y/20150709/222322641178.shtml?from=wap) | 初版只有转载；E2已取得上交所官方三方答问补强费率/面值，早期最低收费与券商语义仍不齐 |
| O4 | [深交所2020-08-21正式答问](https://www.szse.cn/aboutus/trends/news/t20200821_580924.html) | 创业板改革与过渡例外；发布日期不替代实际生效日 |
| O5 | [深交所风险警示/退市整理过渡通知](https://www.szse.cn/disclosure/notice/general/t20200710_579459.html) | 风险警示20%与旧制度例外；ST不是全市场恒定5% |
| O6 | [上交所2023规则历史归档](https://www.sse.com.cn/lawandrules/sselawsrules2025/repeal/rules/c/c_20250612_10824490.shtml) | 原规则现被标为失效，但历史回测需其当时有效版本；E2 锁定附件条文及实际实施日，不用2026新规则回填 |
| O7 | [深交所交易规则2023正式PDF](https://docs.static.szse.cn/www/lawrules/index/rule/W020230217564423808793.pdf) | 检索定位到正式文件，直接抓取本轮超时；T+1/条文号的逐条验收列入 E2，不把征求意见稿当正式法规 |
| O8 | [上交所旧新股首日机制说明](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20150912_3988762.shtml) | 证明旧制度有首日价格控制，不是永久套用前5日无限幅；网页迁移日期不是原制度实施日 |
| O9 | [财政/税务/证监会2015股息红利政策答问](https://shanghai.chinatax.gov.cn/zcfw/zcjd/201509/t419000.html) | 个人持股期限影响股息税；MVP 若暂不实现，明确结果在股息所得税前 |

冻结前维护一张简单 parameter authority 表，分三类：

- **外部约束**：交易制度、税费日期、tick/lot、数据发布时点，不由 performance 决定。
- **工程假设**：AUM、5%现金、20D ADV/1% cap、佣金/滑点、开盘成交近似、重试/结算、估值与终点；须明确批准，不伪装成经验定律。
- **研究选择**：B唯一信号、monthly/buffer两臂、EW、p/h、benchmark、primary metric/2 contrasts、HAC/MBB；在 E4 前一次明确冻结。

禁止搜索维度：representation、LightGBM参数、label horizon、top5/10/20策略菜单、weekly/5D/10D/20D/40D、多个 buffer、cap/score/rank/softmax weights、执行价择优、按年 liquidity cutoff、benchmark择优。
E1 的结构描述与 E4 的 fee stress 必须与正式 strategy arms 分离；任何超过本文上限的比较都先修订计划，不能事后称为 sensitivity 逃避多重性。

## 13. 最终交付与本轮完成界限

后续 MVP 应交付：能逐笔复核的 orders/fills/rejects/partials、cash/positions/receivables、daily NAV、费用分桶、turnover、容量限制、两个固定 contrasts 与完整失败证据。
可信的负面结果或数据不可实施结论也算研究完成，不以“必须赚钱”驱动迭代。

初版完成静态代码审计、sealed aggregate 数量核查、论文段落与制度来源检索；本次另获 **E1 prediction-only＋E2 execution/data readiness** 授权。
实施结果以本阶段报告为准，不能用本计划宣告九年市场数据可成交性。结束点为结构证据与执行合同/缺口，不是正式回测。
E3/E4、E5、E6 分别保持待授权；2024+ 项目研究数据与现有 Forward/Strategy V1 不随本文改变。
