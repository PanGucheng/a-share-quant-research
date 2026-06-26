# Alpha158 Stability Diagnostics V1

本文档是 V3.17 的具体计划与执行记录。它承接 V3.16 recent OOS diagnostics，只比较已有 main 与 recent OOS 输出，不重新计算因子，不训练模型，不做策略优化。

## 1. 目标

建立如下诊断：

```text
main diagnostics
recent OOS diagnostics
  -> single factor stability
  -> TopK sensitivity delta
  -> cost sensitivity delta
  -> liquidity bucket exposure delta
  -> stability report
```

核心问题：

- 哪些候选因子 main 和 recent OOS 都有正向表现。
- 哪些候选因子只在 main window 强。
- TopK/成本敏感性在 recent OOS 是否恶化。
- 持仓 liquidity bucket 分布是否明显变化。

## 2. 输入

```text
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/
outputs/alpha158_portfolio_diagnostics_v1/recent_oos_2024_2026/
```

## 3. 实现文件

```text
configs/alpha158_stability_diagnostics_v1.yaml
factor_research/alpha158_stability_diagnostics.py
scripts/run_alpha158_stability_diagnostics_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_stability_diagnostics_v1.py --config configs\alpha158_stability_diagnostics_v1.yaml
```

## 4. 输出

```text
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/
  alpha158_stability_diagnostics_report.md
  single_factor_stability.csv
  topk_sensitivity_delta.csv
  cost_sensitivity_delta.csv
  liquidity_bucket_exposure_delta.csv
```

## 5. 验收标准

- [x] 单因子稳定性表包含 14 行。
- [x] TopK 对比包含 50、100、200 三档。
- [x] 成本对比包含 5、10、20 bps 三档。
- [x] 流动性 bucket 对比包含 main/recent share 和差值。
- [x] Markdown 报告给出下一步建议。

## 6. 当前结果

稳定性标签：

```text
weak_or_negative_oos: 8
positive_but_weaker_oos: 3
main_only: 2
oos_improved: 1
```

相对稳定或值得继续观察的候选：

```text
alpha158_VSUMN60    oos_improved
alpha158_ROC60      positive_but_weaker_oos
alpha158_ROC30      positive_but_weaker_oos
alpha158_ROC10      positive_but_weaker_oos
```

明显 main-only 或 recent OOS 弱化的候选：

```text
alpha158_QTLD60     main_only
alpha158_QTLD30     main_only
8 factors           weak_or_negative_oos
```

TopK 100 对比：

```text
main net_excess_ir:   0.552843
recent net_excess_ir: 0.221295
delta:               -0.331548
```

流动性 bucket 暴露变化：

```text
bucket 3 share: +0.063357
bucket 4 share: -0.005643
bucket 5 share: -0.057714
```

结论：

- recent OOS 明显弱于 main window。
- 候选因子排序不稳定，不适合直接进入策略优化。
- recent OOS 持仓更偏 bucket 3，流动性暴露需要继续诊断。

## 7. 下一步

V3.17 完成后，若稳定性明显不足，下一阶段不应急着优化策略，而应先做：

- 因子候选分层：stable、oos_improved、main_only、weak_oos。
- 暴露诊断：流动性、价格动量、波动率、成交量代理。
- 低换手版本的 score smoothing 或持仓缓冲研究。
