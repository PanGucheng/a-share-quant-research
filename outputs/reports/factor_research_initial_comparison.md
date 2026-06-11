# Initial Factor Research Comparison

Scope:

```text
provider: E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
period: 2017-01-01 to 2020-08-01
label: label_1d_t1
factor set: basic price/volume factors
```

Compared universes:

- `csi500`
- `all_stock_shsz_liquid2000`

## Summary

| factor | csi500 mean_rank_ic | liquid2000 mean_rank_ic | interpretation |
| --- | ---: | ---: | --- |
| `rev_5` | `0.022072` | `0.035087` | short-term reversal is stronger in liquid2000 |
| `ret_5` | `-0.022072` | `-0.035087` | same signal as `rev_5` with opposite sign |
| `ret_20` | `-0.024963` | `-0.034431` | medium-term momentum is negative in this label setup |
| `std_20` | `-0.027684` | `-0.036701` | high volatility is generally unfavorable |
| `amplitude_20` | `-0.028375` | `-0.038912` | high intraday range is generally unfavorable |
| `amount_mean_20` | `-0.017888` | `-0.017891` | high liquidity alone is not positive alpha |

## Interpretation

- The first factor pass supports the current route: broad-universe work should focus on tradability and factor diagnostics, not just model changes.
- `liquid2000` has stronger factor separation than `csi500` for short-term reversal and volatility/range factors.
- Simple raw momentum factors are not positive under the current T+1 one-day label; reversal-style definitions are more promising.
- Liquidity is useful as a universe filter, but the raw liquidity level itself is not a strong positive alpha factor.

## Generated Reports

```text
outputs/factor_research/csi500_2017-01-01_2020-08-01/factor_research_report.md
outputs/factor_research/all_stock_shsz_liquid2000_2017-01-01_2020-08-01/factor_research_report.md
```

## Next Work

1. Add robust liquidity factors that reduce the impact of extreme observations.
2. Add factor direction metadata so reports can mark whether high values are expected to be good or bad.
3. Add `label_5d_t1` comparison to distinguish one-day reversal from short-horizon effects.
4. Use selected factors for a linear-model sanity check before expanding to XGBoost/CatBoost.
