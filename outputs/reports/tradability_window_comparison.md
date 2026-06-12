# Tradability Window Comparison

| window | rows | instruments | dates | can_buy_rate | can_sell_rate | avg_score | suspended_rate | limit_up_rate | limit_down_rate | low_liquidity_rate | core_missing_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| main_2021_2023 | 1414832 | 1977 | 727 | 0.585493 | 0.991338 | 89.055241 | 0.003501 | 0.012141 | 0.003275 | 0.398704 | 0.003501 |
| recent_oos_2024_2026 | 1096231 | 1904 | 587 | 0.583596 | 0.989573 | 88.918777 | 0.002343 | 0.015565 | 0.005880 | 0.399169 | 0.002343 |

## Interpretation

- The two windows have similar buyable coverage and liquidity-filter impact.
- Low liquidity remains the dominant exclusion reason, so factor portfolios should keep `liquidity_bucket >= 3` as a default constraint.
- Warm-up dates with zero buyable instruments should be skipped by portfolio experiments.
