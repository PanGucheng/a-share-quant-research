# A-share Universe Policy

This document defines the default stock-universe policy for this project.

## Default Decision

Use exchange-defined CSI universe files as the default research universes:

```text
csi300
csi500
csi800
csi1000
```

For broad all-market research, use Shanghai and Shenzhen A-shares by default and exclude Beijing Stock Exchange instruments unless the experiment explicitly studies BSE liquidity, micro-cap behavior, or BSE-specific execution constraints.

Rationale:

- The current baseline is `LightGBM + Alpha158 + CSI500`; keeping CSI files unchanged preserves comparability.
- The community provider includes BSE instruments in broad files, but CSI300/CSI500/CSI800/CSI1000 currently contain only `SH` and `SZ` symbols.
- BSE instruments can have materially different liquidity, listing history, price-limit behavior, and execution assumptions. Mixing them into broad all-market experiments without a separate policy would make results harder to interpret.

## Current Provider Evidence

Reports:

```text
outputs/reports/universe_summary_old.md
outputs/reports/universe_summary_community_20260609.md
```

Historical baseline provider:

| scope | unique instruments | prefixes |
| --- | ---: | --- |
| features | `3875` | `SH: 1565`, `SZ: 2310` |
| `all.txt` | `3875` | `SH: 1565`, `SZ: 2310` |
| `csi300.txt` | `690` | `SH: 410`, `SZ: 280` |
| `csi500.txt` | `1540` | `SH: 783`, `SZ: 757` |

Community provider `2026-06-09`:

| scope | unique instruments | prefixes |
| --- | ---: | --- |
| features | `6106` | `BJ: 568`, `SH: 2459`, `SZ: 3079` |
| `all.txt` | `6106` | `BJ: 568`, `SH: 2459`, `SZ: 3079` |
| `csiall.txt` | `5718` | `BJ: 342`, `SH: 2366`, `SZ: 3010` |
| `csi300.txt` | `939` | `SH: 542`, `SZ: 397` |
| `csi500.txt` | `1774` | `SH: 913`, `SZ: 861` |
| `csi800.txt` | `1993` | `SH: 1071`, `SZ: 922` |
| `csi1000.txt` | `2744` | `SH: 1117`, `SZ: 1627` |

## Policy Rules

1. Baseline experiments keep using `csi500` unless the experiment states otherwise.
2. CSI universe files from the provider are treated as dynamic membership ranges and must not be flattened into a single static historical union.
3. Broad all-market experiments should use an explicit filtered universe that excludes `BJ*` instruments.
4. BSE-inclusive experiments must use a separate config name and report section, for example `all_with_bse` or `csiall_with_bse`.
5. Any new provider must run `scripts/summarize_universe.py` before it is used for model comparison.

## Derived Broad Universe

The first derived broad stock universe for the community provider is:

```text
outputs/universes/community_20260609/all_stock_shsz.txt
```

It is generated from:

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609/instruments/all.txt
```

Generation policy:

- Include `SH` and `SZ`.
- Exclude `BJ`.
- Exclude common index-like symbols such as `SH000*` and `SZ399*`.

Generated result:

| item | rows |
| --- | ---: |
| source rows | `6106` |
| output rows | `5532` |
| BSE rows retained | `0` |
| index-like rows retained | `0` |

Report:

```text
outputs/reports/filtered_universe_all_stock_shsz_community_20260609.md
```

## Commands

Generate universe summaries:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_universe.py --provider-uri E:/qlib_prj/qlib_data/cn_data --output outputs/reports/universe_summary_old.md --json-output outputs/reports/universe_summary_old.json
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_universe.py --provider-uri E:/qlib_prj/qlib_data/cn_data_community_20260609 --output outputs/reports/universe_summary_community_20260609.md --json-output outputs/reports/universe_summary_community_20260609.json
```

Generate the derived Shanghai/Shenzhen stock universe:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\create_filtered_universe.py --source E:/qlib_prj/qlib_data/cn_data_community_20260609/instruments/all.txt --output outputs/universes/community_20260609/all_stock_shsz.txt --include-prefixes SH,SZ --exclude-index-symbols --summary-output outputs/reports/filtered_universe_all_stock_shsz_community_20260609.md
```

## Next Implementation Step

Create a provider-specific derived data directory or copy step that places reviewed generated universe files under `instruments/` without mutating the raw imported provider.
