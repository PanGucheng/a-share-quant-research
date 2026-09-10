# D2 完成核验

2026-09-11：**D1 CLOSED / REPRESENTATIONS FROZEN / D2 COMPLETE / ALL FIVE ARMS SEALED**。
用户完成运行后，168个月表示缓存、27模型及27份独立replay回执全部通过完整性核验。
无需重跑。停止等待D3的单独授权。

## 结果与身份

| 表示 | 列数 | 年度模型 | prediction行数 | prediction日期 | 工程coverage | 独立重放 |
|---|---:|---:|---:|---:|---:|---|
| R | 218 | 9 | 4,377,824 | 2,189 | 每折100% | all_nine_exact |
| C | 201 | 9 | 4,377,824 | 2,189 | 每折100% | all_nine_exact |
| H | 358 | 9 | 4,377,824 | 2,189 | 每折100% | all_nine_exact |

新生成prediction共13,133,472行。已有Broad494/Strict332各九折独立重放仍为all_nine_exact；
五臂合计45模型、21,889,120行prediction保持封存。coverage只是工程资格，不是效果判断。

- D1冻结提交：`d05e7eb`；D2运行代码：`a8284202257545223fb9fcbd38abdef4303eb913`。
- freeze hash：`29e473cedcefa2715bb770188d64da23db579e509bb2a99982e93b8885d24ccc`。
- recipe hash：`8b688bd098ebafd1c1da2bab32d029624f6da65f7166c59f702fbc18499cf51f`。
- run contract：`25b801854c073c2fc246756a84f05eedb182aa4edfb0f880516edc846ec37f29`。
- [逐折模型SHA及工程资源](completion_v1/folds.csv)、[独立重放结果](completion_v1/replay_results.json)、
  [核验及全部receipt哈希](completion_v1/verification.json)、[交付文件哈希](completion_v1/hashes_lf.json)。

U61、family内50%可用节点、跨family全可用、economic-axis方向及n_min100均未改变。
保留recursive raw U质量限制、Alpha101未解经济语义和dense variable-node composition caveats。

## 九折共同键轴

以下train/prediction行数对R/C/H全部成立。每月训练键哈希、行数与B/S两个原基准完全相同。

| Fold | train行数 | prediction行数 |
|---|---:|---:|
| 2015 | 2,091,683 | 487,993 |
| 2016 | 2,494,922 | 488,000 |
| 2017 | 2,938,932 | 488,000 |
| 2018 | 3,391,417 | 485,999 |
| 2019 | 3,854,187 | 487,969 |
| 2020 | 4,339,529 | 485,973 |
| 2021 | 4,823,170 | 485,981 |
| 2022 | 5,307,701 | 483,983 |
| 2023 | 5,790,153 | 483,926 |

V3 LightGBM4.6.0、float64 Sequence、固定100轮/8线程、目标、daily-equal权重、purge、maturity和运行环境均匹配。
所有独立预测score、keys/date、missing reason验证为exact；独立naive表示最大差
`3.885780586188048e-16`，在预注册的rtol=0/atol=1e-12内，未启用预测容差fallback。

## 资源与恢复记录

表示缓存168个月、6,640,610行，磁盘14,387,569,191字节（约13.40 GiB）。
缓存回执累计41.33分钟；27模型单元累计62.98分钟；独立replay计时累计171.68分钟。
这些计时合计约4.60小时，未含所有进程启动、阶段间校验和等待，不能称作完整端到端墙钟时长。

H2023实测峰值RSS 3,666.53 MiB（约3.58 GiB），低于12 GiB门槛；
prepare130.79秒、dataset29.90秒、fit66.11秒、predict17.21秒。
其一折临时float64块16,582,998,192字节，完成后按合同记录hash并删除；正式缓存与结果保留。
各fold实测资源见上述CSV，不据此推断预测优劣。

本run未发现failure.json或残留incomplete目录。完成单元的跳过/续跑次数没有独立日志，
因此只能说明现存证据完整，不能断言从未中断或精确恢复次数。

## 本次核验范围

新脚本只核验当前source/runtime/freeze/run合同、全部缓存/模型/replay/sealed文件哈希及工程metadata。
核对15,744条完成的特征切片访问记录与D1证据相同，列/日期在允许范围；
逐折train/predict访问日期、缓存receipt绑定、表示依赖/类型、模型与重放绑定、封存汇总重建均通过。

真正独立的canonical数值重建及saved-Booster逐值预测重放发生在用户运行中。
本轮没有重新加载canonical研究值或prediction scores进行计算；读取输出字节用于checksum，不解释分数。
实现阶段53项定向测试仍为已有验证证据，本次未修改数值代码或重复运行长计算。
没有运行可能读取历史outcome/近期证据的全仓full validators。

OUTCOME EVALUATION NOT AUTHORIZED；POOL PERFORMANCE COMPARISON NOT AUTHORIZED；
2024+研究值未访问；Strategy V1/V2边界不变；不自动进入D3。
