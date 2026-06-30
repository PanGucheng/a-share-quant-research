# Factor Evaluation Source Manifest

This document records the first V3.6 source manifest for open-source factor
evaluation coexistence. The machine-readable source file is:

```text
factor_research/external/source_manifest.yaml
```

## Policy

- External metric systems should first coexist instead of being merged into a
  single project-defined score.
- The project may write data adapters, source manifests, reports, and judgement
  rules, but should not silently rewrite third-party metric definitions.
- Every reused evaluator must keep its project, commit, license, source files,
  function names, local adapter, and output namespace traceable.
- `data_quality` and `tradability` remain mandatory prefilters before external
  evaluation adapters are used.

## Registered Sources

| source | commit | license | V3.6 role |
| --- | --- | --- | --- |
| `alphalens-reloaded` | `f0a07c22d554e4b4036983cc80320b432714fe7e` | Apache-2.0 | Primary factor evaluation reference |
| `jqfactor_analyzer` | `69e677dc0dd9bed9fece02a70b9c81ce3d0afc53` | MIT | A-share style grouped/neutralized analysis reference |
| `Qlib evaluate` | `d5379c520f66a39953bad76234a7019a72796fd0` | MIT | Qlib-native evaluation compatibility |
| `qlib_factor_platform` | `9611ac2d1392761af5988e8a571f2075c61c601e` | MIT | Workflow and factor management design reference |
| `ta` | `a890410710a6e483c9ba08da7f3dd5089e4b9dff` | MIT | Later technical indicator factor source |
| `KunQuant` | `d4b9e61f729df347730aa921b539b9df3c3fe36d` | Apache-2.0 | Later Alpha101/Alpha158 formula reference |
| `Ginkgo_Alpha101` | `57cec7002698d89c130e027c7661bf53d307dcac` | MIT | Later Alpha101 formula reference |
| `FactorTest` | `98cb0e0310a50adc1ca1a34fdd89e18caa03381f` | MIT | Later A-share data/exposure reference |
| `multi-factor` | `d86618d8d62ca4d70a283957be6c64003c7bf2c6` | unknown | Pending license review |

## First Adapter Boundary

The first adapter module is:

```text
factor_research/external/adapters.py
```

It currently provides schema conversion only:

| adapter | output |
| --- | --- |
| `to_alphalens_factor_data` | Alphalens-style `(date, asset)` MultiIndex with `factor`, forward return period columns, optional `factor_quantile` and `group` |
| `to_jqfactor_inputs` | jqfactor-style aligned `factor`, `forward_returns`, optional `groupby`, optional `weights` |
| `to_qlib_score_frame` | Qlib-style `datetime`, `instrument`, `score`, `label` frame |

These functions do not compute IC, grouped returns, turnover, alpha/beta, risk
metrics, or any screening score. Those calculations must be called from the
registered source systems in the next implementation step.

## Next Implementation Step

The next step is to build a small runner that:

1. loads a tradability-filtered internal factor data sample,
2. exports Alphalens/jqfactor/Qlib-compatible inputs for a small factor set,
3. writes adapter reports and samples under `outputs/factor_evaluation_v4/`,
4. records failure reasons instead of stopping the whole batch.

