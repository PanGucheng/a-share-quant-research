# E2 Data Readiness Matrix

2026-09-14 更新：[用户运行/中断复核](USER_RUN_20260914.md)。Quotes 全部完成并验 hash，States 完成118只、Dividends完成5日；使用新版[续跑命令](RUNBOOK.md)。以下为本轮原始就绪评估，E2仍BLOCKED。

2026-09-13。**E2 STILL BLOCKED；E2 READY FOR E3 FREEZE = false。**

READY 仅覆盖该行限定对象；READY WITH MVP APPROXIMATION 的候选近似须在 E3 前明确接受，未接受部分不能拿来放行。旧矩阵中的 CAN BE RELIABLY ACQUIRED 在本轮拆成“已取得样本”和“仍缺完整历史验收”，不因接口成功就升级。详见 [报告](REPORT.md)。

| Blocker | 分类 | 当前证据 / 已解决范围 | 尚缺或下一步 |
|---|---|---|---|
| Q01 文件与索引 | READY | 保留前轮 4,416 股 × 7 字段文件/索引审计 | 不代表逐值完整 |
| Q02 旧代码单位 | READY | SH601313 654 有效日及独立 20 日 warmup 修正；双源逐日核对，隔离 overlay | 仅观测日期，不涵盖身份/缺失日 |
| Q03 全期 raw OHLCV / amount / factor | BLOCKING / UNRESOLVED | 既有抽样 + 本轮双代码全期 | 用户 Quotes 全值扫描、逐段单位与异常闭环 |
| I01 alias / economic identity | BLOCKING / UNRESOLVED | 两代码候选并存 444 日；入口已拒绝同资产双代码 | 完整生效映射；未来执行层去重/分数处理另行审议，不改冻结训练 |
| S01 日终停牌/ST数据 | EXISTING DATA BUT NOT WIRED | 可获取样本，48 缺行情日均为双源停牌 | 用户 States 全期采集与日终覆盖核验 |
| S02 历史盘前状态/board/IPO/退市 | BLOCKING / UNRESOLVED | 有时间、制度及三态检查原语，unknown 不会变 ordinary | 九年 effective 状态表及可得日期、来源冲突清单 |
| L01 普通日价格上下限 | EXISTING DATA BUT NOT WIRED | 已有 dated rules 和独立普通日样本；新入口核对 prepared 一致性 | 逐日参考价、上下限与状态输入；全覆盖核验 |
| L02 特殊 regime | BLOCKING / UNRESOLVED | 明确 special 不走普通成交路径 | 禁止新开仓可作为候选规则；持仓日估值/权益与制度证据仍不能省略 |
| C01 dividend/bonus 数据 | EXISTING DATA BUT NOT WIRED | 264 条 ex-date 样本、261 正现金、29 正送转 | 用户 Dividends 全 ex-date 查询；身份、遗漏事件、时间、净额/税核验 |
| C02 Qlib 应收与红股桥 | READY | synthetic Account/Position 守恒、登记后卖出、到账/上市/T+1 已验证 | 仅最小桥；真实数据和税/复杂事件仍受其他行阻塞 |
| C03 税/rights issue | BLOCKING / UNRESOLVED | 税前不充税后；未知配股/非整数分配拒绝 | 实际事件量未知，需公告与会计，不得记零 |
| C04 conversion/代码迁移 | BLOCKING / UNRESOLVED | 同股数迁移原语与公告/操作通知样本 | 完整身份、登记结算及待结权益映射；非一般换股实现 |
| C05 delisting cash/terminal rights | BLOCKING / UNRESOLVED | 未知终止权利保留库存并停止 | 实际事件 inventory、结算与估值，不假设末价退出 |
| H01 已知 48 个缺行情日原因 | READY | 全部有两源全日停牌记录 | 不代表其盘前证据或持仓估值已就绪 |
| H02 离池后的连续账户覆盖 | BLOCKING / UNRESOLVED | 候选 ∪ 持仓入口检查；全期扫描覆盖潜在延续 | 全期行情/状态/事件、待结权利及有来源估值 |
| T01 隔夜 date-PIT 合同 | READY WITH MVP APPROXIMATION | 已实现显式接受开关及日期/批次守卫；不要求虚构 15:00 到齐 | 近似待接受；真实完整输入 receipts/vintage 说明未认证 |
| W01 ADV20 warmup 接口 | READY | 2014 明确 20 日读取、因果窗口、独立均值校验 | 仅工程接入，不代表全池覆盖 |
| W02 warmup 全池有效性 | BLOCKING / UNRESOLVED | 1,706/2,000 有完整量；294 仍未知；四股单位交叉 | 解释 2,927 缺量日、扩展单位核验，不未知填零 |
| F01 dated 法定费用 | BLOCKING / UNRESOLVED | 官方 2015 沪深旧费基/新费率补证；后续沿已有表 | 早期面值、最低费/pass-through 语义；近似候选未自动采用 |
| F02 个人佣金假设 | READY WITH MVP APPROXIMATION | 用户已明确万 2.5 双向最低 5 元，税/过户另计 | 未来真实入口替换旧万三默认并验母单分币舍入 |
| O01 竞价 open-evidence | BLOCKING / UNRESOLVED | 未取得完整可用竞价证据，前轮权限失败保留 | 可审议 O02 替代研究定义，不声称已具竞价能力 |
| O02 日线 open-reference | READY WITH MVP APPROXIMATION | 普通日首笔价格参考、滞后 ADV、批初现金规则候选 | 待明确接受；不认证排队/冲击，不豁免真实缺值和事件 |
| B01 全池 EW / 小资金组合身份 | BLOCKING / UNRESOLVED | 上轮证据保留：不要求个人账户复制数千只股票 | 收益打开前单独确认 reference 与 executable strategy 定义；本轮不再选择 K/AUM |

最有价值的下一步是执行有界的全期 quote / 日终 state / ex-date inventory 三个扫描，并对异常和事件做闭环。不能在扫描完成前以“个股少、影响小”代替证据。限制未来新开仓范围是可审议的研究定义，已有持仓及后来发生的特殊事件仍须如实结算；当前未实施事后删股。
