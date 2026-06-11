# Data Baseline Snapshot

This document freezes the current local A-share qlib data directory as the historical baseline for later data upgrades.

## Baseline Data Directory

```text
E:/qlib_prj/qlib_data/cn_data
```

This directory is treated as read-only for the data-layer upgrade work. New data should be imported into a separate directory such as:

```text
E:/qlib_prj/qlib_data/cn_data_community_latest
E:/qlib_prj/qlib_data/cn_data_akshare_latest
```

## Snapshot Summary

| item | value |
| --- | --- |
| provider URI | `E:/qlib_prj/qlib_data/cn_data` |
| total size | `458.77 MB` |
| calendar file | `calendars/day.txt` |
| calendar count | `4943` |
| calendar start | `1999-11-10` |
| calendar end | `2020-09-25` |
| feature instrument directories | `3875` |
| global fields | `adjclose`, `change`, `close`, `factor`, `high`, `low`, `open`, `volume` |
| missing key field | `amount` |

## Instrument Files

| file | rows | note |
| --- | ---: | --- |
| `all.txt` | `3875` | broad universe |
| `csi100.txt` | `246` | CSI 100 membership history |
| `csi300.txt` | `820` | CSI 300 membership history |
| `csi500.txt` | `2017` | CSI 500 membership history |

Sample rows observed:

```text
all.txt:    SH000300  2005-01-04  2020-09-25
csi300.txt: SH600000  2005-01-01  2020-09-25
csi500.txt: SH600006  2013-06-25  2022-03-21
```

Important note: some instrument membership files contain dates beyond the current price calendar end date. For example, `csi500.txt` contains rows ending on `2022-03-21`, while the current calendar ends on `2020-09-25`. The next data-quality upgrade must distinguish this from a true price-data gap.

## Archive File

| file | size bytes | SHA256 |
| --- | ---: | --- |
| `20260222105635_qlib_data_cn_1d_latest.zip` | `196549189` | `8A323FEC32E1BD0C1662C1FC753AD033F190523E450936E63C9509796EA32E41` |

## Generated Structure Report

The first machine-generated snapshot report is:

```text
outputs/reports/data_snapshot_old.md
outputs/reports/data_snapshot_old.json
```

Generated with:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\inspect_qlib_data.py --provider-uri E:\qlib_prj\qlib_data\cn_data --output outputs\reports\data_snapshot_old.md --json-output outputs\reports\data_snapshot_old.json
```

## Baseline Experiment Anchor

Historical validated run:

```text
Experiment ID: 902143453991050438
Run ID: 1664d70296414b29ad01866f1f585e15
```

Recent unsandboxed reproducibility run:

```text
Experiment ID: 902143453991050438
Run ID: f6a1207624a74d498c00655a218b274c
```

Core metrics from the recent unsandboxed run:

| metric | value |
| --- | ---: |
| IC | `0.039390054668819584` |
| ICIR | `0.4036532897768011` |
| Rank IC | `0.04727387420884508` |
| Rank ICIR | `0.5052277849472542` |
| excess return with cost annualized return | `0.11107595634238779` |
| excess return with cost information ratio | `1.3252492154867777` |
| excess return with cost max drawdown | `-0.07277290679859844` |

## Known Data Issues To Preserve For Comparison

- `amount` is not available in this data snapshot.
- Some instruments have missing OHLCV rows within the baseline test window.
- Some dates have low coverage in the current data-quality report.
- The dataset is stale for recent A-share research because the price calendar ends on `2020-09-25`.
- Dynamic index membership handling needs improvement before comparing broad-market results across data versions.

## Rule

Do not overwrite or repair `E:/qlib_prj/qlib_data/cn_data` in place. All cleaning, conversion, and upgraded datasets must go into separate directories.
