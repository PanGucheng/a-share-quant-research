# Qlib A 股量化研究基线项目

本项目是一个围绕 [Microsoft Qlib](https://github.com/microsoft/qlib) 搭建的
A 股量化研究工程。它最初用于复现官方 LightGBM + Alpha158 baseline，现在正在扩展为一个适合量化新手逐步学习和实践的研究框架：先保证数据、可交易性和因子评价可靠，再考虑模型、组合和回测。

> 本项目仅用于研究和学习，不构成投资建议，也不包含实盘交易代码。

## 当前方向

项目坚持一个原则：不替换 Qlib 主线，而是在 Qlib 外围补齐研究工程能力。

当前主线包括：

- **Qlib baseline**：已验证官方 LightGBM + Alpha158 工作流可以跑通。
- **数据质量诊断**：检查缺失值、价格成交异常、生命周期问题和逐行数据问题。
- **可交易性标签层**：把流动性、数据质量和交易约束转成统一标签。
- **因子研究模块**：在数据质量和可交易性过滤之后，评价 IC、Rank IC、ICIR、分组收益、换手率、覆盖率、缺失率、相关性、单调性、切片稳定性和中性化效果。
- **因子筛选模块**：把因子研究输出转成可解释的候选看板，再交给后续组合测试。
- **后续组合回测模块**：规划中，未来会消费筛选后的因子候选，而不是直接绕过研究层做策略。

当前优先级是继续完善因子研究与因子筛选工具链，暂时不急着训练新模型或调具体策略参数。

## 目录结构

```text
configs/          Qlib qrun 工作流配置。
data_quality/     数据质量诊断模块。
tradability/      可交易性标签构建与报告。
factor_research/  因子评价、预处理、中性化和报告模块。
scripts/          可复现运行脚本和汇总脚本。
docs/             开发计划、算法审计、开源参考调研和设计文档。
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

该模块直接读取现有 Qlib provider 的成分区间和基准特征，只为因子评价补充上下文，不绕过既有数据质量检查与可交易性前置过滤。时点规则和上市日期代理限制见 `docs/FACTOR_CONTEXT_V1.md`。

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
docs/FACTOR_BATCH_EVALUATION_V1.md
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
new_source_adapter_inventory: blocked
generic_multi_source_screening: partial
```

这说明 Alpha158 研究链路已经可复现，第一个非 Alpha158 adapter 也已进入 smoke 阶段；但多来源大规模因子研究还不能直接开跑。下一步应先提升更多 TA 因子，再接 Alpha101 公式源，并统一多来源 screening / candidate pool 契约。

关键输出：

```text
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
```

## TA 因子 adapter smoke

第一个非 Alpha158 开源因子源已经以 smoke 级别接入：`bukosabino/ta`。

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_ta_factor_adapter_smoke_v1.py --config configs\ta_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\ta_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_smoke_catalog_entries_v1.py --config configs\ta_factor_smoke_promotion_v1.yaml
```

当前 TA smoke 结果：

```text
eligible TA factors: 79
excluded TA columns: 7
V4 smoke factors: 5
promoted smoke factors: 5
readiness new_source_runnable: 5
```

这已经证明新源 adapter 路径能跑通，但还不足以直接开始 TA 全量筛选。下一步应为剩余 eligible TA 因子建立可恢复的 batch 计划。

TA remaining batch dry-run：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_ta_batch_catalogs_v1.py --config configs\ta_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_ta_remaining74.yaml --dry-run
```

当前 batch 计划：

```text
remaining TA factors: 74
planned batches: 15
batch size: 5
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
docs/FACTOR_RESEARCH_ALGORITHM_AUDIT.md
docs/FACTOR_RESEARCH_V3_REFERENCE_SURVEY.md
docs/FACTOR_RESEARCH_V3_1_PLAN.md
docs/FACTOR_EXPANSION_V3_5_REFERENCE_SURVEY.md
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
docs/DEVELOPMENT_PLAN.md
docs/ENVIRONMENT.md
docs/BASELINE_REPRODUCIBILITY.md
docs/TRADABILITY_LABEL_LAYER.md
docs/PROVIDER_DATA_CAPABILITY_V3_6.md
docs/FACTOR_CONTEXT_V1.md
docs/FACTOR_BATCH_EVALUATION_V1.md
docs/ALPHA158_CATALOG_AUDIT_V1.md
docs/ALPHA158_EXPRESSION_EVALUATION_STAGE_PLAN.md
docs/ALPHA158_EXPRESSION_ADAPTER_V1.md
docs/ALPHA158_FULL_EVALUATION_STAGE_PLAN.md
docs/ALPHA158_FULL_SCREENING_INPUT_V1.md
docs/ALPHA158_JUDGEMENT_LAYER_V1.md
docs/ALPHA158_CANDIDATE_POOL_V1.md
docs/ALPHA158_CANDIDATE_PORTFOLIO_SMOKE_V1.md
docs/ALPHA158_PORTFOLIO_DIAGNOSTICS_V1.md
docs/ALPHA158_RECENT_OOS_EXTENSION_V1.md
docs/ALPHA158_STABILITY_DIAGNOSTICS_V1.md
docs/FACTOR_RESEARCH_TOOLCHAIN_READINESS_V1.md
docs/TA_FACTOR_ADAPTER_SMOKE_V1.md
docs/TA_BATCH_EVALUATION_PLAN_V1.md
docs/STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md
docs/PROJECT_CONTEXT_SUMMARY.md
```
