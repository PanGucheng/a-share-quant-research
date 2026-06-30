# Factor Expansion V3.5 Implementation

本阶段在 V3.5 开源参考调研基础上，新增 5 个小批量因子，并完整跑通：

```text
factor_research -> factor_screening -> factor_candidate_pool
```

## 1. Added Factors

| Factor | Category | Expected Direction | Formula Summary | Reference |
| --- | --- | --- | --- | --- |
| `downside_std_20` | risk | negative | 20-day rolling std of downside daily returns. | Qlib `Std` style, downside-risk convention. |
| `max_drawdown_20` | risk | negative | 20-day rolling maximum peak-to-trough drawdown. | Qlib rolling `Max/Min`, `ta` drawdown/ulcer family. |
| `rev_20_exclude_5` | reversal | positive | Negative return from t-20 to t-5, excluding recent 5 trading days. | Qlib `Ref` return expressions. |
| `amount_cv_20` | liquidity | negative | 20-day amount std / 20-day amount mean. | Qlib `Std/Mean` style. |
| `corr_ret_amount_20` | price_volume | watch | 20-day rolling correlation between daily return and amount. | Qlib `Corr` Alpha158 style. |

Implementation files:

```text
factor_research/factor_library.py
factor_research/registry.py
scripts/run_factor_research_v3.py
factor_research/screening_v3.py
factor_research/candidate_pool_v3.py
```

`BASIC_FACTOR_VERSION` was bumped to `2` so cached basic-factor frames cannot silently reuse stale columns.

## 2. Commands

Expanded factor research:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --factors amplitude_20,std_20,rev_5,ret_20,amount_mean_20,downside_std_20,max_drawdown_20,rev_20_exclude_5,amount_cv_20,corr_ret_amount_20 --output-dir outputs\factor_research_v3\liquid2000_expanded --refresh-factor-cache
```

Expanded screening:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_screening_v3.py --input-dir outputs\factor_research_v3\liquid2000_expanded --output-dir outputs\factor_screening_v3\liquid2000_expanded
```

Expanded candidate pool:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_candidate_pool_v3.py --candidate-board outputs\factor_screening_v3\liquid2000_expanded\factor_candidate_board.csv --output-dir outputs\factor_candidate_pool_v3\liquid2000_expanded --pool-name liquid2000_expanded_v3_5
```

## 3. Outputs

```text
outputs/factor_research_v3/liquid2000_expanded
outputs/factor_screening_v3/liquid2000_expanded
outputs/factor_candidate_pool_v3/liquid2000_expanded
```

## 4. Expanded Candidate Pool

Current roles:

```text
rev_20_exclude_5 -> alpha_candidate
rev_5            -> alpha_candidate
amplitude_20     -> risk_control
std_20           -> risk_control
downside_std_20  -> risk_control
max_drawdown_20  -> monitor
amount_cv_20     -> monitor
ret_20           -> monitor
amount_mean_20   -> monitor
corr_ret_amount_20 -> monitor
```

## 5. Key Findings

- `rev_20_exclude_5` is the strongest new alpha candidate:
  - main directional Rank IC: about `0.0538`
  - OOS directional Rank IC: about `0.0590`
  - residual retention: about `0.1786`
- `rev_5` remains an alpha candidate:
  - main directional Rank IC: about `0.0196`
  - OOS directional Rank IC: about `0.0352`
  - residual retention: about `0.9374`
- `downside_std_20` has strong raw signal but is exposure-dominated:
  - main directional Rank IC: about `0.0652`
  - dominant exposure: `std_20`
  - status: `risk_exposure`
- `max_drawdown_20` has raw/OOS signal but flips after controls:
  - main directional Rank IC: about `0.0307`
  - OOS directional Rank IC: about `0.0253`
  - residual retention: about `-1.1317`
  - status: `watch`
- `amount_cv_20` has positive OOS but insufficient evidence under current rules.

## 6. Screening Rule Fix

During V3.5, `max_drawdown_20` exposed a rule weakness: a factor could become `research_candidate` even if the joint residual signal flipped negative. This was fixed in:

```text
factor_research/screening_v3.py
```

New behavior:

```text
joint_residual_directional_rank_ic < 0 -> watch / signal_flips_after_controls
```

This prevents raw risk-like signals from entering the alpha candidate pool when neutralized signal is negative.

## 7. Next Step

The next natural step is not to add many more factors immediately. Recommended follow-up:

1. Build a small portfolio-test scaffold that reads `factor_candidate_pool.csv`.
2. Test `rev_20_exclude_5` and `rev_5` as alpha candidates.
3. Use `amplitude_20`, `std_20`, and `downside_std_20` as risk controls or exposure diagnostics.
4. Keep `max_drawdown_20` and `amount_cv_20` in monitor until better definitions are tested.
