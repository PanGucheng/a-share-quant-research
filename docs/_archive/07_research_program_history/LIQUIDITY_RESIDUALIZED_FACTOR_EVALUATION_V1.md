# Liquidity Residualized Factor Evaluation V1

> ARCHIVED / CLOSED：该历史评估已结束，不是当前模型或因子入口。

V3.39 – Residualized evaluation of 19 tradability-exposed probes.

## Status

Implemented and operational. Runs on 19 watchlist factors from `tradability_exposure_attribution_v1`.
Uses existing tradability labels and factor frames; does **not** train models, modify
evaluator definitions, or change downstream defaults.

**Current contract status**: `residualized_coverage_min` is blocked by coverage (see Contract
section below). The pipeline runs correctly; the blockage is a data-scope limitation — TA
pipeline factors have limited instrument overlap with the tradability-label universe.

## What it does

1. Reads the 19 watchlist factors from the tradability exposure attribution board.
2. Loads TA and Alpha101 factor frames and merges them on `(datetime, instrument)`.
3. Attaches unified tradability labels (`liquidity_value`, `liquidity_bucket`, `tradability_score`).
   Proxies that are constant on a given trading day (e.g. `tradability_score` is uniformly 80)
   are automatically dropped from that day's regression; the residualization proceeds with the
   remaining non-constant proxies.
4. For each trading day and factor, performs a cross-sectional OLS residualization:

```
factor_z = intercept + liquidity_value_z + liquidity_bucket_z + tradability_score_z + residual
```

   The factor and each proxy are winsorized (MAD 4.5σ) and robust-zscored (clip ±3) before regression.

5. Writes ``<factor>__resid_liquidity`` columns into the residualized factor frame.
   Raw columns are **never** overwritten.

6. Computes per-day diagnostics (coverage, R², raw–residual correlation).

7. If forward-return labels are available, computes \(IC\) and \(Rank IC\) for both raw
   and residualized versions and compares them.  Otherwise the comparison table uses
   residualization diagnostics (coverage, \(R^2\)) — it still contains **real** computed
   numbers, never dummy rows.

8. Assigns a candidate action to each factor×label pair:

   - `residual_signal_survives` — residualized Rank IC remains positive with retention > 0.30.
   - `liquidity_proxy_confirmed` — raw signal is significant but residualized is weak or sign-flipped.
   - `holdout` — no stable residual signal; hold back from training.
   - `needs_manual_review` — coverage too low or insufficient data.

9. Produces a contract-status CSV with ≥ 8 checks.

## Input

| artefact | path |
| --- | --- |
| Attribution board | `outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_board.csv` |
| TA factor frame | `outputs/ta_factor_adapter_v1/smoke/factor_frame.pkl` |
| Alpha101 factor frame | `outputs/alpha101_factor_adapter_v1/batch82/factor_frame.pkl` |
| Tradability labels | `outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv` |
| Feature cache (optional) | `tmp/factor_feature_cache/` |

## Output

```
outputs/liquidity_residualized_factor_evaluation_v1/current/
├── residualized_factor_frame.pkl              # large, local cache only
├── residualized_factor_summary.csv            # per-factor coverage
├── daily_residualization_diagnostics.csv       # per-day × per-factor diagnostics
├── raw_vs_residualized_metric_comparison.csv   # IC or diagnostic comparison
├── residualized_candidate_actions.csv          # decision per factor
├── liquidity_residualized_contract_status.csv  # ≥ 8 checks
└── liquidity_residualized_factor_evaluation_report.md
```

## Contract

| check | minimum |
| --- | --- |
| watchlist_rows | ≥ 19 |
| residualized_factor_count | ≥ 19 |
| residualized_coverage_min | ≥ 0.80 |
| daily_diagnostics_rows | > 0 |
| raw_vs_residualized_metric_rows | > 0 |
| contract_status_rows | ≥ 8 |
| downstream_default_included | = 0 |
| residualized_factor_frame_produced | ≥ 19 |

## Run

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_liquidity_residualized_factor_evaluation_v1.py --config configs\liquidity_residualized_factor_evaluation_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_liquidity_residualized_factor_evaluation_v1.py --config configs\liquidity_residualized_factor_evaluation_v1.yaml
```

## Validate

The lightweight validation script uses synthetic data and does not require Qlib data:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\validate_liquidity_residualized_factor_evaluation_v1.py
```

It covers constant-proxy handling, all-NaN guard cases, unsorted-row alignment, R^2 scale, and `liquidity_value` merge behavior.

## Residualization details

- **Method**: daily cross-sectional OLS via `numpy.linalg.lstsq`.
- **Normalization**: MAD winsorization (4.5σ) followed by robust z-score (median / MAD×1.4826), clipped to ±3.
- **Proxies**: `liquidity_value`, `liquidity_bucket`, `tradability_score`.  Any proxy that
  is constant (zero cross-sectional variance) on a given day is auto-excluded from that day's
  regression; the configured set represents the maximum, not the guarantee.
  `liquidity_bucket` is treated as an ordinal numeric regressor (its integer bucket rank
  is used directly in the OLS design matrix without one-hot encoding).
- **Suffix**: `__resid_liquidity` (never overwrites raw).
- **Min observations**: 50 valid rows per day for OLS.

## Boundary

- No model training.
- No strategy or portfolio optimization.
- No downstream defaults include residualized factors.
- No changes to existing evaluator definitions (Alphalens Reloaded, jqfactor_analyzer, Qlib eval).
- No modification of tradability labels or data quality outputs.

## Next steps

After V3.39:

1. For factors marked `residual_signal_survives`, run a recent-OOS residualized evaluation.
2. Design an external industry / market-cap data access contract.
3. When industry / market-cap data is ready, implement FactorTest-style industry/size neutralized evaluation.
4. Continue expanding the factor registry with new open-source sources, using the established gate pipeline.
