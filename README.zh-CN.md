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

注意：Alpha158 条目当前仍是 `runnable: false`，只作为已审计 metadata 来源。后续需要先完成 Qlib expression adapter，再进入正式 V4 因子评价。

## 当前因子研究结论

截至 V3.1/V3.2：

- `amplitude_20` raw directional Rank IC 较强，但流动性、波动率和成交额代理联合中性化后大幅下降，更像风险/流动性暴露。
- `std_20` 与 `amplitude_20` 高度冗余，应优先作为风险暴露处理。
- `rev_5` 在成交额代理残差中性化后有所改善，但仍只是观察候选，不适合直接进入模型训练。
- 当前更应该优化因子研究工具链，而不是马上引入大量新因子或训练新模型。

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
docs/STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md
docs/PROJECT_CONTEXT_SUMMARY.md
```
