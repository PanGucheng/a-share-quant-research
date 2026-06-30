# Alpha158 Full Screening Input V1

本文档记录 Alpha158 全量评价完成后的下一步：把 first20 与 remaining138 的开源评价结果、context 结果、表达式覆盖率和相关性诊断合并成一个可复现的筛选输入层。

本阶段仍然只服务于因子研究与因子筛选工具链：

- 不训练新模型。
- 不调整具体策略参数。
- 不生成自研综合分。
- 不替换 Alphalens Reloaded、jqfactor_analyzer 或 Qlib eval 的评价口径。
- 不绕过已有 data_quality、tradability 和 factor context 约束。

## 1. 输入关系

```text
Qlib Alpha158 source audit
  -> expression adapter / expression frame validation
  -> first20 V4 evaluation
  -> remaining138 batch evaluation
  -> strict runnable / holdout catalog
  -> Alpha158 full screening input
```

本阶段读取以下已存在结果：

```text
outputs/factor_evaluation_v4/alpha158_first20_smoke/
outputs/factor_evaluation_batch_v1/alpha158_remaining138/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_all.yaml
outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml
outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_holdout.yaml
outputs/factor_catalog_alpha158_v1/alpha158_remaining138_promotion_audit.csv
outputs/alpha158_expression_frame_v1/full158_main_research/
```

其中 context 输出来自既有 factor context/tradability-aware 评价链路，因此 full Alpha158 筛选输入不会绕过可交易性约束。

## 2. 实现文件

```text
configs/factor_screening_alpha158_full_v1.yaml
factor_research/alpha158_screening_input.py
scripts/run_alpha158_screening_input_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_screening_input_v1.py --config configs\factor_screening_alpha158_full_v1.yaml
```

## 3. 评价体系保留方式

本阶段将多个开源评价体系并列保留：

- `alphalens_reloaded`：Rank IC、ICIR、分组收益、换手率、rank autocorrelation。
- `jqfactor_analyzer`：Rank IC、ICIR、分组收益、换手率。
- `qlib_eval`：daily rank IC、ICIR、risk analysis。
- `context`：按 index segment 等上下文分组后的 IC 和分组收益。

说明：

- Alphalens 的 `factor_information_coefficient` 使用 Spearman rank correlation，本阶段作为 Rank IC 使用。
- ICIR 由对应评价体系输出的 IC 日序列计算，公式为均值除以样本标准差。
- jqfactor_analyzer 当前在 pandas 2.x 环境下仍有已知 `factor_returns` / `factor_alpha_beta` partial-pass，本阶段保留其 partial-pass 状态，不改写为 pass。
- 不把上述指标合成为单一分数。

## 4. 新增诊断维度

除合并原始 metric index 外，本阶段新增以下 compact 诊断：

- 覆盖率和缺失率：来自 full158 expression frame validation。
- Rank IC / ICIR / win rate：来自各评价体系的 IC 日序列。
- 分组收益与单调性：从 `mean_return_by_quantile.csv` 计算 top-bottom spread 和 quantile Spearman monotonicity。
- 换手率：从 `quantile_turnover.csv` 计算均值、中位数和有效样本数。
- rank autocorrelation：从 Alphalens 输出中计算均值、中位数和有效样本数。
- context 分组稳定性：保留 index segment 等分组下的 IC 和分组收益。
- 因子相关性：读取已验证的 full158 expression frame，按每日横截面 Spearman 相关取均值，输出最强相关因子和 Top pairs。

相关性配置：

```yaml
correlation:
  enabled: true
  method: "daily_cross_section_spearman_mean"
  max_dates: 120
  min_instruments: 100
  top_pairs: 100
```

## 5. 当前运行结果

输出目录：

```text
outputs/factor_screening_alpha158_v1/full158/
```

关键结果：

```text
factor board rows: 158
strict_screening_input: 155
holdout: 3
metric index rows: 33,148
IC summary rows: 948
quantile return summary rows: 632
turnover summary rows: 624
rank autocorrelation summary rows: 474
context IC summary rows: 1,264
context return summary rows: 5,056
correlation used dates: 120
```

Holdout 仍然是以下 3 个因子：

```text
alpha158_CNTN5
alpha158_IMAX5
alpha158_RANK5
```

原因：Alphalens Reloaded 的 `quantile_turnover` 对这 3 个因子缺少有效数值，因此它们保留在 holdout，不进入 strict screening input。

## 6. 输出文件

```text
alpha158_full_metric_index.csv
alpha158_factor_screening_input.csv
alpha158_ic_timeseries_summary.csv
alpha158_quantile_return_summary.csv
alpha158_turnover_summary.csv
alpha158_rank_autocorrelation_summary.csv
alpha158_context_group_ic_summary.csv
alpha158_context_group_return_summary.csv
alpha158_factor_correlation_summary.csv
alpha158_factor_correlation_top_pairs.csv
alpha158_factor_correlation_meta.csv
alpha158_full_screening_input_report.md
```

最重要的下游入口是：

```text
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_screening_input.csv
```

它是后续因子筛选 judgement layer、候选池冻结、组合回测接口的输入，不是交易信号。

## 7. 下一步

下一阶段仍然不急着训练模型。更合理的顺序是：

1. 基于 `alpha158_factor_screening_input.csv` 建立 judgement layer，但只引用原始评价指标，不覆盖开源结果。
2. 先输出候选分层：strong signal、redundant、unstable、high turnover、holdout、review。
3. 把强相关因子簇做成可读的 redundancy cluster，避免后续大量重复因子污染训练集。
4. 在筛选层稳定后，再启动 `ta` 技术指标和 Alpha101 来源审计与批量接入。

执行状态：

```text
V3.12 Alpha158 Judgement Layer 已完成。
详见 docs/ALPHA158_JUDGEMENT_LAYER_V1.md
```
