# Factor Research V3.1 Plan

本计划承接 V3 最小实现。核心原则是：推进项目前先查开源参考，尽量复用成熟项目的指标口径和模块边界，避免重复造轮子；实现时保持本项目的 Qlib baseline、data_quality、tradability 主线不被替换。

## 1. Current State

V3 已完成：

- 本地 DataFrame 版预处理：MAD 去极值、横截面 z-score/rank、残差中性化。
- 年份、流动性桶、波动率桶、市场状态切片。
- 轻量中性化：流动性桶、波动率桶、成交额代理、联合残差中性化。
- 输出 `factor_neutralized_summary.csv`、`factor_exposure_correlation.csv`、`factor_candidate_changelog.csv` 等诊断文件。

V3 关键发现：

- `amplitude_20` raw directional Rank IC 较强，但联合中性化后几乎消失。
- `amplitude_20` 与 `std_20` 高度相关，仍应视为风险/风格暴露，而不是干净 alpha。
- `rev_5` 在成交额代理残差中性化后有所改善，但仍不足以直接 promote。

## 2. Reference-First Rule

后续每次新增因子研究能力，先检查并记录至少一个参考来源：

- `alphalens-reloaded`: IC、Rank IC、分组收益、换手率、factor data 口径。
- `jqfactor_analyzer`: A 股单因子分析、预处理、中性化接口、tear-sheet 指标组织。
- `FactorTest`: Barra/暴露相关性、双重排序、分组 IC。
- `multi-factor`: MAD 去极值、z-score、行业/市值残差中性化流程。
- `microsoft/qlib`: 横截面标准化、模型 score 分组收益、Qlib 原生 report 口径。

不直接复制无 license 或强平台绑定项目代码，只借鉴算法思想和输出结构。

## 3. V3.1 Goals

### 3.1 Directional ICIR

问题：

- 当前负向因子的 `directional_mean_rank_ic` 已转为正向解释，但 `rank_icir` 仍保留原始符号，容易误读。

目标：

- 在 factor summary 中新增 `directional_rank_icir`。
- 报告优先展示 `directional_mean_rank_ic` 和 `directional_rank_icir`。

### 3.2 No-Lookahead Market State

问题：

- V3 的 `market_state` 使用未来 label 均值切分，只适合作为诊断，不适合作为后续可用条件。

目标：

- 改为基于过去可观测信息：
  - 股票池等权日收益。
  - 过去 20 日等权累计收益。
  - 过去 20 日等权波动率。
- 输出 `up`、`down`、`sideways`。

### 3.3 Output Size Control

问题：

- V3 默认输出明细文件较大，例如 `factor_slice_group_return.csv`。

目标：

- 增加 `--write-detail`。
- 默认只写 summary/report/changelog/correlation/exposure。
- 明细文件只在显式指定 `--write-detail` 时写出。

### 3.4 Exposure Explanation Report

目标：

- 新增 `factor_exposure_report.md`。
- 用更直接的语言解释：
  - 因子是否主要像波动率暴露。
  - 是否像流动性/成交额暴露。
  - 是否与已有核心因子高度冗余。
  - 中性化后是否仍保留有效性。

## 4. Implementation Order

1. 更新 `factor_research/diagnostics.py`，新增 `directional_rank_icir`。
2. 更新 `factor_research/slices.py`，将 `market_state` 改为过去 20 日可观测市场状态。
3. 更新 `scripts/run_factor_research_v3.py`：
   - 报告展示 `directional_rank_icir`。
   - 增加 `--write-detail`。
   - 默认删除或跳过明细输出，避免旧文件误导。
   - 生成 `factor_exposure_report.md`。
4. 跑 smoke test。
5. 跑默认 V3.1。
6. 更新第五步总计划文档并提交推送。

## 5. Acceptance Criteria

- [x] `factor_neutralized_summary.csv` 包含 `directional_rank_icir`。
- [x] `market_state` 不依赖未来 label。
- [x] 默认 V3.1 输出不再写大体积明细 CSV。
- [x] `factor_exposure_report.md` 能清楚解释 `amplitude_20`、`std_20`、`rev_5` 的暴露属性。
- [x] 通过 smoke test 和默认运行。

## 6. Execution Result

完成时间：2026-06-13。

验证命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe -m py_compile factor_research\diagnostics.py factor_research\slices.py scripts\run_factor_research_v3.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --window smoke_2021_jan,2021-01-01,2021-01-31,outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29,outputs/data_quality_tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29 --labels label_20d_t1 --factors amplitude_20,rev_5 --output-dir tmp\factor_research_v3_1_smoke --min-count 20
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --output-dir outputs\factor_research_v3\liquid2000_core
```

正式输出：

```text
outputs/factor_research_v3/liquid2000_core/factor_exposure_report.md
outputs/factor_research_v3/liquid2000_core/factor_neutralized_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_ic.csv
```

关键结论延续 V3 判断：

- `amplitude_20` raw directional Rank IC 仍较强，但联合中性化后降至约 `0.005`，更像波动率/流动性暴露。
- `std_20` 与 `amplitude_20` 高度冗余，仍应作为风险暴露处理。
- `rev_5` 在成交额代理残差中性化后改善，但仍属于观察候选，不应直接进入模型训练。
