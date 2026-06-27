# Open Source Factor Expansion Audit V1

本文档记录 V3.27：在 Alpha158、TA、Alpha101 和 multi-source judgement 已经跑通后，开始系统选择下一批开源因子/数据源。本阶段只做来源审计和最小输出，不训练模型、不调策略、不复制 GPL 或 unknown-license 代码。

## 定位

当前工具链已经可以承接更多因子：

```text
total runnable factors: 311
new-source runnable factors: 141
multi-source judgement board rows: 319
new-source alpha probes: 29
```

下一步不应继续研究单个常见因子，而是先回答：

- 哪些开源项目适合直接接入 adapter？
- 哪些项目只适合作为算法/数据结构参考？
- 哪些来源需要先做数据能力审计，例如基本面、行业、Barra/风格暴露？
- 哪些 license 或数据假设会阻塞直接复用？

## 输入

```text
configs/open_source_factor_expansion_audit_v1.yaml
tmp/reference_repos/
E:/qlib_prj/qlib_clone
```

本阶段额外拉取到 `tmp/reference_repos/` 的参考仓库：

```text
GetAstockFactors
ChinaAShareEquityCharacteristics
techfactor
```

这些仓库仍然被 `.gitignore` 忽略，只作为本地参考，不进入项目代码。

## 配置与脚本

```text
configs/open_source_factor_expansion_audit_v1.yaml
scripts/audit_open_source_factor_expansion_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_open_source_factor_expansion_v1.py --config configs\open_source_factor_expansion_audit_v1.yaml
```

## 候选来源

V1 候选分为三类：

```text
direct_adapter_next:
  - qlib_alpha360

data_audit_next:
  - factortest_exposure_diagnostics

reference_only:
  - get_astock_factors
  - china_ashare_equity_characteristics
  - multi_factor_fundamental_formulas
  - techfactor_gtja191
  - parsnip77_multi_factor_model
  - alphatrading_notebook_workflow
```

## 输出

```text
outputs/open_source_factor_expansion_audit_v1/current/open_source_factor_source_candidates.csv
outputs/open_source_factor_expansion_audit_v1/current/open_source_factor_expansion_next_steps.csv
outputs/open_source_factor_expansion_audit_v1/current/open_source_factor_expansion_manifest.json
outputs/open_source_factor_expansion_audit_v1/current/open_source_factor_expansion_report.md
```

## 当前结果

```text
candidates: 8
direct_adapter_next: 1
data_audit_next: 1
reference_only_due_gpl: 2
reference_only_until_license_review: 4
top candidate: qlib_alpha360
second candidate: factortest_exposure_diagnostics
```

排序结论：

```text
qlib_alpha360: score 12, direct_adapter_next, MIT, high data fit, low adapter complexity
factortest_exposure_diagnostics: score 9, data_audit_next, MIT, medium data fit, medium adapter complexity
get_astock_factors: score 5, reference only until license review
techfactor_gtja191: score 4, reference only due GPL
alphatrading_notebook_workflow: score 3, reference only until license review
multi_factor_fundamental_formulas: score 1, reference only until license/data review
parsnip77_multi_factor_model: score 1, remote reference only until license review
china_ashare_equity_characteristics: score 0, reference only due GPL and data requirements
```

## 预期下一步

V3.27 的预期结论不是“马上训练模型”，而是确定后续顺序：

1. 优先为 `qlib_alpha360` 制定 adapter smoke / batch 计划，因为它 license 兼容、数据适配度高、能复用当前 Qlib OHLCV/amount provider。
2. 同步为 `factortest_exposure_diagnostics` 制定数据能力审计计划，因为它能补齐行业/风格/Barra 暴露诊断，但需要确认本项目 provider 是否已有足够字段。
3. GPL 或 unknown-license 项目只保留来源、字段、公式、评价思想，不直接复制实现。
