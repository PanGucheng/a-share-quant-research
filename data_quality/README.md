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
- Dynamic membership coverage: if `instruments/<market>.txt` exists, expected instruments are calculated from each membership date range instead of treating the entire historical union as active every day.
- Lifecycle clipping: if `instruments/all.txt` exists, membership intervals are clipped to each instrument's broad lifecycle range before expected coverage is calculated.
- Expected missing spans: continuous missing ranges inside expected membership/lifecycle dates, useful for later suspension-source reconciliation.

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

Check another provider:

```powershell
python -m data_quality.checker --provider-uri E:/qlib_prj/qlib_data/cn_data_community_20260609 --market csi500 --start-time 2017-01-01 --end-time 2020-08-01 --output-dir outputs/data_quality_dynamic_community
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
- `expected_missing_spans.csv`
- `date_coverage.csv`
- `abnormal_instruments.csv`
- `abnormal_dates.csv`
- `long_gaps.csv`

`overview.csv` includes `membership_rows`, `membership_clipped_rows`, `dynamic_membership_enabled`, and expected-instrument-count statistics when a market membership file is available.

Markdown report:

- `data_quality_report.md`
