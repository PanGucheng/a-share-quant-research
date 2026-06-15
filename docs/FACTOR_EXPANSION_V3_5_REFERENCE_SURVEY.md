# Factor Expansion V3.5 Reference Survey

本阶段目标是为下一批因子扩展选择可复用的开源来源。原则是：优先克隆和参考有明确 license、实现成熟、能和现有 Qlib/data_quality/tradability/factor_research 链路兼容的项目；不把大型外部框架直接并入主线。

## 1. Scope

当前候选池只有一个 alpha 候选：

```text
rev_5 -> alpha_candidate
```

V3.5 计划围绕反转、波动率、回撤、流动性稳定性和量价关系扩展一小批因子。扩展前先确认参考项目：

```text
downside_std_20
max_drawdown_20
rev_20_exclude_5
amount_cv_20
corr_ret_amount_20
```

## 2. Newly Cloned Reference Repositories

克隆目录：

```text
tmp/reference_repos
```

新增仓库：

| Repo | URL | Commit | License | Initial Decision |
| --- | --- | --- | --- | --- |
| `ta` | `https://github.com/bukosabino/ta.git` | `a890410` | MIT | Adopt as lightweight technical-indicator reference. |
| `KunQuant` | `https://github.com/Menooker/KunQuant.git` | `d4b9e61` | Apache-2.0 | Keep as future expression-engine/performance reference; do not integrate now. |
| `Ginkgo_Alpha101` | `https://github.com/Kaoruha/Ginkgo_Alpha101.git` | `57cec70` | MIT | Not useful now; repository has almost no factor implementation content. |

Existing local references:

| Repo | Commit | License File | Usage |
| --- | --- | --- | --- |
| `alphalens-reloaded` | `f0a07c2` | yes | Evaluation metrics and report style. |
| `jqfactor_analyzer` | `69e677d` | yes | A-share single-factor workflow and preprocessing organization. |
| `FactorTest` | `98cb0e0` | yes | Exposure correlation, neutralization, and slice diagnostics. |
| `qlib_factor_platform` | `9611ac2` | no clear local license | Module organization reference only. |
| `multi-factor` | `d86618d` | no clear local license | Formula/process reference only; no code copy. |
| `AlphaTrading` | `5e73923` | no clear local license | Workflow reference only; no code copy. |

## 3. Source Assessment

### 3.1 Microsoft Qlib

Local path:

```text
E:\qlib_prj\qlib_clone
```

Relevant files:

```text
qlib/contrib/data/loader.py
qlib/contrib/data/handler.py
```

Useful design points:

- Alpha158 uses Qlib expressions such as `Ref`, `Mean`, `Std`, `Max`, `Min`, `Corr`, `IdxMax`, and `IdxMin`.
- This is the best source for formulas that can be expressed directly on OHLCV panels.
- It matches the current data backbone and avoids adding a new dependency.

Decision:

```text
Use Qlib expressions and Alpha158 formulas as the primary formula reference.
Do not replace the current local DataFrame evaluator yet.
```

### 3.2 `bukosabino/ta`

License: MIT.

Relevant files:

```text
ta/volatility.py
ta/volume.py
ta/momentum.py
ta/trend.py
```

Useful implementation families:

- `AverageTrueRange`
- `BollingerBands`
- `DonchianChannel`
- `UlcerIndex`
- `VolumePriceTrendIndicator`
- `MoneyFlowIndex`
- `RSIIndicator`
- `ROCIndicator`

Decision:

```text
Use as the first external formula reference for technical indicators.
Prefer wrapping simple pure-pandas functions when a factor matches a ta implementation.
Avoid importing the whole package into the main project until dependency handling is explicit.
```

### 3.3 `Menooker/KunQuant`

License: Apache-2.0.

Useful design points:

- Expression optimizer/code generator for Alpha101/Alpha158-like formulas.
- Potential future speedup path if factor count grows substantially.

Decision:

```text
Do not integrate in V3.5.
Keep as future performance/reference candidate after the factor library is larger.
```

Reason:

- It introduces expression engine, generated code, and additional build/runtime complexity.
- Current bottleneck and project goal are not yet “hundreds of factors at high speed”.

### 3.4 `Kaoruha/Ginkgo_Alpha101`

License: MIT.

Finding:

- Repository currently contains README and license, but no useful factor implementation files.

Decision:

```text
Do not use for V3.5.
```

## 4. Mapping To Planned Factors

| Planned Factor | Preferred Reference | Implementation Strategy |
| --- | --- | --- |
| `downside_std_20` | Qlib `Std` style + downside return convention | Implement locally from daily return downside series. |
| `max_drawdown_20` | Qlib `Max/Min` rolling expressions + ta `UlcerIndex` drawdown family | Implement locally, cross-check with drawdown/ulcer style. |
| `rev_20_exclude_5` | Qlib `Ref` return expressions | Implement locally as medium reversal excluding recent 5 days. |
| `amount_cv_20` | Qlib `Mean/Std` volume features | Implement locally as amount std / amount mean. |
| `corr_ret_amount_20` | Qlib `Corr` Alpha158 style | Implement locally as rolling correlation between daily return and amount. |

## 5. Integration Decision

For V3.5:

1. Do not vendor external code into the repository.
2. Do not add a hard dependency on `ta` yet.
3. Implement the planned factors inside the existing `factor_research/factor_library.py`.
4. Record formula references and license decisions in this document.
5. Run expanded outputs separately:

```text
outputs/factor_research_v3/liquid2000_expanded
outputs/factor_screening_v3/liquid2000_expanded
outputs/factor_candidate_pool_v3/liquid2000_expanded
```

## 6. Next Implementation Step

Add the five planned factors to:

```text
factor_research/factor_library.py
factor_research/registry.py
```

Then run:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --factors amplitude_20,std_20,rev_5,ret_20,amount_mean_20,downside_std_20,max_drawdown_20,rev_20_exclude_5,amount_cv_20,corr_ret_amount_20 --output-dir outputs\factor_research_v3\liquid2000_expanded --refresh-factor-cache
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_screening_v3.py --input-dir outputs\factor_research_v3\liquid2000_expanded --output-dir outputs\factor_screening_v3\liquid2000_expanded
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_candidate_pool_v3.py --candidate-board outputs\factor_screening_v3\liquid2000_expanded\factor_candidate_board.csv --output-dir outputs\factor_candidate_pool_v3\liquid2000_expanded --pool-name liquid2000_expanded_v3_5
```
