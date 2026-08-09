# Daily Data Update V1

This is the lightweight data-to-feature part of the Forward Track. Its source policy
is fixed:

```text
primary / long-term: chenditc/investment_data Community Qlib
single daily fallback: BaoStock
```

The entry point is:

```powershell
qlib-daily-update --target-date 2026-08-07
```

With the Qlib environment activated, `qlib-daily-update` defaults to the local
calendar date. Install `requirements-daily-update.txt` and this project in editable
mode in that environment. `python scripts/daily_update.py` remains a compatibility
wrapper around the same command implementation.

The command checks the latest Community release first. If it covers the target date,
the release is used directly. Otherwise it asks BaoStock for the target-day stock
list only after 18:00 Asia/Shanghai, so both the documented 17:30 daily-bar window and
18:00 adjustment-factor window have elapsed, before downloading or mutating any
provider. An absent list, incomplete OHLCVA,
request error, or coverage below 95% returns `status=not_ready` with exit code zero;
it writes no empty daily data or feature snapshot.

For a valid fallback, the collector uses BaoStock 0.9.3's official
`query_daily_history_k_AStock(date=...)` once per calendar date, rather than issuing
one historical request per stock. It also calls `query_daily_adjust_factor(date=...)`
once to confirm the factor endpoint is available. A transient factor socket error is
retried only once after ten seconds. The process uses no concurrent BaoStock sessions,
keeping request volume far below the behavior shown on the official blacklist page.
Raw fields follow the frozen Data Source Audit V2
semantics. The previous valid Community close and factor anchor each instrument. For
each later BaoStock row:

```text
factor_t = factor_previous * raw_close_previous / BaoStock_preclose_t
provider_price = raw_price * factor_t
provider_volume = raw_volume_shares / (factor_t * 100)
provider_amount = raw_amount_cny / 1000
```

The Community provider is copied to an untracked runtime cache and updated through
Qlib's existing `dump_update`. The historical provider is never modified. The frozen
52 features are computed with the existing Qlib expressions, project basic factors,
KunQuant Alpha101 adapter, and TA adapter. Successful output is
`outputs/daily_data_update_v1/<date>/feature_snapshot.csv`.

When a later Community release covers a date previously filled by BaoStock, rerunning
the same date compares reconstructed raw OHLCVA, factor, and all 52 final factors. A
material difference removes the current snapshot alias, records the comparison, and
stops. This command does not run prediction, paper portfolio logic, retraining, or
Strategy V2.

## Forward Prediction Input

The existing Forward pipeline can consume a ready day directly:

```powershell
qlib-forward-predict `
  --date 2026-08-07 `
  --calendar-file <community-provider>/calendars/day_future.txt `
  --daily-update-dir outputs/daily_data_update_v1/2026-08-07
```

The adapter selects exactly the feature-snapshot instruments and maps provider
OHLCVA to the existing Forward raw schema. BaoStock documents suspended daily bars
as unchanged OHLC with zero volume and amount. When the batch response leaves those
two fields empty, the adapter records the affected instruments and maps only those
fields to zero. It does not filter instruments or alter model features.
