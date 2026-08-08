# Model Diagnostic Style Attribution Extension V1

Core diagnostic values were not recomputed or modified.

## Evidence

- `split_001` Top50 mean size percentile `0.456` vs universe `0.500`; Small share `0.364`.
- `split_002` Top50 mean size percentile `0.623` vs universe `0.500`; Small share `0.160`.
- `split_003` Top50 mean size percentile `0.637` vs universe `0.500`; Small share `0.163`.

- `split_001` liquidity-size daily rank correlation `0.544`; Small/Large proxy percentiles `0.330`/`0.702`.
- `split_002` liquidity-size daily rank correlation `0.471`; Small/Large proxy percentiles `0.347`/`0.669`.
- `split_003` liquidity-size daily rank correlation `0.595`; Small/Large proxy percentiles `0.291`/`0.702`.
- `split_001` model Size-conditional Rank IC: Small `0.0990`, Mid `0.0377`, Large `0.0427`.
- `split_002` model Size-conditional Rank IC: Small `0.1756`, Mid `0.1573`, Large `0.0946`.
- `split_003` model Size-conditional Rank IC: Small `0.1359`, Mid `0.0780`, Large `-0.0378`.

## Controlled Model Alpha

- `split_001` controlled model-score coefficient `0.000314`, positive-day ratio `0.592`.
- `split_002` controlled model-score coefficient `0.004054`, positive-day ratio `0.597`.
- `split_003` controlled model-score coefficient `-0.000580`, positive-day ratio `0.492`.

## Industry Evidence

- `split_001` largest Top50 over-exposure: `公用事业` at `0.044` active share.
- `split_002` largest Top50 over-exposure: `银行` at `0.096` active share.
- `split_003` largest Top50 over-exposure: `银行` at `0.096` active share.

## Answers To Frozen Research Questions

1. Small-cap bias: not persistent; below-universe Top50 Size appears only in `split_001`, while the three-split average Top50 size percentile is `0.572`.
2. Low-liquidity proxy: partly associated with Small Cap cross-sectionally (`amount_mean_20` versus Size mean daily rank correlation `0.537`); this is association, not proof that the proxy is only Size.
3. Size regime mismatch: consistent with the observed decay; Small-minus-Large future return changed from development mean `0.030345` to split_003 `-0.009101`. This is attribution only.
4. Industry concentration: maximum absolute Top50 active SW L1 share is `0.104`; detailed drift and HHI are in `industry_exposure.csv`.
5. Benchmark-relative industry explanation: unresolved because monthly index weights were canary-verified only and were not admitted as formal SDK research input.
6. Independent model information: mixed across splits after daily Size and SW L1 controls; coefficients are attribution statistics, not an unbiased final estimate.
7. V2 hypotheses: evidence statuses are listed in `v2_hypothesis_status.md`; no V2 training, factor deletion, neutralization, TopK scan, or portfolio optimization was performed.

Industry data represents historical effective-date classification reconstructed today, not proof of the database vintage available on each historical date.

Historical diagnosis != unbiased future evidence.
