# TopK Scan: liquid2000 Community 2026-06-09

Scope:

```text
provider: E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
market: all_stock_shsz_liquid2000
model: LightGBM
features: Alpha158
train: 2008-01-01 to 2014-12-31
valid: 2015-01-01 to 2016-12-31
test: 2017-01-01 to 2020-08-01
benchmark: SH000985
```

The signal model is unchanged across runs. Only `TopkDropoutStrategy.topk` and `n_drop` are changed.

## Results

| topk | n_drop | experiment_id | run_id | IC | Rank IC | cost annualized excess | cost IR | cost max drawdown | no-cost annualized excess | no-cost IR | no-cost max drawdown |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 5 | `365355581238963703` | `8902c70d60f14afa8064275c1db3404a` | `0.072184` | `0.062222` | `0.054915` | `0.312190` | `-0.169295` | `0.079570` | `0.452356` | `-0.165707` |
| 100 | 10 | `441016757506069138` | `be0b410908a14b0d8e4246e6c633974d` | `0.072184` | `0.062222` | `0.082686` | `0.524204` | `-0.148199` | `0.118495` | `0.751031` | `-0.144073` |
| 200 | 20 | `979893573690720104` | `5d833f55f5ee47df92501e4905e66366` | `0.072184` | `0.062222` | `0.151621` | `1.051600` | `-0.149152` | `0.192997` | `1.338232` | `-0.146271` |
| 300 | 30 | `649002761809471200` | `16dc5b1bb7a94460968f0adfa36b6c9a` | `0.072184` | `0.062222` | `0.151472` | `1.060656` | `-0.146884` | `0.194098` | `1.358735` | `-0.144199` |

## Interpretation

- Increasing holdings from `topk=50` to `topk=200` materially improves the broad-universe portfolio result.
- `topk=300` does not improve annualized excess return versus `topk=200`, but it slightly improves cost IR and max drawdown.
- The current best candidate is `topk=300, n_drop=30` if the priority is smoother risk-adjusted performance, and `topk=200, n_drop=20` if the priority is a simpler, slightly more concentrated portfolio.
- The unchanged IC/Rank IC confirms this scan is testing portfolio construction rather than model signal quality.

## Next Decision

Use `all_stock_shsz_liquid2000` with `topk=200` or `topk=300` as the next broad-universe portfolio baseline.

Before expanding models, continue with:

1. Factor research module scaffolding.
2. Abnormal liquidity check for `SH601313`.
3. Turnover and holding diagnostics for `topk=200` and `topk=300`.
