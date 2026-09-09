# Research Protocol V3-MVP P0–P2 验收报告

状态：`P0–P2 COMPLETE / STOP FOR HUMAN REVIEW`。运行：`v3_mvp_20260909_v2`；contract hash：`6a3189ca60450d9cba7a37833c3a732f965de1e053d8dcf567d5beb25cb71682`。

## 结果

- P0 物化2015–2023九个年度fold；预测日2,189，开发期成熟评价日2,168；每折exact purge 21个边界训练signal，额外embargo为0。
- P1 完成2010–2023共14个年份、765项research-usable因子的分批feature-only审计；训练有限标签合计按折分别为2,091,683至5,790,153，所有fold每日最低有限标签对数930以上，未出现少于100对的训练或评价日。
- P1身份诊断：physical 765、broad working set 494、strict 3-of-3 332。Baseline与Human/Economic池仍未冻结，不能启动四池比较。
- P2固定LightGBM 4.6.0、100轮、8线程、原生NaN；2015和2023工程canary均完成annual fit、整年/按月预测parity和模型receipt。2015 peak RSS约622MiB、fit约2.1s；2023 peak RSS约1,111MiB、fit约5.3s。

## 阻塞与边界

2015八列工程canary预测覆盖94.8786%，低于计划95%年度coverage提示线；2023为99.9934%。这是所选诊断列在早期数据的覆盖结果，不能推断完整池，也不能通过删除该年绕过。`full_width_resource_qualified=false`：494列最大折原始float64矩阵约22.5GiB，当前约28GiB物理内存不足以把完整矩阵并行复制；未取得完整池资源资格。

因此最终状态为：`protocol_ready=true`、`pool_experiment_ready=false`。本轮没有读取2024+值、计算IC/收益/importance、选择winner、运行P3或近期诊断。P2 canary是工程验收，不是模型表现证据。

在用户清理内存后重试，494列首折wide canary已通过：float32磁盘memmap、按年读取、单次LightGBM构建，2,091,683行、100轮、fit约29.5秒，实测peak RSS约21.6GiB。该结果说明工程优化可行，但峰值仍接近本机物理内存上限；最大折（2023）尚未测量，因此`full_width_resource_qualified`仅对首折工程canary成立，不能外推全量36次fit。

## 证据入口

- 机器状态：[status.json](../../outputs/research_protocol_v3_mvp/v3_mvp_20260909_v2/status.json)
- P0折表：[folds.csv](../../outputs/research_protocol_v3_mvp/v3_mvp_20260909_v2/p0/folds.csv)
- P1样本计数：[sample_counts.csv](../../outputs/research_protocol_v3_mvp/v3_mvp_20260909_v2/p1/sample_counts.csv)
- P1资格汇总：[feature_eligibility.csv](../../outputs/research_protocol_v3_mvp/v3_mvp_20260909_v2/p1/feature_eligibility.csv)
- P2资源：[annual_2015/resource.json](../../outputs/research_protocol_v3_mvp/v3_mvp_20260909_v2/canary/annual_2015/resource.json)、[annual_2023/resource.json](../../outputs/research_protocol_v3_mvp/v3_mvp_20260909_v2/canary/annual_2023/resource.json)

全部运行输出为本机runtime，未提交大型parquet、模型或逐样本label到Git；上游Canonical、Primary、Consolidation和Forward证据未修改。
