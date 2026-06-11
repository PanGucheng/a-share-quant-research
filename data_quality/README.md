# A-share Data Quality Diagnostics

This module diagnoses local Qlib A-share data quality without modifying Qlib source code or raw data.

It does not train models, run backtests, calculate Alpha158 IC, screen factors, or repair data.

## Checks

- Missing OHLCVA fields: `open`, `high`, `low`, `close`, `volume`, `amount`
- Price anomalies: non-positive prices, `high < low`, open/close outside high-low range
- Volume and amount anomalies: negative values, long zero runs
- Return anomalies: oversized daily return, close jump, suspected adjustment error
- Coverage issues: per-instrument valid days, missing ratio, per-date coverage, long-missing instruments
- Time range issues: instrument start/end date and long internal gaps

## Run

From `E:/qlib_prj/qlib_baseline`:

```powershell
conda activate qlib_env
python -m data_quality.checker --config data_quality/config.yaml
```

Override scope from the command line:

```powershell
python -m data_quality.checker --market csi300 --start-time 2019-01-01 --end-time 2020-08-01
```

## Outputs

By default, outputs are written to:

```text
outputs/data_quality/<market>_<start>_<end>/
```

CSV outputs:

- `overview.csv`
- `field_missing_rate.csv`
- `rule_counts.csv`
- `row_issues.csv`
- `price_anomalies.csv`
- `volume_amount_anomalies.csv`
- `return_anomalies.csv`
- `instrument_availability.csv`
- `date_coverage.csv`
- `abnormal_instruments.csv`
- `abnormal_dates.csv`
- `long_gaps.csv`

Markdown report:

- `data_quality_report.md`

