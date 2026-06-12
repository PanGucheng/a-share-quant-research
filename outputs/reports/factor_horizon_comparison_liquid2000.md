# Factor Horizon Comparison: liquid2000

Scope:

```text
market: all_stock_shsz_liquid2000
provider: E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
labels: label_1d_t1, label_10d_t1, label_20d_t1
time slices: 2010-2016, 2017-2020, 2021-2023, 2024-2026
```

## Directional Rank IC Summary

| label | factor | expected direction | positive directional slices | mean directional Rank IC | recent 2024-2026 directional Rank IC |
| --- | --- | --- | ---: | ---: | ---: |
| `label_1d_t1` | `amplitude_20` | negative | `4/4` | `0.039469` | `0.038382` |
| `label_1d_t1` | `std_20` | negative | `4/4` | `0.037023` | `0.039549` |
| `label_1d_t1` | `rev_5` | positive | `4/4` | `0.036709` | `0.025411` |
| `label_10d_t1` | `amplitude_20` | negative | `4/4` | `0.065014` | `0.045089` |
| `label_10d_t1` | `std_20` | negative | `4/4` | `0.062395` | `0.047369` |
| `label_10d_t1` | `rev_5` | positive | `4/4` | `0.028299` | `0.034178` |
| `label_20d_t1` | `amplitude_20` | negative | `4/4` | `0.075864` | `0.051124` |
| `label_20d_t1` | `std_20` | negative | `4/4` | `0.071619` | `0.053787` |
| `label_20d_t1` | `rev_5` | positive | `4/4` | `0.030789` | `0.040805` |

## Interpretation

- The low-frequency labels are more aligned with the personal-investor requirement than `label_1d_t1`.
- Low volatility and low amplitude become stronger on `label_10d_t1` and strongest on `label_20d_t1`.
- Short-term reversal remains directionally stable, but it should be used as a secondary score component because it can create turnover pressure.
- The next portfolio experiments should use `label_20d_t1` first, with weekly or monthly rebalance constraints, and keep `label_10d_t1` as the faster comparison.
