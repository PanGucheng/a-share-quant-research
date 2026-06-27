# Project Context Summary

本文件用于在对话很长时快速恢复上下文。

## Project

路径：

```text
E:\qlib_prj\qlib_baseline
```

目标：

- 面向量化新手，基于 Qlib 和开源项目整合 A 股量化研究框架。
- 当前重点是因子研究、因子筛选、数据质量和可交易性约束。
- 不急于训练新模型，不做实盘，不替换 Qlib baseline。

## Environment

Python：

```text
E:\anaconda_envs\qlib_env\python.exe
```

Qlib 源码：

```text
E:\qlib_prj\qlib_clone
```

默认数据：

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
```

重要运行经验：

- 完整 qrun 或长任务应直接用本地普通权限运行，不要在受限沙盒里跑。
- Windows multiprocessing 需要 `freeze_support()`。
- 临时参考仓库放在 `tmp/reference_repos/`，该目录被 `.gitignore` 忽略。

## Current Factor Research Status

V2 / V3 早期：

- 已实现因子注册、IC/Rank IC、分组收益、换手率、覆盖率、相关性、候选筛选。
- 已实现预处理、中性化、切片诊断和暴露相关性。
- 早期结论是 `amplitude_20` 更像风险/流动性暴露，`std_20` 与其高度冗余，`rev_5` 还不足以直接 promote。

Alpha158 reference pipeline：

```text
outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
```

- Alpha158 已作为验证研究机器的参照链路，不再作为唯一细挖对象。
- 155 个 Alpha158 因子进入 runnable catalog，14 个进入当前默认 `alpha_candidate`。

Open-source factor sources：

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_promoted64.yaml
```

- TA 已有 77 个 promoted runnable 因子、2 个 holdout。
- KunQuant Alpha101 已有 64 个 promoted runnable 因子、18 个 holdout。

Multi-source toolchain：

```text
outputs/multi_source_screening_v1/current/multi_source_screening_input.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
```

- Readiness 当前为 `ready`。
- total runnable factors: 311。
- new-source runnable factors: 141。
- multi-source screening rows: 319。
- multi-source judgement research candidates: 43。
- new-source alpha probes: 29（TA 15，Alpha101 14）。
- `new_source_alpha_probe` 是研究队列，不是默认模型或组合输入。

## Open Source References

已拉取参考：

```text
tmp/reference_repos/jqfactor_analyzer
tmp/reference_repos/FactorTest
tmp/reference_repos/multi-factor
tmp/reference_repos/AlphaTrading
tmp/reference_repos/alphalens-reloaded
tmp/reference_repos/qlib_factor_platform
tmp/reference_repos/GetAstockFactors
tmp/reference_repos/ChinaAShareEquityCharacteristics
tmp/reference_repos/techfactor
```

参考规则：

- 优先借鉴成熟口径和模块边界。
- 不复制无 license 项目代码。
- 不引入复杂 UI。
- 不绕过现有 data_quality/tradability。

## Next Work

当前下一阶段：

- 不继续围绕单个 Alpha158、TA 或 Alpha101 因子细调策略。
- V3.28 `qlib_alpha360` source audit 与 adapter smoke 已完成：360 个 Qlib 原生公式全部可用，24 个 smoke 因子已生成 expression frame。
- V3.29 Alpha360 V4 smoke 已完成：22 个非恒等 smoke 因子进入 V4；Alphalens/Qlib eval 全部 pass，jqfactor_analyzer 保留已知 partial。
- V3.30 Alpha360 batch catalog/dry-run 已完成：358 个 batch candidates、2 个 adapter holdouts、72 个 planned dry-run batches。
- V3.31 Alpha360 batch358 factor frame 与真实 smoke batch_001 已完成：358 因子 frame 生成成功，batch_001 pass。
- FactorTest-style 行业/风格/Barra 暴露诊断应先做数据能力审计。
- 下一步以 resume / max-batches 限制继续执行 Alpha360 剩余 batch，再做 promotion/holdout。
- 对现有 29 个 `new_source_alpha_probe` 增加更长 OOS、相关性/暴露和组合 smoke 验证后，再考虑训练输入。
