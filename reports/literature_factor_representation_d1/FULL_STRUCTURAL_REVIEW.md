# D1 全量结构核验与审阅

状态：**FULL STRUCTURAL SCAN VERIFIED / HUMAN REVIEW REQUIRED / D2 NOT AUTHORIZED**。
用户完成 `d1_structure_20260910_v2/full` 后，本轮只重读diagnostics、access logs、receipts和允许的metadata。
没有重跑长任务，没有读取canonical研究值、封存outcome或2024+研究值。

## 核验范围与结果

| 项目 | 核验结果 |
|---|---|
| 日期 | 2010-01-29至2023-12-29，3382日 |
| 完整月度chunk | 168 |
| canonical key行数 | 6,640,610 |
| 原始读取列 / unique parents | 494 / 489 |
| R/C/H列数 | 218 / 201 / 358，未改动 |
| 用户运行中的独立naive oracle | 全日期通过，mask一致，最大绝对差3.885780586188048e-16 |
| 数值容差 | rtol=0，atol=1e-12 |
| exact aliases | 5组×168月均检查通过 |
| access记录 | 5376个request/complete匹配，日期/列均在允许范围 |
| 用户运行累计chunk耗时 | 6471.62秒，约107.86分钟 |
| 最大月度输入frame | 176.57MiB，**不是process峰值RSS** |

已重算/核对source、code、packet、月度文件、receipt及六个year/fold汇总的哈希；
另逐月核对日期轴、叶/输出identity数量、family/node histogram与有效行分母。
本轮不是又一次canonical数值重放：真正独立的生产实现/naive计算在用户full运行时完成，
本轮核验其绑定证据和结构计数。没有将receipt通过说成新的模型或经济效果验证。

[核验记录](full_review_v2/verification.json)、[原始run summary副本](full_review_v2/run_summary.json)、
[交付文件哈希](full_review_v2/file_hashes_lf.json)。候选recipe仍为
`8b688bd098ebafd1c1da2bab32d029624f6da65f7166c59f702fbc18499cf51f`，没有重写原packet或运行回执。

## Rank minimum 100

428个G叶×3382日期，没有all-missing/constant/below-rank-min导致的rank抑制；
140个rank输出×3382日期也没有有效样本数低于100的情况。
原始和生成infinity、constant rank outputs均为0。

建议保留100作为唯一待人工冻结值：在本开发范围没有产生额外可用性损失。
这不是100具有普适理论最优性的证据，也不能据此推断其他时期。
[逐年叶诊断](full_review_v2/year_leaves.csv)、[九折叶诊断](full_review_v2/fold_leaves.csv)。

## 跨family完整性与覆盖代价

两个multi-family输出均保持全部family可用才生成值，single-family有效次数和跨family有效权重漂移均为0。
30-session up-day balance各年覆盖率为100%。range intensity的覆盖率及代价如下：

| 年份 | range输出有限率 | 相对于任一parent可用的额外缺失率 |
|---|---:|---:|
| 2010 | 72.72% | 26.03% |
| 2011 | 72.91% | 25.51% |
| 2012 | 80.53% | 18.06% |
| 2015 | 77.50% | 13.24% |
| 2020 | 96.03% | 2.58% |
| 2023 | 98.09% | 1.88% |

全量range有效5,881,956行；任一parent可用6,423,165行，完整family规则额外屏蔽541,209行。
建议保持这条完整性要求，而不是为提高coverage恢复单family替代。
原因仍是两个不同估计量组成的经济测量含义。不存在结果驱动的threshold sweep。
[逐年输出](full_review_v2/year_outputs.csv)、[九折输出](full_review_v2/fold_outputs.csv)。

## Family内50%：不是“组成已稳定”

同family的price/volume partition和ret/rev聚合，有效输出未观察到只使用部分成员的情况。
dense桶存在部分lag可用：6–21桶全期有效输出约5.32%使用部分节点，22–63桶约12.25%；
22–63桶在2010年该比例达到44.52%，五个field一致。

它们满足当前至少一半节点的工程定义，且没有把不同family混合进来；但不能因此声称固定完整lag路径。
当前确切含义是“同field、同分母、预定义时间桶内可用lag节点的平均rank”。
已有histogram证明参与数量，不证明每次参与lag的位置分布或固定时间跨度。
人工冻结时必须明确接受这种可变节点定义；如要求完整固定lag路径，应先修订研究定义并单独验证，
不能把本次pass直接当成对50%经济充分性的证明。
本轮保留唯一候选和原阈值，不根据coverage挑另一套规则。
[逐年family组成](full_review_v2/year_family_composition.csv)。

## U与其他稀疏输入

总共2893个leaf-date的有限样本数小于100，全部属于raw U，未参与rank：
ADX正/负及ATR在2010–2013每个日期都低于100，合计2844个单元；PSAR down另有49个state单元。
三个递归因子各有414个整日全缺失；其2010–2013年有限cell率约0.012%、0.043%、0.018%、0.331%。
这些限制不能被“全量代码通过”掩盖，也不应通过填充、重启递归或偷偷删U来修复。
[全缺失日期计数](full_review_v2/all_missing_leaf_dates.csv)。

32个Alpha101经济语义仍未解决；23个price-scale主限制、3个recursive质量主限制、3个state主限制保持披露。
本次没有新增canonical correctness判断或重新给予数据资格。保留它们的理由是保持原raw输入信息与共同U定义，
并非证明其质量或经济含义已经合格。所有U保留仍需人工认可；如识别correctness blocker，必须停止而非收入U。

非U也不是每个stock-date都有值：2010年的KST及KST difference rank输出有限率约48.36%，
dividend-yield约53.60%。这些截面仍全部满足n≥100，说明rank样本数合格不等于接近完整覆盖。

## 九折与停止点

九个predict日轴分别为244、244、244、243、244、243、243、242、242日；
对应train日轴1172、1416、1660、1904、2147、2391、2634、2877、3119日。
汇总使用P0的train/predict membership，重叠train日分别计入各折；没有执行evaluate角色。
[逐年arm结构](full_review_v2/year_arms.csv)、[九折arm结构](full_review_v2/fold_arms.csv)。
各臂的finite-cell分母不同，只用于结构说明，不作pool performance comparison。

结论：工程执行和全量结构核验已完成；保留R218/C201/H358以及当前唯一V2规则供人工审核。
需人工接受的重点是U原样保留、range覆盖代价、dense桶可变节点含义。
不修改已绑定正式计划/候选packet的哈希；本补充审阅更新当前状态，原实施记录作为历史证据保留。
`policy_finalized=false`与`d2_authorized=false`继续有效。
停止在D1人工审阅，不训练新模型、不解封outcome、不访问2024+。
