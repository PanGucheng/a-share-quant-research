# Data Upgrade Comparison

This document compares the historical baseline qlib data with the first imported community qlib data.

## Compared Providers

| provider | path | role |
| --- | --- | --- |
| Historical baseline | `E:/qlib_prj/qlib_data/cn_data` | Reproducibility anchor |
| Community 2026-06-09 | `E:/qlib_prj/qlib_data/cn_data_community_20260609` | Candidate upgraded provider |

## Source

The community provider was imported from:

```text
https://github.com/chenditc/investment_data/releases/download/2026-06-09/qlib_bin.tar.gz
```

Raw archive:

```text
E:/qlib_prj/data_workspace/raw/investment_data/qlib_bin_2026-06-09.tar.gz
```

SHA256:

```text
3B1F6AF8C73BF0EA30AEE9C1D15EC5CAF88E377F6201F53CD5D2FC7EBA002AFD
```

## Structural Comparison

| item | historical baseline | community 2026-06-09 |
| --- | ---: | ---: |
| calendar start | `1999-11-10` | `2000-01-04` |
| calendar end | `2020-09-25` | `2026-06-09` |
| future calendar end | none | `2026-12-31` |
| feature instruments | `3875` | `6106` |
| total provider size | `458.77 MB` | `676.92 MB` |
| fields | `adjclose`, `change`, `close`, `factor`, `high`, `low`, `open`, `volume` | `adjclose`, `amount`, `change`, `close`, `factor`, `high`, `low`, `open`, `volume`, `vwap` |
| has `amount` | no | yes |
| has `vwap` | no | yes |

Generated reports:

```text
outputs/reports/data_snapshot_old.md
outputs/reports/data_snapshot_community_20260609.md
```

## Instrument File Comparison

| file | historical baseline rows | community rows |
| --- | ---: | ---: |
| `all.txt` | `3875` | `6106` |
| `csi300.txt` | `820` | `15898` |
| `csi500.txt` | `2017` | `22000` |
| `csi1000.txt` | none | `32005` |
| `csi800.txt` | none | `58404` |
| `csiall.txt` | none | `119178` |

Interpretation:

- The community data uses much richer dynamic index membership ranges.
- Directly comparing row counts is not enough; the next quality upgrade must verify membership intervals and avoid look-ahead bias.

## Data Quality Comparison

Scope:

```text
market: csi500
start: 2017-01-01
end: 2020-08-01
```

Static reports from the first pass:

```text
outputs/data_quality/csi500_2017-01-01_2020-08-01
outputs/data_quality_community/csi500_2017-01-01_2020-08-01
```

Dynamic-membership reports from the upgraded checker:

```text
outputs/data_quality_dynamic_old/csi500_2017-01-01_2020-08-01
outputs/data_quality_dynamic_community/csi500_2017-01-01_2020-08-01
```

Lifecycle-clipped dynamic-membership reports:

```text
outputs/data_quality_lifecycle_old/csi500_2017-01-01_2020-08-01
outputs/data_quality_lifecycle_community/csi500_2017-01-01_2020-08-01
```

Lifecycle-clipped dynamic-membership overview:

| metric | historical baseline | community 2026-06-09 |
| --- | ---: | ---: |
| instrument count | `812` | `816` |
| membership rows after lifecycle clipping | `1880` | `21999` |
| membership rows clipped | `646` | `14` |
| calendar trade days | `871` | `871` |
| raw rows | `433947` | `435352` |
| total issue rows | `506712` | `77523` |
| avg availability score | `96.8254` | `97.0405` |
| min availability score | `40.0` | `40.0` |
| avg expected instruments per day | `499.9816` | `499.8301` |
| min expected instruments per day | `499` | `498` |
| max expected instruments per day | `500` | `500` |
| avg coverage rate | `0.9631` | `0.9703` |
| min coverage rate | `0.0` | `0.9040` |

Field missing rates:

| field | historical baseline | community 2026-06-09 |
| --- | ---: | ---: |
| open | `3.3444%` | `2.9666%` |
| high | `3.3444%` | `2.9666%` |
| low | `3.3444%` | `2.9666%` |
| close | `3.3444%` | `2.9666%` |
| volume | `3.3444%` | `2.9666%` |
| amount | `100.0000%` | `2.9666%` |

Interpretation:

- The community provider fixes the main baseline problem: `amount` is no longer structurally missing.
- Total issue rows fall sharply, mostly because `amount_missing` is no longer universal.
- Dynamic index membership handling changes the interpretation substantially: average coverage is above 96% for both providers, not around 59%.
- Lifecycle clipping is now applied before expected membership coverage is calculated. It clips 646 historical baseline membership rows and only 14 community-provider rows.
- Minimum date coverage improves from zero in the historical baseline to about 90.40% in the community provider.
- Missing OHLCVA rows still exist and must be interpreted with lifecycle and suspension awareness.

## Baseline Qrun Comparison

Both runs use:

```text
LightGBM + Alpha158 + CSI500
train: 2008-01-01 to 2014-12-31
valid: 2015-01-01 to 2016-12-31
test: 2017-01-01 to 2020-08-01
```

Historical baseline run:

```text
Run ID: f6a1207624a74d498c00655a218b274c
Log: logs/qrun_lightgbm_alpha158_csi500_20260611_194840.log
```

Community provider run:

```text
Run ID: 34754ef6650a4253b371301559df4ce3
Log: logs/qrun_lightgbm_alpha158_csi500_20260611_201059.log
```

Metrics:

| metric | historical baseline | community 2026-06-09 | direction |
| --- | ---: | ---: | --- |
| IC | `0.039390` | `0.037766` | slightly lower |
| ICIR | `0.403653` | `0.361939` | lower |
| Rank IC | `0.047274` | `0.048017` | slightly higher |
| Rank ICIR | `0.505228` | `0.486945` | slightly lower |
| excess return with cost annualized return | `0.111076` | `0.116544` | higher |
| excess return with cost information ratio | `1.325249` | `1.438300` | higher |
| excess return with cost max drawdown | `-0.072773` | `-0.075736` | slightly worse |
| excess return without cost annualized return | `0.153454` | `0.154918` | slightly higher |
| excess return without cost information ratio | `1.831191` | `1.912617` | higher |
| excess return without cost max drawdown | `-0.066508` | `-0.068136` | slightly worse |

Interpretation:

- Signal quality remains broadly comparable.
- Rank IC is slightly better on the community provider, while IC and ICIR are lower.
- Portfolio metrics improve modestly in annualized excess return and information ratio.
- Drawdown is slightly worse and should be inspected before trusting the upgrade.
- The result is encouraging enough to continue with the community provider, but not enough to declare it production-ready.

## Current Decision

Use `E:/qlib_prj/qlib_data/cn_data_community_20260609` as the candidate data provider for the next development tasks.

Do not delete or overwrite `E:/qlib_prj/qlib_data/cn_data`.

## Required Follow-up

Done in this step:

1. Data quality checks now use dynamic index membership intervals from `instruments/<market>.txt`.
2. Data quality checks now clip index membership intervals to the broad lifecycle ranges in `all.txt`.
3. The community provider has been imported and initialized successfully.
4. The community provider has completed the same LightGBM Alpha158 CSI500 qrun baseline.
5. Initial field validation found that `vwap = amount / volume * 10` for sampled rows.

Remaining follow-up:

1. Add suspension-aware missing-data checks.
2. Verify adjustment factor and `adjclose` semantics with a few known corporate-action cases.
3. Confirm `amount` and `volume` units from upstream documentation or raw source tables.
4. Decide whether Beijing Stock Exchange instruments should be included or filtered for each research universe.
5. Create a reusable config templating pattern for provider-specific qrun configs.
