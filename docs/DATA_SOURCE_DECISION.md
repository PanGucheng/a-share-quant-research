# Data Source Decision

This document records the first data-source decision for the A-share data-layer upgrade.

## Decision

Use `chenditc/investment_data` release `2026-06-09` as the first upgraded qlib-format A-share dataset.

The dataset is imported into a separate provider directory:

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609
```

The historical baseline remains unchanged:

```text
E:/qlib_prj/qlib_data/cn_data
```

## Source

- Repository: `https://github.com/chenditc/investment_data`
- Latest release observed: `2026-06-09`
- Release commit shown on GitHub: `604beb5`
- Asset used: `qlib_bin.tar.gz`
- Download URL:

```text
https://github.com/chenditc/investment_data/releases/download/2026-06-09/qlib_bin.tar.gz
```

The repository README says to download the tarball from the latest GitHub release and extract it into a qlib data directory. It also states that the project merges and validates data from several sources, including Tushare, AkShare, Yahoo, Baostock, and final merged tables.

## Imported Artifact

Raw archive:

```text
E:/qlib_prj/data_workspace/raw/investment_data/qlib_bin_2026-06-09.tar.gz
```

Archive metadata:

| item | value |
| --- | --- |
| size bytes | `554151681` |
| SHA256 | `3B1F6AF8C73BF0EA30AEE9C1D15EC5CAF88E377F6201F53CD5D2FC7EBA002AFD` |

Imported qlib provider:

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609
```

## Initial Inspection

Generated reports:

```text
outputs/reports/data_snapshot_community_20260609.md
outputs/reports/data_snapshot_community_20260609.json
```

Summary:

| item | old baseline | community 2026-06-09 |
| --- | ---: | ---: |
| calendar start | `1999-11-10` | `2000-01-04` |
| calendar end | `2020-09-25` | `2026-06-09` |
| feature instruments | `3875` | `6106` |
| total size | `458.77 MB` | `676.92 MB` |
| has `amount` | no | yes |
| has `vwap` | no | yes |
| has `day_future.txt` | no | yes |

Community data fields:

```text
adjclose
amount
change
close
factor
high
low
open
volume
vwap
```

Instrument files:

| file | rows |
| --- | ---: |
| `all.txt` | `6106` |
| `csi1000.txt` | `32005` |
| `csi300.txt` | `15898` |
| `csi500.txt` | `22000` |
| `csi800.txt` | `58404` |
| `csiall.txt` | `119178` |

## Smoke Test

The imported provider was initialized successfully with qlib:

```powershell
E:\anaconda_envs\qlib_env\python.exe -c "import qlib; from qlib.data import D; qlib.init(provider_uri=r'E:/qlib_prj/qlib_data/cn_data_community_20260609', region='cn'); print(D.calendar(start_time='2026-06-01', end_time='2026-06-10')[-5:])"
```

Observed recent calendar values:

```text
2026-06-03
2026-06-04
2026-06-05
2026-06-08
2026-06-09
```

## Rationale

This source is a good second-step candidate because:

- It is already qlib-format, so integration risk is lower than building a converter first.
- It is much fresher than the baseline data.
- It includes the missing `amount` field.
- It adds `vwap`, which is useful for later execution and liquidity analysis.
- It has richer dynamic index membership files.

## Risks

- Field definitions and adjustment conventions still need verification.
- Dynamic index membership must be checked carefully to avoid look-ahead bias.
- The source combines multiple upstream providers, so exact provenance must be documented before relying on it for production-like research.
- Northbound, ST status, suspension, and limit-up/limit-down details still need separate inspection.

## Historical Follow-up Status

The originally proposed data-quality check against the imported provider and the
baseline comparison were completed in later data-layer stages. Their reports and
historical plans are indexed under [DOC_INDEX.md](DOC_INDEX.md) and
[`_archive/02_data_layer_history/`](_archive/02_data_layer_history/). The preserved
provider path is:

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609
```

This section records provenance; it is not a pending action or authorization to
acquire a new provider. Current runtime source and fallback rules are defined by
[DAILY_DATA_UPDATE_V1.md](DAILY_DATA_UPDATE_V1.md).
