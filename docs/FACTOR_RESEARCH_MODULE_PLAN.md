# Factor Research Module Plan

This document defines the local factor research module boundary. The module borrows organization ideas from `qlib_factor_platform` and metric ideas from Alphalens / alphalens-reloaded, but it remains a small command-line research core inside this repository.

## Scope

The module does:

- Build a reproducible factor evaluation dataset from Qlib data.
- Reuse existing `data_quality` and `tradability` outputs before factor evaluation.
- Evaluate factors with IC, Rank IC, ICIR, group returns, turnover, coverage, missing rate, correlation, and monotonicity.
- Produce CSV and Markdown reports for factor screening.
- Maintain a candidate pool for downstream model or portfolio experiments.

The module does not:

- Replace the existing Qlib baseline workflow.
- Train new models.
- Run live trading.
- Introduce a UI.
- Refactor unrelated data, model, or portfolio modules.

## Borrowed Design

From `qlib_factor_platform`, this project borrows the separation between factor registry, factor computation, factor analysis, workflow runner, and reports. The current project does not borrow the Streamlit UI or full platform layout.

From Alphalens / alphalens-reloaded, this project borrows the evaluation vocabulary:

- factor data schema
- forward-return labels
- quantile group returns
- IC and Rank IC
- ICIR
- turnover
- factor correlation
- tear-sheet-like summary reports

The implementation remains CSV/Markdown based so it is easy to inspect and version.

## Relationship To Existing Modules

```text
Qlib provider
  -> data_quality
  -> tradability
  -> factor_research
  -> candidate factor pool
  -> later model / portfolio modules
```

`Qlib baseline` remains the benchmark and experiment anchor. `factor_research` reads Qlib data but does not change baseline configs.

`data_quality` detects field missingness, price anomalies, volume anomalies, gaps, and row-level issues. `factor_research` must consume these outputs when available.

`tradability` converts data quality and market constraints into tradability labels. `factor_research` must apply `can_buy`, `liquidity_bucket`, `tradability_score`, and data quality status before evaluating the `tradable_only` sample.

Portfolio modules should consume the candidate pool after a factor passes research screening. A `promote` decision is not a live-trading signal.

## Factor Data Contract

The internal evaluator uses a wide daily cross-sectional frame for speed. Its public contract follows an Alphalens-style long schema:

```text
datetime
instrument
factor
factor_value
factor_quantile
label
forward_return
can_buy
can_sell
liquidity_bucket
tradability_score
data_quality_status
has_data_quality_issue
```

The schema is written to each run directory as:

```text
factor_data_schema.md
factor_data_sample.csv
```

## Default Evaluation Metrics

Core outputs:

```text
factor_summary.csv
factor_missing_coverage.csv
factor_group_monotonicity.csv
factor_bucket_ic.csv
factor_turnover.csv
factor_turnover_summary.csv
factor_correlation.csv
factor_candidate_decision.csv
factor_research_v2_report.md
```

Metrics:

- `coverage`: valid factor and label rows divided by total rows.
- `missing_rate`: one minus coverage.
- `mean_ic`: average daily Pearson IC.
- `mean_rank_ic`: average daily Spearman Rank IC.
- `icir` and `rank_icir`: mean IC divided by IC standard deviation.
- `ic_win_rate`: share of daily Rank IC observations with the expected sign.
- `directional_mean_rank_ic`: Rank IC adjusted by expected direction.
- `directional_spread`: top-minus-bottom group return adjusted by expected direction.
- `monotonicity_score`: Spearman relation between quantile number and group return, adjusted by expected direction.
- `mean_top_quantile_turnover`: average replacement ratio of the top quantile.
- `spearman_corr`: factor-to-factor rank correlation.

## Default Tradability Filter

```text
can_buy == true
liquidity_bucket >= 3
tradability_score >= 75
data_quality_status not in ["severe"]
has_core_missing != true
```

If a window is configured as `tradable_only`, missing tradability labels should fail loudly. Raw historical reference windows can use precomputed raw time-slice summaries.

## Candidate Rules

Default screening rules:

```text
coverage >= 0.90
missing_rate <= 0.10
main directional Rank IC > 0.03
recent OOS directional Rank IC > 0
IC win rate >= 0.52
raw time slices at least 3/4 directionally positive
directional spread > 0
monotonicity_score > 0
mean top quantile turnover <= 1.0
correlation with promoted factors < 0.80
```

Candidate decisions:

- `promote`: ready for later feature-pool or portfolio research.
- `watch`: needs a clearer direction, neutralization, or more evidence.
- `reject`: weak, unstable, low coverage, high missingness, negative OOS, high turnover, or redundant.

## Current Minimal Implementation

The first implementation keeps the existing V2 runner:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v2.py --output-dir outputs\factor_research_v2\liquid2000_default
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_factor_candidates.py --input-dir outputs\factor_research_v2\liquid2000_default
```

The runner now writes the factor data schema, coverage/missing table, top-quantile turnover, and rule-driven candidate decisions.

## Next Expansion

After this minimum is stable:

1. Add industry, size, liquidity, and volatility neutralization.
2. Add market-state slices.
3. Add more factor categories to `registry.py`.
4. Track candidate-pool diffs between runs.
5. Only then connect promoted factors to model or portfolio modules.
