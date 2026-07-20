# Qlib A 股量化研究基线项目

本项目是一个围绕 [Microsoft Qlib](https://github.com/microsoft/qlib) 搭建的
A 股量化研究工程。它最初用于复现官方 LightGBM + Alpha158 baseline，现在正在扩展为一个适合量化新手逐步学习和实践的研究框架：先保证数据、可交易性和因子评价可靠，再考虑模型、组合和回测。

> 本项目仅用于研究和学习，不构成投资建议，也不包含实盘交易代码。

## 当前方向

> **当前里程碑：**PR #4 已完成 669 因子的工程规模化，包括 30 个可恢复特征分区、
> t+1 标签、daily IC、outer purged splits 和三段 Qlib Exchange。合并后审计发现当前
> selection/stability 与 clustering 受到 outer-test 数据影响，raw/source provenance
> 也不完整。因此 16 个代表只作为探索证据，模型 readiness 已暂停，模型训练尚未启动。

项目坚持一个原则：不替换 Qlib 主线，而是在 Qlib 外围补齐研究工程能力。

当前主线包括：

- **Qlib baseline**：已验证官方 LightGBM + Alpha158 工作流可以跑通。
- **数据质量诊断**：检查缺失值、价格成交异常、生命周期问题和逐行数据问题。
- **可交易性标签层**：把流动性、数据质量和交易约束转成统一标签。
- **因子研究模块**：在数据质量和可交易性过滤之后，评价 IC、Rank IC、ICIR、分组收益、换手率、覆盖率、缺失率、相关性、单调性、切片稳定性和中性化效果。
- **因子筛选模块**：把因子研究输出转成可解释的候选看板，再交给后续组合测试。
- **Qlib execution 层**：固定版本的 Exchange/Executor adapter、A 股约束、标准化 artifact、合成精确对账和本地真实小样本均已落地。

当前优先级是强制完成 Selection Holdout Integrity：先机器级阻断残留的 model-ready 状态，再补齐 raw/source provenance，建立 outer-train FDR eligibility 与 development robustness windows，真实消费 split-scoped FDR，并按 outer split 的 development dates 重建 allowlist。任何大批量重跑都必须先提交 review bundle，由用户针对 exact run 明确批准；只有 anti-leakage 与 pre-test freeze 门禁通过后，才按透明基线、Ridge、Elastic Net、LightGBM 顺序进入模型阶段。

## 目录结构

```text
configs/          Qlib qrun 工作流配置。
data_quality/     数据质量诊断模块。
tradability/      可交易性标签构建与报告。
factor_research/  因子评价、预处理、中性化和报告模块。
scripts/          可复现运行脚本和汇总脚本。
docs/             当前开发文档，以及已归档的历史计划和审计记录。
outputs/          已验证输出和较小的研究汇总结果。
logs/             保留的 baseline 日志和本地运行日志。
tmp/              被忽略的本地缓存、参考仓库和临时输出。
```

## 本地环境

当前已验证环境：

```text
项目目录：        E:\qlib_prj\qlib_baseline
Python 环境：     E:\anaconda_envs\qlib_env\python.exe
Qlib 源码仓库：   E:\qlib_prj\qlib_clone
原始 Qlib 数据：  E:\qlib_prj\qlib_data\cn_data
衍生数据目录：    E:\qlib_prj\qlib_data\cn_data_community_20260609_derived
```

如果遇到 Qlib 编译扩展缺失，例如：

```text
ModuleNotFoundError: No module named 'qlib.data._libs.rolling'
```

先在本地源码仓库中安装 Qlib：

```powershell
cd E:\qlib_prj\qlib_clone
conda activate qlib_env
python -m pip install setuptools-scm
python -m pip install -e .
```

Windows 下源码版 Qlib 需要生成类似下面的编译扩展：

```text
qlib\data\_libs\rolling.cp310-win_amd64.pyd
qlib\data\_libs\expanding.cp310-win_amd64.pyd
```

## 复现 baseline

不要在 Qlib 源码目录里直接跑实验，应该进入独立项目目录：

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_baseline.ps1
```

baseline runner 使用了项目内临时目录 wrapper，解决 Windows multiprocessing 和 tempfile 权限问题。完整 qrun 实验建议使用本机普通权限运行，不要放在受限沙盒里跑。

关键文件：

```text
configs/workflow_lightgbm_alpha158_csi500.yaml
scripts/qrun_with_project_tmp.py
logs/qrun_lightgbm_alpha158_csi500_20260611_113628.log
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15
```

## 数据质量与可交易性

运行数据质量诊断：

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_data_quality.ps1 --config data_quality\config.yaml
```

生成可交易性标签：

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_tradability_labels.ps1
```

因子研究必须复用这两层输出。可交易性标签是因子评价的前置过滤条件，不是事后可选项。

## 因子研究 V3

运行当前因子研究主流程：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --output-dir outputs\factor_research_v3\liquid2000_core
```

默认研究范围：

```text
股票池： all_stock_shsz_liquid2000
标签：   label_20d_t1
因子：   amplitude_20, std_20, rev_5, ret_20, amount_mean_20
窗口：
  main_research_2021_2023
  recent_oos_2024_2026
```

主要输出：

```text
outputs/factor_research_v3/liquid2000_core/factor_neutralized_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_neutralized_group_return_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_ic.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_group_return_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_exposure_correlation.csv
outputs/factor_research_v3/liquid2000_core/factor_exposure_report.md
outputs/factor_research_v3/liquid2000_core/factor_candidate_changelog.csv
outputs/factor_research_v3/liquid2000_core/factor_research_v3_report.md
```

默认不会写出大体积的逐日逐分组明细 CSV。需要深挖分组收益时，再显式加：

```powershell
--write-detail
```

## 因子筛选 V3.3

基于 V3 输出生成当前因子候选看板：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_screening_v3.py
```

主要输出：

```text
outputs/factor_screening_v3/liquid2000_core/factor_candidate_board.csv
outputs/factor_screening_v3/liquid2000_core/factor_screening_report.md
```

当前默认结果：

```text
rev_5          research_candidate
amplitude_20   risk_exposure
std_20         risk_exposure
ret_20         watch
amount_mean_20 watch
```

## 因子候选池 V3.4

将筛选结果固化成后续组合回测可读取的候选池：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_candidate_pool_v3.py
```

主要输出：

```text
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.csv
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.json
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool_report.md
```

当前角色：

```text
rev_5          alpha_candidate
amplitude_20   risk_control
std_20         risk_control
ret_20         monitor
amount_mean_20 monitor
```

V3.5 已小批量扩展参考因子，并将结果写入独立 expanded 目录：

```text
outputs/factor_research_v3/liquid2000_expanded
outputs/factor_screening_v3/liquid2000_expanded
outputs/factor_candidate_pool_v3/liquid2000_expanded
```

当前 expanded alpha 候选：

```text
rev_20_exclude_5
rev_5
```

## 缓存与加速

因子研究默认启用本地缓存，缓存目录被 `.gitignore` 忽略：

```text
tmp/factor_feature_cache
tmp/factor_frame_cache
```

常用参数：

```powershell
--refresh-feature-cache
--refresh-factor-cache
--no-feature-cache
--no-factor-cache
```

使用建议：

- 日常重复跑同一窗口时，直接使用默认缓存。
- 更新 Qlib 数据、股票池或基础字段后，使用 `--refresh-feature-cache --refresh-factor-cache`。
- 只修改基础因子或 label 计算逻辑后，使用 `--refresh-factor-cache`。
- 排查原始数据读取问题时，使用 `--no-feature-cache --no-factor-cache`。

近期 smoke 测试耗时：

```text
原始 profile：           约 50.4s
raw feature cache 命中： 约 11.5s-12.2s
basic factor cache 命中：约 9.9s
```

## 时点正确的因子研究上下文

构建并验证基准收益、历史股票池成员资格和上市年龄上下文：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_factor_context_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_context_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_context_smoke.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_evaluation_context.py
```

该模块直接读取现有 Qlib provider 的成分区间和基准特征，只为因子评价补充上下文，不绕过既有数据质量检查与可交易性前置过滤。历史设计说明已归档到 `docs/_archive/03_factor_research_history/FACTOR_CONTEXT_V1.md`。

## 批量因子评估 V1

后续扩张因子池前，先使用因子目录和批量 runner 管理来源、分批运行和断点续跑：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_smoke.yaml --dry-run
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1.yaml
```

核心文件：

```text
factor_research/factor_catalog.yaml
factor_research/catalog.py
scripts/run_factor_evaluation_batch_v1.py
docs/_archive/03_factor_research_history/FACTOR_BATCH_EVALUATION_V1.md
```

该模块只负责选择因子、生成 V4 配置、记录 manifest 和失败批次。具体 IC、分组收益、换手率和上下文评价仍由 V4 调用 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 和本项目已有输出完成。

## Qlib Alpha158 因子来源审计

抽取本地 Qlib 源码中的 Alpha158 公式，并检查当前 provider 是否具备所需字段：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha158_catalog_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_metadata_smoke.yaml --dry-run
```

当前审计结果：

```text
Alpha158 formulas: 158
field_status=available: 158
first batch metadata entries: 20
```

首批 20 个 Alpha158 条目已经在 expression adapter、V4 smoke 和 context validation 通过后，单独生成了 runnable catalog。Alpha158 全量 158 个因子的扩张仍然是下一阶段任务。

## Qlib Alpha158 首批 20 个因子评价

构建并验证首批 Alpha158 expression frame：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_v1.yaml
```

运行首批 20 个因子的 V4 评价与 context 验证：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_alpha158_first20.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_evaluation_context.py --output-dir outputs\factor_evaluation_v4\alpha158_first20_smoke
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_alpha158_first20.py
```

运行可断点续跑的 batch 版本：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_first20.yaml --dry-run
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_first20.yaml
```

当前结果：

```text
expression frame rows: 1,603,860
factor count: 20
adapter validation: pass
Alphalens Reloaded: pass 20
jqfactor_analyzer: partial_pass 20
Qlib eval: pass 20
context: pass 240, skipped_non_informative 80
combined metric index rows: 4,200
```

关键输出：

```text
outputs/alpha158_expression_frame_v1/first20_main_research/
outputs/factor_evaluation_v4/alpha158_first20_smoke/
outputs/factor_evaluation_batch_v1/alpha158_first20/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml
```

大体积的 `factor_frame.pkl` 和逐 batch 明细运行目录已被 `.gitignore` 排除，Git 只保留 compact manifest、summary、validation report 和 metric index。

## Qlib Alpha158 全量扩张与筛选输入

Alpha158 全量评价阶段已经完成。当前不重复评价已完成的 first20，而是复用 first20 结果，并将 remaining138 的 batch 评价结果合并成 full Alpha158 筛选输入。

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha158_full_stage_catalogs_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_full_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_full_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_remaining138.yaml --max-batches 1
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_screening_input_v1.py --config configs\factor_screening_alpha158_full_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_judgement_v1.py --config configs\factor_judgement_alpha158_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_pool_v1.py --config configs\factor_candidate_pool_alpha158_v1.yaml
```

当前进展：

```text
full158 expression frame：通过，1,603,860 行，158 个因子
remaining138 batch：13 个 pass，1 个 skipped_existing
remaining138 strict runnable：135 个
remaining138 holdout：3 个
full strict runnable catalog：155 个因子
full screening input：158 行
strict_screening_input：155 个因子
screening holdout：3 个因子
judgement board：158 行
redundancy clusters：23 个
strong_signal：10 个
consistent_signal：4 个
redundant：55 个
candidate pool：158 行
alpha_candidate：14 个
excluded_redundant：55 个
excluded_high_turnover：33 个
excluded_unstable_context：16 个
monitor：37 个
holdout：3 个
```

关键输出：

```text
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_screening_input.csv
outputs/factor_screening_alpha158_v1/full158/alpha158_full_screening_input_report.md
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_correlation_top_pairs.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_board.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_report.md
outputs/factor_judgement_alpha158_v1/full158/alpha158_redundancy_clusters.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool_report.md
```

当前 Alpha158 candidate pool 是后续模块默认读取的 alpha 输入。它保留 158 行完整角色表，同时单独暴露 14 个 `alpha_candidate` 给下一阶段组合 smoke 使用。这里仍然是研究输入，不是交易信号。

## Alpha158 候选组合 smoke

从冻结后的 Alpha158 候选池运行当前组合接口 smoke：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_v1.yaml
```

当前 smoke 结果：

```text
candidate_count: 14
warning_low_monotonicity_count: 4
trading_days: 700
executed_rebalances: 35
net_annualized_excess: 0.060632
net_excess_ir: 0.552843
average_turnover: 0.824857
```

关键输出：

```text
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/summary.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/alpha158_candidate_portfolio_smoke_report.md
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/candidate_weight_table.csv
```

这只是接口 smoke，不是可直接使用的策略结论。当前平均换手率偏高，下一阶段应该先补齐组合诊断，再判断是否进入策略优化或扩张新因子。

## Alpha158 组合诊断

运行当前诊断层：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_v1.yaml
```

当前诊断结果：

```text
single_factor rows: 14
best single factor: alpha158_ROC30
best single factor net_excess_ir: 0.803985
topk_50 net_excess_ir: 0.676352
topk_100 net_excess_ir: 0.552843
topk_200 net_excess_ir: 0.405610
cost_20bps net_excess_ir: 0.465720
```

关键输出：

```text
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/alpha158_portfolio_diagnostics_report.md
```

## Alpha158 recent OOS

当前已经为 14 个 Alpha158 候选因子单独构建了 2024-2026 recent OOS expression frame，并跑通组合 smoke 与诊断：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_candidate_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml --candidate-pool outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_recent_oos_v1.yaml
```

当前 recent OOS 结果：

```text
expression rows: 1,096,231
min factor coverage: 0.995898
topk_100 net_excess_ir: 0.221295
average_turnover: 0.799286
best single factor: alpha158_VSUMN60
```

这个结果弱于 2021-2023 main window，因此下一步应先做稳定性与暴露诊断，而不是直接进入策略优化。

## Alpha158 稳定性诊断

main 与 recent OOS 稳定性诊断：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_stability_diagnostics_v1.py --config configs\alpha158_stability_diagnostics_v1.yaml
```

当前稳定性结果：

```text
weak_or_negative_oos: 8
positive_but_weaker_oos: 3
main_only: 2
oos_improved: 1
topk_100 net_excess_ir delta: -0.331548
bucket_3 exposure share delta: +0.063357
```

关键输出：

```text
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/alpha158_stability_diagnostics_report.md
```

## 因子研究工具链 readiness

Alpha158 现在应作为“已验证研究流水线”的参照，而不是继续细抠的唯一研究对象。扩张几百个新因子前，先运行工具链 readiness 闸门：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

当前 readiness 结果：

```text
prefilter_policy: pass
open_source_evaluator_systems: pass
batch_runner: pass
required_output_contracts: pass
runnable_factor_inventory: pass
new_source_adapter_inventory: pass
generic_multi_source_screening: pass
generic_multi_source_judgement: pass
total_runnable: 669
new_source_runnable: 499
```

这说明 Alpha158 参照链路、TA、Alpha101 与 Alpha360 三类非 Alpha158 promoted 来源，以及通用多来源 screening / judgement 契约都已经准备好。下一阶段应该先补新来源 probes 的相关性、暴露、稳定性、组合 smoke 等诊断，再继续扩张更多开源因子源，而不是继续只围绕 Alpha158 细挖。

关键输出：

```text
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
```

## TA 因子 adapter 与 batch promotion

第一个非 Alpha158 开源因子源已经通过 `bukosabino/ta` 接入，并完成 smoke 与剩余 batch 验证。

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_ta_factor_adapter_smoke_v1.py --config configs\ta_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\ta_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_smoke_catalog_entries_v1.py --config configs\ta_factor_smoke_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_ta_batch_catalogs_v1.py --config configs\ta_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_ta_remaining74.yaml --max-batches 15 --output-root outputs\factor_evaluation_batch_v1\ta_remaining74_batch1
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_batch_catalog_entries_v1.py --config configs\ta_factor_batch_promotion_v1.yaml
```

当前 TA 结果：

```text
eligible TA factors: 79
excluded TA columns: 7
smoke promoted: 5
remaining batch evaluated: 74
batch promoted: 72
batch holdout: 2
combined promoted TA catalog: 77
```

两个 holdout 因子是 `ta_volatility_bbli` 和 `ta_volatility_kchi`。它们通过了 Qlib eval，但 Alphalens quantile turnover 没有产生数值，因此暂不进入 promoted runnable catalog。

## 多来源 screening contract

基于 Alpha158、promoted TA、Alpha101 和 Alpha360 因子生成通用筛选输入与候选池：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
```

当前结果：

```text
screening rows: 679
sources: 4
Alpha158 strict rows: 155
TA strict rows: 77
Alpha101 strict rows: 64
Alpha360 strict rows: 358
holdouts: 25
alpha candidates: 14
contract status: pass
```

TA、Alpha101 和 Alpha360 promoted 因子在 screening contract 中仍保守放入 `monitor`，不会直接当成 alpha 信号。后续由通用 judgement 层决定哪些新来源因子进入研究 probe 队列。

## 多来源 judgement

在 multi-source screening 输入之上生成通用研究分层表：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_judgement_v1.py --config configs\multi_source_judgement_v1.yaml
```

当前结果：

```text
judgement board rows: 679
research candidates: 342
new-source alpha probes: 328
TA probes: 15
Alpha101 probes: 14
Alpha360 probes: 299
contract status: pass
```

`new_source_alpha_probe` 只是后续研究队列，不是默认模型或组合输入。Alpha158 保留既有 14 个 `alpha_candidate`；promoted TA、Alpha101 和 Alpha360 因子在更大范围验证前只会进入 probe。

## 新来源 probe 诊断

对 328 个 `new_source_alpha_probe` 运行第一层诊断：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_diagnostics_v1.py --config configs\new_source_probe_diagnostics_v1.yaml
```

当前结果：

```text
all probes: 328
frame diagnostics selected: 120
portfolio smoke selected: 50
correlation pairs: 200
portfolio smoke executed rebalances: 4
new_source_probe_diagnostics: pass
```

组合 smoke 只是接口和风险诊断，不是策略结论。本轮已经暴露出部分 TA / Alpha101 因子高度冗余，部分 probe 与可交易性/流动性代理有较强相关。下一步应先做冗余和暴露复核，再考虑模型训练。

第一层 probe review 也已经完成：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_review_v1.py --config configs\new_source_probe_review_v1.yaml
```

当前 review 结果：

```text
review rows: 328
redundancy pairs: 200
redundancy groups: 4
tradability exposure watchlist: 19
strict OOS extension candidates: 3
new_source_probe_review: pass
```

严格候选是 `alpha360_HIGH36`、`alpha360_HIGH37`、`alpha360_HIGH40`。它们仍然只是研究候选，不是训练输入。

这 3 个候选的 strict recent-OOS extension 也已经完成：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_strict_oos_recent_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_strict_oos_recent.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_extension_v1.py --config configs\alpha360_strict_oos_extension_audit_v1.yaml
```

Strict-OOS 结果：

```text
recent OOS factor frame rows: 286,944
min coverage: 0.996236
V4 batches: 1 pass
metric index rows: 54
alpha360_strict_oos_extension: pass
```

3 个因子在 recent-OOS 中仍保持正 mean IC，但这只是诊断结果，不代表进入训练或策略结论。

main-vs-recent 稳定性 audit 也已经完成：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_stability_v1.py --config configs\alpha360_strict_oos_stability_v1.yaml
```

稳定性结果：

```text
metric pairs: 54
recent Alphalens mean IC min: 0.063736
recent Qlib information ratio min: 5.025121
signal sign flips: 0
alpha360_strict_oos_stability: pass
```

19 个 tradability exposure watchlist probes 也已经完成归因：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_tradability_exposure_attribution_v1.py --config configs\tradability_exposure_attribution_v1.yaml
```

归因结果：

```text
watchlist rows: 19
primary proxy: liquidity_value for all 19
holdout before/residualization actions: 14
manual review: 4
residualization candidate review: 1
tradability_exposure_attribution: pass
```

FactorTest-style 暴露数据能力审计也已经完成：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_exposure_data_capability_v1.py --config configs\exposure_data_capability_audit_v1.yaml
```

能力审计结果：

```text
reference industry/size/Barra design: available
project context/tradability/data_quality: available
provider size fields: missing
provider industry fields: missing
provider Barra fields: missing
exposure_data_capability_audit: pass
```

所以下一步不能直接跳到行业/Barra 中性化；需要先接外部行业/市值数据，或先走更小的 liquidity residualization 路径。

关键输出：

```text
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_DIAGNOSTICS_V1.md
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_REVIEW_V1.md
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_EXTENSION_V1.md
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_STABILITY_V1.md
docs/_archive/06_probe_and_tradeability_audits/TRADABILITY_EXPOSURE_ATTRIBUTION_V1.md
docs/_archive/06_probe_and_tradeability_audits/EXPOSURE_DATA_CAPABILITY_AUDIT_V1.md
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostics_report.md
outputs/new_source_probe_review_v1/current/probe_review_report.md
outputs/alpha360_strict_oos_extension_v1/current/alpha360_strict_oos_extension_report.md
outputs/alpha360_strict_oos_stability_v1/current/alpha360_strict_oos_stability_report.md
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_report.md
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_report.md
```

## Alpha101 来源审计与 adapter smoke

Alpha101 当前优先使用 KunQuant 作为公式来源。source audit 确认了 82 个可用公式；5 个 smoke 因子先通过验证后，完整 candidate batch 又 promotion 了 59 个，最终形成 64 个 promoted Alpha101 因子与 18 个 holdout：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha101_sources_v1.py --config configs\alpha101_source_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\alpha101_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_smoke_catalog_entries_v1.py --config configs\alpha101_factor_smoke_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha101_batch_catalogs_v1.py --config configs\alpha101_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_batch82_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha101_candidate71.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_batch_catalog_entries_v1.py --config configs\alpha101_factor_batch_promotion_v1.yaml
```

当前结果：

```text
KunQuant all_alpha entries: 82
Ginkgo runnable implementation files: 0
Alpha101 metadata catalog entries: 82
smoke selected factors: 5
batch adapter eligible factors: 76
adapter holdout: 6
V4 batch candidates: 71
batch promoted: 59
V4 batch holdout: 12
combined Alpha101 promoted catalog: 64
combined Alpha101 holdout catalog: 18
```

Alpha101 metadata catalog 默认仍保持 non-runnable。只有 promoted catalog 被标记为 enabled / runnable。Alpha101 promoted 因子在 screening contract 中仍放在 `monitor`；当前 judgement 层把其中 14 个标记为 `new_source_alpha_probe`，用于后续研究。

## 开源因子源扩张审计

写下一条 adapter 之前，先审计下一批因子/数据源：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_open_source_factor_expansion_v1.py --config configs\open_source_factor_expansion_audit_v1.yaml
```

当前结果：

```text
candidates: 8
direct_adapter_next: qlib_alpha360
data_audit_next: factortest_exposure_diagnostics
reference-only candidates: GPL 或 unknown-license 来源
```

这能保证后续扩张继续优先参考开源，但不把 license 或数据假设风险带入主项目。Qlib Alpha360 已完成直接 adapter 路径；FactorTest 风格的行业/风格暴露诊断应先做数据能力审计。

## Qlib Alpha360 Batch Promotion

Alpha360 已经完成 source audit、adapter smoke、V4 smoke、完整 358 因子 batch V4、promotion/holdout 与 multi-source 接入：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_catalog_v1.py --config configs\alpha360_catalog_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358_execution.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha360_batch_catalog_entries_v1.py --config configs\alpha360_factor_batch_promotion_v1.yaml
```

当前结果：

```text
Alpha360 formulas: 360
missing provider fields: 0
smoke catalog entries: 24
smoke frame rows: 88,797
batch candidates: 358
batch manifests: 72
metric index rows: 6,444
batch promoted: 358
adapter holdouts: 2
multi-source Alpha360 probes: 299
readiness alpha360 contracts: pass
```

Alpha360 V4 smoke 已完成，范围是 22 个非恒等 smoke 因子：

```text
Alphalens Reloaded: 22 pass
Qlib eval: 22 pass
jqfactor_analyzer: 22 partial_pass
open_source_metric_index rows: 396
context_metric_index rows: 4,224
```

jqfactor partial 会被记录，但不改开源评价口径。完整 Alpha360 batch V4 随后评估了 358 个非 holdout 因子：

```text
Alphalens Reloaded: 358 pass
Qlib eval: 358 pass
jqfactor_analyzer: 358 partial_pass
batch promoted: 358
V4 batch holdout: 0
adapter holdout: alpha360_CLOSE0, alpha360_VOLUME0
```

两个 adapter holdout 是 `alpha360_CLOSE0` 和 `alpha360_VOLUME0`。Promoted catalog 已 enabled/runnable，但 Alpha360 行在 judgement 后仍只是研究 probes；下一步需补相关性、暴露、稳定性、OOS 和组合 smoke 诊断。

关键输出：

```text
docs/_archive/05_open_source_factor_batches/ALPHA360_BATCH_PROMOTION_AND_MULTI_SOURCE_V1.md
outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml
outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/alpha360_candidate358_metric_index.csv
```

## 当前因子研究结论

截至 V3.1/V3.2：

- `amplitude_20` raw directional Rank IC 较强，但流动性、波动率和成交额代理联合中性化后大幅下降，更像风险/流动性暴露。
- `std_20` 与 `amplitude_20` 高度冗余，应优先作为风险暴露处理。
- `rev_5` 在成交额代理残差中性化后有所改善，但仍只是观察候选，不适合直接进入模型训练。
- 当前不应继续围绕少量常见因子做策略细调；应先让工具链 readiness 通过，再按开源来源大规模扩张因子池。

## 开源参考

本项目推进时会优先参考成熟开源项目，避免重复造轮子：

- `microsoft/qlib`：数据、模型工作流、横截面标准化思路。
- `alphalens-reloaded`：IC、Rank IC、ICIR、分组收益、换手率等评价口径。
- `JoinQuant/jqfactor_analyzer`：A 股单因子研究流程组织。
- `jltxzxy/FactorTest`：暴露相关性、中性化和分层诊断。
- `bukosabino/ta`：MIT license 的轻量技术指标参考，适合波动率、动量、成交量类公式。
- `Menooker/KunQuant`：Apache-2.0 表达式引擎参考，适合未来大批量因子性能优化研究。

相关文档：

```text
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_ALGORITHM_AUDIT.md
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_V3_REFERENCE_SURVEY.md
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_V3_1_PLAN.md
docs/_archive/03_factor_research_history/FACTOR_EXPANSION_V3_5_REFERENCE_SURVEY.md
```

## 开发约束

- 保持 Qlib baseline、data_quality、tradability、factor_research 解耦。
- 因子评价不能绕过 tradability 标签。
- 大体积临时输出和参考仓库放在 `tmp/`。
- Git 中尽量保留紧凑 summary、报告和关键验证结果。
- 在因子筛选工具链稳定前，不急着训练新模型或做实盘相关模块。
- Windows 下完整 qrun 使用本地普通权限运行，不要放在受限沙盒里。

## 关键文档

```text
docs/DOC_INDEX.md
docs/PROJECT_CONTEXT_SUMMARY.md
docs/SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md
docs/STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md
docs/FACTOR_RESEARCH_TOOLCHAIN_READINESS_V1.md
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1_PLAN.md
docs/ENVIRONMENT.md
docs/BASELINE_REPRODUCIBILITY.md
docs/DATA_SOURCE_DECISION.md
docs/UNIVERSE_POLICY.md
docs/TRADABILITY_LABEL_LAYER.md
docs/_archive/README.md
```
