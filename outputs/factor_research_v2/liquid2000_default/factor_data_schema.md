# Factor Data Schema

The internal evaluator uses a wide daily cross-sectional frame for speed, but the research contract follows an Alphalens-style long factor_data schema.

| column | meaning |
| --- | --- |
| `datetime` | Trading date. |
| `instrument` | Qlib instrument code. |
| `factor` | Factor name from the registry. |
| `factor_value` | Numeric factor value before quantile bucketing. |
| `factor_quantile` | Daily cross-sectional quantile, 1 is lowest. |
| `label` | Forward-return label name. |
| `forward_return` | Forward return for the label. |
| `can_buy` | Tradability label from the unified tradability layer. |
| `can_sell` | Tradability label from the unified tradability layer. |
| `liquidity_bucket` | Daily liquidity bucket from the tradability layer. |
| `tradability_score` | Tradability score from the tradability layer. |
| `data_quality_status` | Data quality status carried from tradability/data_quality outputs. |
| `has_data_quality_issue` | Whether row-level data_quality flagged this date/instrument. |
