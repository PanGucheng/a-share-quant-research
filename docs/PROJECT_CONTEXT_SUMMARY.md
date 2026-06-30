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
outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml
```

- TA 已有 77 个 promoted runnable 因子、2 个 holdout。
- KunQuant Alpha101 已有 64 个 promoted runnable 因子、18 个 holdout。
- Qlib Alpha360 已有 358 个 promoted runnable 因子、2 个 adapter holdout。

Multi-source toolchain：

```text
outputs/multi_source_screening_v1/current/multi_source_screening_input.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostic_board.csv
outputs/new_source_probe_review_v1/current/probe_review_board.csv
outputs/alpha360_strict_oos_extension_v1/current/strict_oos_contract_status.csv
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_contract_status.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_contract_status.csv
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_contract_status.csv
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv
```

- Readiness 当前为 `ready`。
- total runnable factors: 669。
- new-source runnable factors: 499。
- multi-source screening rows: 679。
- multi-source judgement research candidates: 342。
- new-source alpha probes: 328（TA 15，Alpha101 14，Alpha360 299）。
- new-source probe diagnostics: 328 probes、120 个 frame diagnostics、50 个 portfolio smoke probes、4 次实际调仓，contract pass。
- new-source probe review: 4 个冗余组、19 个 tradability exposure watchlist、3 个严格 OOS extension candidates（`alpha360_HIGH36`、`alpha360_HIGH37`、`alpha360_HIGH40`），contract pass。
- Alpha360 strict OOS extension: 3 个严格候选 recent-OOS frame 286,944 行，min coverage 0.996236，V4 metric index 54 行，contract pass。
- Alpha360 strict OOS stability: main vs recent metric pairs 54 行，recent Alphalens mean IC min 0.063736，recent Qlib IR min 5.025121，signal sign flips 0，contract pass。
- Tradability exposure attribution: 19 个 watchlist 全部归因，主代理均为 `liquidity_value`；14 个建议 holdout/residualization first，4 个 manual review，1 个 residualization candidate review。
- Exposure data capability audit: FactorTest/qlib_factor_platform 参考能力存在；项目 context/tradability/data_quality 可用；当前 provider 缺市值、行业和 Barra 字段。
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
- V3.32 Alpha360 358 因子 batch V4 已完成：358 promoted、0 V4 batch holdout；已接入 multi-source screening / judgement。
- V3.33 new-source probe diagnostics 已完成：328 probes 全量看板、相关性诊断、tradability exposure 代理诊断、TopK portfolio smoke 均已接入 readiness。
- V3.34 new-source probe review 已完成：冗余/暴露复核层已接入 readiness，严格 OOS 候选收缩到 3 个 Alpha360 high-window 代表因子。
- V3.35 Alpha360 strict OOS extension 已完成：3 个严格候选在 2024-2026 recent OOS 窗口重新生成 factor frame，并通过 V4 多评价体系与 contract audit。
- V3.36 Alpha360 strict OOS stability 已完成：主窗口与 recent-OOS 指标对齐，信号指标无符号翻转，候选仍保持研究状态。
- V3.37 Tradability exposure attribution 已完成：19 个高可交易性暴露 probes 已分层，直接 raw training 前需要 holdout、人工复核或 residualization。
- V3.38 Exposure data capability audit 已完成：当前 provider 不支持市值/行业/Barra 字段，不能直接做 FactorTest-style industry/Barra neutralization。
- V3.39 Liquidity residualized factor evaluation 代码链路已完成但 contract blocked：19 个 watchlist probes 通过每日横截面 OLS 残差化（configured proxies: `liquidity_value`, `liquidity_bucket`, `tradability_score`；常数 proxy 会按日自动剔除）。残差列后缀 `__resid_liquidity`，不覆写原始因子。产出了 residualized factor frame、每日诊断、raw-vs-residualized 比较、候选动作决策与 contract status。当前 `residualized_coverage_min=0.1495 < 0.80`，audit 正确失败；downstream default 仍为 0。
  关键输出：
  ```text
  outputs/liquidity_residualized_factor_evaluation_v1/current/
    residualized_factor_frame.pkl
    residualized_factor_summary.csv
    daily_residualization_diagnostics.csv
    raw_vs_residualized_metric_comparison.csv
    residualized_candidate_actions.csv
    liquidity_residualized_contract_status.csv
    liquidity_residualized_factor_evaluation_report.md
  ```
- 下一步：先复核低覆盖来源，暂不把 V3.39 结果用于训练或默认候选；随后设计外部行业/市值数据接入 contract。
- 后续继续接入更多开源因子源，但必须沿用 source audit、adapter、V4 batch、promotion/holdout、multi-source screening、multi-source judgement 的路径。
