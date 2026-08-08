# Model Diagnostic V1

## Status

- Core diagnostic: `complete`
- Style attribution: `partial / waiting external PIT data` (`unavailable_data`)
- SHAP runtime: `ready`
- Frozen base cache: `9f296c6671c2cf92a843a47038e28cf64cb9eccc6961acc22459d54ed15c68bb` (hit=True)
- Historical diagnosis != unbiased future evidence; split_003 has already been observed.

## Deliverables

Factor structure, existing-PIT conditional IC, fixed ranking concentration, fixed signal decay, ranking stability/retention/edge churn, frozen LightGBM importance, permutation importance, optional SHAP summaries, and P01 prediction/portfolio/cost attribution are published as machine-readable tables.

Liquidity, volatility, and momentum fields are explicitly proxies. They are not historical market capitalization, Size, or industry data.

## Split Evidence

| Split | 20D Rank IC | 20D ICIR | Top10 excess | P01 total | Benchmark total | Cost drag | Avg daily turnover |
|---|---:|---:|---:|---:|---:|---:|---:|
| split_001 | 0.077783 | 0.487 | 0.001425 | 0.3927 | 0.2232 | 0.0755 | 0.2839 |
| split_002 | 0.143224 | 0.738 | 0.002502 | 0.1892 | 0.1208 | 0.0647 | 0.2685 |
| split_003 | 0.051802 | 0.317 | -0.010924 | 0.0357 | 0.1919 | 0.0580 | 0.2553 |

## Interpretation Boundary

The tables diagnose the already-observed historical splits. They do not authorize factor deletion, model retraining, TopK/rebalance selection, or any change to P01. The hypotheses document contains only candidates for a separately preregistered V2 study.
