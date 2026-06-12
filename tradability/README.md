# A-share Tradability Label Layer

This module builds a stable `date x instrument` tradability label table for downstream factor research, portfolio constraints, and backtest constraints.

## Inputs

- Qlib daily OHLCV data from a provider URI.
- A Qlib instrument universe such as `all_stock_shsz_liquid2000`.
- Data quality diagnosis outputs containing `row_issues.csv`, `instrument_availability.csv`, and `date_coverage.csv`.
- Rule thresholds from `tradability/config.yaml`.

## Outputs

The stable output directory is:

```text
outputs/tradability/<market>_<start>_<end>/
```

Files:

- `tradability_labels.csv`: main row-level label table.
- `summary.csv`: top-level metrics.
- `instrument_scores.csv`: per-instrument tradability scores.
- `date_coverage.csv`: per-date tradability coverage.
- `reason_counts.csv`: disabled reason counts.
- `tradability_report.md`: human-readable report.
- `resolved_config.yaml`: final config used.
- `run.log`: runtime log.

## Main Fields

- `can_buy`, `can_sell`: final composite tradability flags.
- `tradability_score`: 0-100 score after configured penalties.
- `disabled_reason`: `|`-separated stable reason codes.
- `liquidity_source`: `amount`, `close_volume`, or `unavailable`.
- `limit_status`: `normal`, `limit_up`, `limit_down`, or `unknown`.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_tradability_labels.ps1
```

Validate:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\validate_tradability_outputs.py --output-dir outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29
```

## Limits

- The first version does not use official ST, suspension, or limit-price data.
- Limit-up and limit-down labels are inferred from OHLC and previous close.
- If required inputs are missing, the module fails clearly instead of silently producing misleading labels.
