# Economic Translation MVP：E1 / E2 交付

日期：2026-09-11。计划已先独立修订并提交：`6464937`。

| 阶段 | 本轮结果 |
|---|---|
| E1 implementation | **IMPLEMENTED / SYNTHETIC VERIFIED / AWAITING USER RUN**；真实九年结构扫描和独立重放脚本已交付 |
| E2 execution/data readiness | **BLOCKED BY EXECUTION / DATA GAP**；执行原语、实际 Qlib 合成验证、有限真实单位核验与缺口报告已完成 |
| E3 freeze | **NOT AUTHORIZED**；10/20、Monthly、EW、AUM、ADV、fee/slippage、benchmark 没有正式冻结 |
| E4 outcomes / 2024+ / Strategy V2 | **NOT AUTHORIZED**；没有真实策略/benchmark NAV、收益比较、调参或 recent 研究值访问 |

这份意见的核心收紧已吸收：B494 是 reference incumbent 的治理选择，D3-A 不是新 winner 的统计授权；
E1 固定四类描述与单一10/20候选；E2 必须区分代码能运行和数据真就绪，不以 synthetic pass 降低标准。
计划中更具体的未来阶段建议仍可审议，不能自动变成 E3 authority。

## E1 已实施，正式运行交用户

[研究代码](../../model_research/economic_prediction_structure.py)只读取固定九折 B score / canonical keys，
入口没有可改 p、h、lag、模型或输入路径的参数；[输入白名单](e1_inputs.json)从 sealed D3 metadata 提取 B/keys hashes 与开发日历。
不调用 D3 preflight 或 outcome reader，也不读其他四臂 prediction。

固定产出：rank lags 1/2/5/10/20；Top10 primary、Top5/20 context membership；Top10的1/5/10/20迁移（含absent）；
Top10每日重建与10/20单候选理论成员状态；age、完整spell及右删失；全期、逐年、三段描述。
包含 ties、冷启动、交集覆盖与跨年度切模；不压缩缺日、不断开年底持仓、不估alpha半衰期、不计算显著性。

独立重放不调用主计算的 rank_day/study/overlap/churn：重新算每对Spearman、成员迁移/比例、buffer状态、age与逐证券spell；
合成CLI端到端已验证封存、hash、读取报告与重放。正式全九年运行尚未执行，不能报告 E1 COMPLETE 或 buffer structurally plausible。
运行后由固定描述证据判断 pathology；没有随结果移动的自动通过阈值，也不运行另一个 buffer。

参见 [运行说明](../../docs/ECONOMIC_TRANSLATION_E1_E2_RUNBOOK.md)。长扫描由用户执行；E2 此次短 canary 已运行，不需要重复。

## E2 得出的关键证据

完整内容见 [执行合同与 Data Readiness Matrix](EXECUTION_CONTRACT.md)。

- opt-in `EconomicOpenExchange` 复用现有 PreparedQuoteExchange/Qlib账户链，严格 raw open、方向限制、T+1 raw-shares、
  母单累计费用与开盘批次现金预算；预模拟恢复全部 exchange 状态。旧 adapter/config/runner 与 frozen D1/D2/D3 均未改动。
- 在实际 Qlib 内存/临时日历测试中，missing open 无成交、修改次日 close 不改 fill、directional limits、partial fee、
  T+1、held universe exit、跨年和Topk预演都获验证。发现并隔离 Qlib 默认 benchmark 隐式查询；provider values 被调用即报错的守卫保护。
- 真实 canary 仅4只股票、6个固定窗口，共596请求证券日；523个有效量额/OHLC配对均与显式单位换算相容。
  有14个SZ300001早期缺量，不能自动填0；另59个STAR上市前窗口不可当作当时有候选。
- 既有独立 normalized 行情文件仅覆盖 recent，其数值本轮未读。它们不能证明2015–2023 raw单位与状态。
- 2015过户费依据已补强为上交所官方三方答问；上交所2023正式条款与创业板2020改革文本已获取/读核并记录原件hash。
  2022费用来源准确标为政府网站托管的新闻转载；没有冒称中国结算原件。
- 公司行为仅交付有独立手算的事件原语；没有完整事件数据、rights/conversion/terminal实现及Qlib receivable估值桥。
  因此没有 assembled executable market dataset，**E2不能宣告READY**。

主要 blocker 是完整 dated state/特殊限价、公司行为及账户桥、独立源/全池行情认证、score输入盘前可得性、
early2015面额与实际费用语义、2015 ADV warmup、开盘成交证据、真实全池benchmark纯可执行性。
缺口是当前证据不足，不能靠删年份/股票、读2024、套现行制度或试收益解决。

## 验证与后续

本轮定向 E1/E2 tests 与 fast quality 的结果、代码/来源/交付文件 hashes 见 [DELIVERY_VERIFICATION.json](DELIVERY_VERIFICATION.json)。
没有运行全仓 full/旧qlib tier：其中包含既有结果 validators，以及可选读取真实近期 provider 的历史 runtime fixture，超出当前访问边界。
替代为新建强制隔离的实际 Qlib runtime suite、封闭 reader 测试和现有 fast checks；没有降低 E2数据验收标准。

用户运行 E1 后，下一步仅核验该输出并审阅 E2 blocker；不得自动冻结策略或开始组合评价。
E3 的 AUM 暂保留1000万元唯一工程候选，但真实全池EW可实施性尚不能认证。若数据缺口不解决，E3正式freeze亦不应继续。
