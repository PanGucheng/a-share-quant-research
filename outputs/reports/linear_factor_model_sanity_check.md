# Linear Factor Model Sanity Check

Scope:

```text
provider: E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
model: StandardScaler + Ridge(alpha=1.0)
features: basic factor_research factor set
train: 2010-01-01 to 2016-12-31
test: 2017-01-01 to 2020-08-01
```

## Results

| market | label | IC | ICIR | Rank IC | Rank ICIR | test dates | prediction rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `csi500` | `label_1d_t1` | `0.001525` | `0.011540` | `0.013532` | `0.113278` | `869` | `405956` |
| `all_stock_shsz_liquid2000` | `label_1d_t1` | `0.003672` | `0.042713` | `0.029948` | `0.326393` | `869` | `1628000` |
| `csi500` | `label_5d_t1` | `0.004982` | `0.037146` | `0.003396` | `0.027699` | `865` | `401738` |
| `all_stock_shsz_liquid2000` | `label_5d_t1` | `-0.007321` | `-0.082846` | `-0.000956` | `-0.009671` | `865` | `1614771` |

## Interpretation

- The basic factor set has usable linear explanatory power for `label_1d_t1`, especially in `all_stock_shsz_liquid2000`.
- The same linear combination does not transfer to `label_5d_t1`; five-day prediction likely needs different features, risk controls, or factor directions.
- This supports the current staged plan: keep LightGBM as the main qrun baseline, use linear models as sanity checks, and postpone heavier model comparisons until factor direction and horizon are clearer.

## Output Reports

```text
outputs/linear_factor_model/csi500_label1d/linear_factor_model_report.md
outputs/linear_factor_model/all_stock_shsz_liquid2000_label1d/linear_factor_model_report.md
outputs/linear_factor_model/csi500_label5d/linear_factor_model_report.md
outputs/linear_factor_model/all_stock_shsz_liquid2000_label5d/linear_factor_model_report.md
```
