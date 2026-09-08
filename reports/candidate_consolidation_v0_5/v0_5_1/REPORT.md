# Candidate Consolidation V0.5.1 修订提案

状态：修订版已生成，停止供人工审阅；没有Core、删除或自动替换。

保留494成员和765语义记录；active中462项恢复了明确语义、窗口和量纲。旧版104条条件替代逐条复核，新版共有0条跨层级条件替代提案；数量是规则结果，不是压缩目标。

新规则将不同指标方法、窗口、会计口径分开；语义未知、价格尺度未确认及状态/递归缺失问题暂缓替代。排序移除运行说明构造的公式复杂度。任何近似替代都必须通过已有Full和四Era的可比、q10及符号标准。单例展示可比与未知pair数量，不称为独立信息。

五组精确重复单独登记为开发期等值关系，保留全部身份和原Primary方向；未把某个聚类cut或簇数当成最终池大小。

[494行新版提案](representative_proposal_board.csv)、[全部变更及原因](proposal_changes.csv)、[实际pair证据](member_representative_evidence.csv)、[语义表](economic_semantic_review.csv)、[五组关系登记](exact_alias_registration.csv)、[低覆盖审阅](low_coverage_review.csv)、[递归缺失实验](recursive_gap_diagnostic.csv)、[真实样本核对](real_gap_diagnostic.csv)、[有界读取记录](DIAGNOSTIC_ACCESS.json)、[来源核验](SOURCE_AUDIT.json)、[验收](VALIDATION.json)。

ATR和ADX +/- 的固定源码递归会传播内部缺失；合成实验用于解释这种行为，不冒充对全部真实缺失的归因。canonical值和Primary不修写。价格单位和完整provider处理链尚未核定，价格相关提案保持暂缓；行业仍无开发期覆盖。32项active Alpha101的实现语义继续待逐项复核。

真实核对共9个股票—指标组合，累计0个值/mask差异（rtol=1e-7、atol=1e-8）。原始输入本身存在缺失，PIT mask后进入递归；该证据解释所选样本，不代表全市场缺失均有相同来源。[价格尺度审计](PRICE_SCALE_AUDIT.json)保留已知与未知边界。

本次复用2010–2023汇总，另对2013年三只股票的三个指标作有界核对，原始输入从2011-10-13开始以复现300交易日warmup。未重跑日Spearman或收益评估。原版receipt绑定文件逐hash不变；修订版独立发布，外部全量命令无需重跑。
