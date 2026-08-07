# Qlib A-Share Research Baseline

This repository is a personal A-share quantitative research workspace built around
[Microsoft Qlib](https://github.com/microsoft/qlib). It supports learning and
practical work across factors, machine learning, portfolios, backtests, and genuine
forward observation. It is intentionally not an institutional platform, compliance
system, or production trading service.

Chinese documentation is available in [README.zh-CN.md](README.zh-CN.md).

> This project is for research and education only. It is not investment advice and
> does not contain live trading code.

## Current Direction

> **Current milestone:** Historical LightGBM research and Historical Portfolio
> Backtest V1 are complete. The frozen LightGBM + P01 candidate (52 factors, long-only
> Top50 equal weight, five-day rebalance) performed well in development but materially
> underperformed its benchmark in the already observed `split_003`. `split_003` is
> diagnosis-only and cannot be reused for selection or described as a fresh holdout.

The project now follows a research-first priority: correct research logic, no future
data, and strict train/validation/test isolation come first; interpretability,
maintainability, automation, and governance follow a personal-project cost/benefit
test. The detailed direction is in
[docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md](docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md).

Qlib remains the main data and model backbone, with existing research modules reused:

- **Qlib baseline**: validated official LightGBM + Alpha158 workflow.
- **Data quality**: checks missing values, price/volume anomalies, lifecycle gaps,
  and row-level issues.
- **Tradability layer**: converts market liquidity and data-quality diagnostics into
  reusable tradability labels.
- **Factor research**: evaluates factors after data-quality and tradability filters,
  using IC, Rank IC, ICIR, group returns, turnover, coverage, missing rate,
  correlation, monotonicity, slices, and neutralization diagnostics.
- **Factor screening**: converts factor research outputs into an explainable
  candidate board before portfolio testing.
- **Qlib execution layer**: pinned Exchange/Executor adapters, A-share constraints,
  normalized artifacts, exact synthetic reconciliation, and a local-reference run.

Existing manifests, validators, lineage, receipts, and frozen artifacts remain for
compatibility and historical evidence. New research modules do not copy that heavy
governance by default: ordinary Python, YAML, CSV/JSON, figures, Markdown reports,
Git, and focused pytest coverage are preferred when sufficient.

The time-sensitive priority is a lightweight Forward Track: Daily Data Update,
frozen Strategy V1 prediction, and paper portfolio recording should begin genuine
prospective evidence collection as soon as practical. A prediction not produced at
the time cannot later be backfilled as independent prospective evidence.

Strategy Diagnostics V1 is a parallel historical research task. It explains the
observed P01 weakness through performance, IC, exposure, concentration, turnover,
and cost analysis without changing Strategy V1 or blocking forward collection.
Historical diagnostics plus genuine forward evidence may later justify a separately
versioned Strategy V2. Shadow or small-capital work remains a much later direction.

## Repository Layout

```text
configs/          Qlib qrun workflow configs.
data_quality/     Data-quality diagnostic module.
tradability/      Tradability label builder and reports.
factor_research/  Factor evaluation, preprocessing, neutralization, and reports.
scripts/          Reproducible command-line runners and summaries.
docs/             Current development docs plus archived plans and audits.
outputs/          Selected validated outputs and compact research summaries.
logs/             Kept baseline log plus local ignored runtime logs.
tmp/              Ignored local caches, reference repos, and scratch outputs.
```

## Environment

The validated local setup uses:

```text
Project:       E:\qlib_prj\qlib_baseline
Python:        E:\anaconda_envs\qlib_env\python.exe
Qlib source:   E:\qlib_prj\qlib_clone
Qlib data:     E:\qlib_prj\qlib_data\cn_data
Derived data:  E:\qlib_prj\qlib_data\cn_data_community_20260609_derived
```

Qlib source builds may require editable installation from the local Qlib clone:

```powershell
cd E:\qlib_prj\qlib_clone
conda activate qlib_env
python -m pip install setuptools-scm
python -m pip install -e .
```

This is important on Windows because Qlib needs compiled local extensions such as
`qlib.data._libs.rolling`.

## Reproduce The Baseline

Run the validated baseline from the independent project directory, not from the
Qlib source tree:

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_baseline.ps1
```

The runner uses a project temp wrapper for Windows multiprocessing and tempfile
handling. Full qrun experiments should be run with normal local permissions instead
of a restricted sandbox.

Important baseline files:

```text
configs/workflow_lightgbm_alpha158_csi500.yaml
scripts/qrun_with_project_tmp.py
logs/qrun_lightgbm_alpha158_csi500_20260611_113628.log
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15
```

## Data Quality And Tradability

Run data-quality diagnostics:

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_data_quality.ps1 --config data_quality\config.yaml
```

Build tradability labels:

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_tradability_labels.ps1
```

The factor research module must reuse these outputs. Tradability filters are a
front-door constraint, not an optional post-processing step.

## Factor Research V3

Run the current factor research workflow:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_research_v3.py --output-dir outputs\factor_research_v3\liquid2000_core
```

Default research scope:

```text
Market:  all_stock_shsz_liquid2000
Label:   label_20d_t1
Factors: amplitude_20, std_20, rev_5, ret_20, amount_mean_20
Windows:
  main_research_2021_2023
  recent_oos_2024_2026
```

Main outputs:

```text
outputs/factor_research_v3/liquid2000_core/factor_neutralized_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_neutralized_group_return_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_ic.csv
outputs/factor_research_v3/liquid2000_core/factor_slice_group_return_summary.csv
outputs/factor_research_v3/liquid2000_core/factor_exposure_correlation.csv
outputs/factor_research_v3/liquid2000_core/factor_exposure_report.md
outputs/factor_research_v3/liquid2000_core/factor_candidate_changelog.csv
outputs/factor_research_v3/liquid2000_core/factor_research_v3_report.md
```

Large group-return detail files are skipped by default. Use `--write-detail` only
when detailed per-date/per-quantile diagnostics are needed.

## Factor Screening V3.3

Build the current factor candidate board from V3 outputs:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_screening_v3.py
```

Main outputs:

```text
outputs/factor_screening_v3/liquid2000_core/factor_candidate_board.csv
outputs/factor_screening_v3/liquid2000_core/factor_screening_report.md
```

Current default result:

```text
rev_5          research_candidate
amplitude_20   risk_exposure
std_20         risk_exposure
ret_20         watch
amount_mean_20 watch
```

## Factor Candidate Pool V3.4

Freeze the screening result into a downstream-readable candidate pool:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_candidate_pool_v3.py
```

Main outputs:

```text
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.csv
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.json
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool_report.md
```

Current roles:

```text
rev_5          alpha_candidate
amplitude_20   risk_control
std_20         risk_control
ret_20         monitor
amount_mean_20 monitor
```

Expanded V3.5 adds a small batch of reference-driven factors and writes separate
outputs under:

```text
outputs/factor_research_v3/liquid2000_expanded
outputs/factor_screening_v3/liquid2000_expanded
outputs/factor_candidate_pool_v3/liquid2000_expanded
```

Current expanded alpha candidates:

```text
rev_20_exclude_5
rev_5
```

## Caching For Faster Iteration

Factor research uses local ignored caches by default:

```text
tmp/factor_feature_cache
tmp/factor_frame_cache
```

Useful options:

```powershell
--refresh-feature-cache
--refresh-factor-cache
--no-feature-cache
--no-factor-cache
```

Use `--refresh-feature-cache --refresh-factor-cache` after updating Qlib data,
universe definitions, or base fields. Use `--refresh-factor-cache` after changing
basic factor or label calculations.

Recent smoke timing:

```text
Original profile:          about 50.4s
Raw feature cache hit:     about 11.5s-12.2s
Basic factor cache hit:    about 9.9s
```

## Point-In-Time Factor Context

Build and validate benchmark returns, historical universe membership, and listing-age context:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_factor_context_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_context_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_context_smoke.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_evaluation_context.py
```

The module reads existing Qlib provider intervals and benchmark features. It is an input to factor evaluation and does not bypass the required data-quality and tradability filters. The historical design note is archived under `docs/_archive/03_factor_research_history/FACTOR_CONTEXT_V1.md`.

## Batch Factor Evaluation V1

Before expanding the factor pool, use the catalog and batch runner to manage
source metadata, batch configs, and resumable execution:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_smoke.yaml --dry-run
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1.yaml
```

Key files:

```text
factor_research/factor_catalog.yaml
factor_research/catalog.py
scripts/run_factor_evaluation_batch_v1.py
docs/_archive/03_factor_research_history/FACTOR_BATCH_EVALUATION_V1.md
```

This layer only selects factors, generates V4 configs, and records manifests and
failed batches. IC, grouped returns, turnover, and context metrics still come
from V4 and the existing open-source evaluator adapters.

## Qlib Alpha158 Source Audit

Extract Alpha158 formulas from the local Qlib source and check whether the current
provider has all required raw fields:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha158_catalog_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_metadata_smoke.yaml --dry-run
```

Current audit result:

```text
Alpha158 formulas: 158
field_status=available: 158
first batch metadata entries: 20
```

The first 20 Alpha158 entries now have a separate runnable catalog after the
expression adapter and V4 smoke checks passed. The full 158-factor expansion is
still pending.

## Qlib Alpha158 First20 Evaluation

Build and validate the first Alpha158 expression frame:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_v1.yaml
```

Run the first20 V4 evaluation and context validation:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_alpha158_first20.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_evaluation_context.py --output-dir outputs\factor_evaluation_v4\alpha158_first20_smoke
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_alpha158_first20.py
```

Run the resumable batch version:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_first20.yaml --dry-run
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_first20.yaml
```

Current result:

```text
expression frame rows: 1,603,860
factor count: 20
adapter validation: pass
Alphalens Reloaded: pass 20
jqfactor_analyzer: partial_pass 20
Qlib eval: pass 20
context: pass 240, skipped_non_informative 80
combined metric index rows: 4,200
```

Key outputs:

```text
outputs/alpha158_expression_frame_v1/first20_main_research/
outputs/factor_evaluation_v4/alpha158_first20_smoke/
outputs/factor_evaluation_batch_v1/alpha158_first20/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml
```

The large `factor_frame.pkl` and per-batch detailed runtime outputs are ignored;
Git keeps compact manifests, summaries, validation reports, and metric indexes.

## Qlib Alpha158 Full Expansion And Screening Input

The full Alpha158 evaluation stage is complete. The project reuses the first20
results, evaluates only the remaining 138 factors, and then builds a full
Alpha158 screening input layer.

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha158_full_stage_catalogs_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_full_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_full_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_remaining138.yaml --max-batches 1
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_screening_input_v1.py --config configs\factor_screening_alpha158_full_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_judgement_v1.py --config configs\factor_judgement_alpha158_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_pool_v1.py --config configs\factor_candidate_pool_alpha158_v1.yaml
```

Current full-stage status:

```text
full158 expression frame: pass, 1,603,860 rows, 158 factors
remaining138 batch status: 13 pass, 1 skipped_existing
remaining138 strict runnable: 135
remaining138 holdout: 3
full strict runnable catalog: 155 factors
full screening input: 158 rows
strict_screening_input: 155 factors
screening holdout: 3 factors
judgement board: 158 rows
redundancy clusters: 23
strong_signal: 10
consistent_signal: 4
redundant: 55
candidate pool: 158 rows
alpha_candidate: 14
excluded_redundant: 55
excluded_high_turnover: 33
excluded_unstable_context: 16
monitor: 37
holdout: 3
```

Key outputs:

```text
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_screening_input.csv
outputs/factor_screening_alpha158_v1/full158/alpha158_full_screening_input_report.md
outputs/factor_screening_alpha158_v1/full158/alpha158_factor_correlation_top_pairs.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_board.csv
outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_report.md
outputs/factor_judgement_alpha158_v1/full158/alpha158_redundancy_clusters.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool_report.md
```

The current Alpha158 candidate pool is the default downstream alpha input. It
keeps a complete 158-row role table while exposing 14 `alpha_candidate` factors
for the next portfolio smoke stage. It is still a research input, not a trading
signal.

## Alpha158 Candidate Portfolio Smoke

Run the current interface smoke from frozen Alpha158 candidates to a
tradability-aware low-frequency portfolio:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_v1.yaml
```

Current smoke result:

```text
candidate_count: 14
warning_low_monotonicity_count: 4
trading_days: 700
executed_rebalances: 35
net_annualized_excess: 0.060632
net_excess_ir: 0.552843
average_turnover: 0.824857
```

Key outputs:

```text
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/summary.csv
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/alpha158_candidate_portfolio_smoke_report.md
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/candidate_weight_table.csv
```

This is only an interface smoke test. The high average turnover means the next
stage should add portfolio diagnostics before treating the candidate pool as a
strategy.

## Alpha158 Portfolio Diagnostics

Run the current diagnostic layer:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_v1.yaml
```

Current diagnostics:

```text
single_factor rows: 14
best single factor: alpha158_ROC30
best single factor net_excess_ir: 0.803985
topk_50 net_excess_ir: 0.676352
topk_100 net_excess_ir: 0.552843
topk_200 net_excess_ir: 0.405610
cost_20bps net_excess_ir: 0.465720
```

Key output:

```text
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/alpha158_portfolio_diagnostics_report.md
```

## Alpha158 Recent OOS

The 14 Alpha158 candidates now have a separate recent OOS expression frame and
portfolio diagnostic run for 2024-2026:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_candidate_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml --candidate-pool outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_recent_oos_v1.yaml
```

Current recent OOS result:

```text
expression rows: 1,096,231
min factor coverage: 0.995898
topk_100 net_excess_ir: 0.221295
average_turnover: 0.799286
best single factor: alpha158_VSUMN60
```

This is weaker than the 2021-2023 main result, so the next work should focus on
stability and exposure diagnostics before strategy optimization.

## Alpha158 Stability Diagnostics

Main vs recent OOS stability diagnostics:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_stability_diagnostics_v1.py --config configs\alpha158_stability_diagnostics_v1.yaml
```

Current stability result:

```text
weak_or_negative_oos: 8
positive_but_weaker_oos: 3
main_only: 2
oos_improved: 1
topk_100 net_excess_ir delta: -0.331548
bucket_3 exposure share delta: +0.063357
```

Key output:

```text
outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/alpha158_stability_diagnostics_report.md
```

## Factor Toolchain Readiness

Alpha158 is now treated as the validated reference pipeline, not the next
research bottleneck. Before adding hundreds of new factors, run the toolchain
readiness gate:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

Current readiness result:

```text
prefilter_policy: pass
open_source_evaluator_systems: pass
batch_runner: pass
required_output_contracts: pass
runnable_factor_inventory: pass
new_source_adapter_inventory: pass
generic_multi_source_screening: pass
generic_multi_source_judgement: pass
total_runnable: 669
new_source_runnable: 499
```

This means the Alpha158 reference path plus the promoted TA, Alpha101, and
Alpha360 non-Alpha158 sources are ready. The generic multi-source screening and
judgement contracts also pass, so the next project stage is broader diagnostics
for new-source probes and continued open-source factor expansion rather than
more Alpha158-only study.

Key output:

```text
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
```

## TA Factor Adapter And Batch Promotion

The first non-Alpha158 open-source factor source is now connected through
`bukosabino/ta`, with smoke and remaining-batch validation both complete:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_ta_factor_adapter_smoke_v1.py --config configs\ta_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\ta_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_smoke_catalog_entries_v1.py --config configs\ta_factor_smoke_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_ta_batch_catalogs_v1.py --config configs\ta_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_ta_remaining74.yaml --max-batches 15 --output-root outputs\factor_evaluation_batch_v1\ta_remaining74_batch1
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_batch_catalog_entries_v1.py --config configs\ta_factor_batch_promotion_v1.yaml
```

Current TA result:

```text
eligible TA factors: 79
excluded TA columns: 7
smoke promoted: 5
remaining batch evaluated: 74
batch promoted: 72
batch holdout: 2
combined promoted TA catalog: 77
```

The two holdout factors are `ta_volatility_bbli` and `ta_volatility_kchi`; both
passed Qlib eval but had no numeric Alphalens quantile-turnover result, so they
stay outside the runnable promoted catalog.

## Multi-Source Screening Contract

Build the generic screening input and candidate pool from Alpha158 plus promoted
TA, Alpha101, and Alpha360 factors:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
```

Current result:

```text
screening rows: 679
sources: 4
Alpha158 strict rows: 155
TA strict rows: 77
Alpha101 strict rows: 64
Alpha360 strict rows: 358
holdouts: 25
alpha candidates: 14
contract status: pass
```

TA, Alpha101, and Alpha360 promoted factors are intentionally kept as `monitor`
rows until the generic judgement layer reviews them; this avoids turning a
successful source adapter into a trading signal by accident.

## Multi-Source Judgement

Build a research judgement board on top of the multi-source screening input:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_judgement_v1.py --config configs\multi_source_judgement_v1.yaml
```

Current result:

```text
judgement board rows: 679
research candidates: 342
new-source alpha probes: 328
TA probes: 15
Alpha101 probes: 14
Alpha360 probes: 299
contract status: pass
```

`new_source_alpha_probe` is a research queue, not a default downstream model or
portfolio input. Alpha158 keeps the existing 14 `alpha_candidate` rows; promoted
TA, Alpha101, and Alpha360 factors can only become probes until broader
validation is added.

## New-Source Probe Diagnostics

Run the first diagnostics layer for the 328 new-source alpha probes:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_diagnostics_v1.py --config configs\new_source_probe_diagnostics_v1.yaml
```

Current result:

```text
all probes: 328
frame diagnostics selected: 120
portfolio smoke selected: 50
correlation pairs: 200
portfolio smoke executed rebalances: 4
new_source_probe_diagnostics: pass
```

The smoke portfolio is only an interface and risk diagnostic. It found very high
redundancy among several TA / Alpha101 factors and material tradability-proxy
exposure for some probes, so the next work should prioritize redundancy and
exposure review before model training.

The first probe review layer is also complete:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_review_v1.py --config configs\new_source_probe_review_v1.yaml
```

Current review result:

```text
review rows: 328
redundancy pairs: 200
redundancy groups: 4
tradability exposure watchlist: 19
strict OOS extension candidates: 3
new_source_probe_review: pass
```

The strict candidates are `alpha360_HIGH36`, `alpha360_HIGH37`, and
`alpha360_HIGH40`. They are still research candidates only.

Their strict recent-OOS extension is now complete:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_strict_oos_recent_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_strict_oos_recent.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_extension_v1.py --config configs\alpha360_strict_oos_extension_audit_v1.yaml
```

Strict-OOS result:

```text
recent OOS factor frame rows: 286,944
min coverage: 0.996236
V4 batches: 1 pass
metric index rows: 54
alpha360_strict_oos_extension: pass
```

The three factors still have positive recent-OOS mean IC, but this is a
diagnostic result only, not training admission or a strategy conclusion.

The main-vs-recent stability audit is also complete:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_stability_v1.py --config configs\alpha360_strict_oos_stability_v1.yaml
```

Stability result:

```text
metric pairs: 54
recent Alphalens mean IC min: 0.063736
recent Qlib information ratio min: 5.025121
signal sign flips: 0
alpha360_strict_oos_stability: pass
```

The 19 tradability exposure watchlist probes have also been attributed:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_tradability_exposure_attribution_v1.py --config configs\tradability_exposure_attribution_v1.yaml
```

Attribution result:

```text
watchlist rows: 19
primary proxy: liquidity_value for all 19
holdout before/residualization actions: 14
manual review: 4
residualization candidate review: 1
tradability_exposure_attribution: pass
```

The FactorTest-style exposure data capability audit is complete:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\audit_exposure_data_capability_v1.py --config configs\exposure_data_capability_audit_v1.yaml
```

Capability result:

```text
reference industry/size/Barra design: available
project context/tradability/data_quality: available
provider size fields: missing
provider industry fields: missing
provider Barra fields: missing
exposure_data_capability_audit: pass
```

So the next neutralization step should not jump straight to industry/Barra
neutralization; it needs external industry/market-cap data or a smaller
liquidity residualization path first.

Key output:

```text
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_DIAGNOSTICS_V1.md
docs/_archive/06_probe_and_tradeability_audits/NEW_SOURCE_PROBE_REVIEW_V1.md
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_EXTENSION_V1.md
docs/_archive/06_probe_and_tradeability_audits/ALPHA360_STRICT_OOS_STABILITY_V1.md
docs/_archive/06_probe_and_tradeability_audits/TRADABILITY_EXPOSURE_ATTRIBUTION_V1.md
docs/_archive/06_probe_and_tradeability_audits/EXPOSURE_DATA_CAPABILITY_AUDIT_V1.md
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostics_report.md
outputs/new_source_probe_review_v1/current/probe_review_report.md
outputs/alpha360_strict_oos_extension_v1/current/alpha360_strict_oos_extension_report.md
outputs/alpha360_strict_oos_stability_v1/current/alpha360_strict_oos_stability_report.md
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_report.md
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_report.md
```

## Alpha101 Source Audit And Adapter Smoke

Alpha101 now uses KunQuant as the primary formula source. The source audit
confirmed 82 available formulas. After smoke validation, the full candidate batch
promoted 64 Alpha101 factors and held out 18:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha101_sources_v1.py --config configs\alpha101_source_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\alpha101_factor_evaluation_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_smoke_catalog_entries_v1.py --config configs\alpha101_factor_smoke_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha101_batch_catalogs_v1.py --config configs\alpha101_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_batch82_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha101_candidate71.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_batch_catalog_entries_v1.py --config configs\alpha101_factor_batch_promotion_v1.yaml
```

Current result:

```text
KunQuant all_alpha entries: 82
Ginkgo runnable implementation files: 0
Alpha101 metadata catalog entries: 82
smoke selected factors: 5
batch adapter eligible factors: 76
adapter holdout: 6
V4 batch candidates: 71
batch promoted: 59
V4 batch holdout: 12
combined Alpha101 promoted catalog: 64
combined Alpha101 holdout catalog: 18
```

The generated metadata catalog remains non-runnable by default. Only the
promoted catalog is enabled/runnable. Alpha101 promoted rows stay in `monitor`
inside the screening contract; the judgement layer currently marks 14 Alpha101
rows as `new_source_alpha_probe` for follow-up research.

## Open-Source Factor Expansion Audit

Audit the next factor/data sources before writing another adapter:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_open_source_factor_expansion_v1.py --config configs\open_source_factor_expansion_audit_v1.yaml
```

Current result:

```text
candidates: 8
direct_adapter_next: qlib_alpha360
data_audit_next: factortest_exposure_diagnostics
reference-only candidates: GPL or unknown-license sources
```

This keeps expansion open-source-first without importing unsafe code. Qlib
Alpha360 has now completed the direct-adapter path; FactorTest-style
industry/style exposure diagnostics should start with a data capability audit.

## Qlib Alpha360 Batch Promotion

Alpha360 now has a source audit, adapter smoke, V4 smoke, full 358-factor batch
V4, promotion/holdout, and multi-source integration path:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_catalog_v1.py --config configs\alpha360_catalog_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_smoke_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358_execution.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha360_batch_catalog_entries_v1.py --config configs\alpha360_factor_batch_promotion_v1.yaml
```

Current result:

```text
Alpha360 formulas: 360
missing provider fields: 0
smoke catalog entries: 24
smoke frame rows: 88,797
batch candidates: 358
batch manifests: 72
metric index rows: 6,444
batch promoted: 358
adapter holdouts: 2
multi-source Alpha360 probes: 299
readiness alpha360 contracts: pass
```

Alpha360 V4 smoke ran on the 22 non-constant smoke factors:

```text
Alphalens Reloaded: 22 pass
Qlib eval: 22 pass
jqfactor_analyzer: 22 partial_pass
open_source_metric_index rows: 396
context_metric_index rows: 4,224
```

The jqfactor partial status is recorded without changing the open-source metric
definitions. Full Alpha360 batch V4 then evaluated the 358 non-holdout factors:

```text
Alphalens Reloaded: 358 pass
Qlib eval: 358 pass
jqfactor_analyzer: 358 partial_pass
batch promoted: 358
V4 batch holdout: 0
adapter holdout: alpha360_CLOSE0, alpha360_VOLUME0
```

The two adapter holdouts are `alpha360_CLOSE0` and `alpha360_VOLUME0`.
The promoted catalog is enabled/runnable, but Alpha360 rows remain research
probes after judgement until correlation, exposure, stability, OOS, and
portfolio-smoke diagnostics are added.

Key output:

```text
docs/_archive/05_open_source_factor_batches/ALPHA360_BATCH_PROMOTION_AND_MULTI_SOURCE_V1.md
outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml
outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/alpha360_candidate358_metric_index.csv
```

## Open-Source References

The factor research design intentionally borrows stable ideas from open-source
projects instead of reinventing every component:

- `microsoft/qlib`: data, model workflow, cross-sectional normalization concepts.
- `alphalens-reloaded`: IC, Rank IC, ICIR, group return, turnover evaluation style.
- `JoinQuant/jqfactor_analyzer`: A-share single-factor workflow organization.
- `jltxzxy/FactorTest`: exposure correlation, neutralization, and slice diagnostics.
- `bukosabino/ta`: lightweight MIT-licensed technical indicator reference for
  volatility, momentum, and volume formulas.
- `Menooker/KunQuant`: Apache-2.0 expression engine reference for future large
  factor-batch performance work.

Reference notes are documented in:

```text
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_ALGORITHM_AUDIT.md
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_V3_REFERENCE_SURVEY.md
docs/_archive/03_factor_research_history/FACTOR_RESEARCH_V3_1_PLAN.md
docs/_archive/03_factor_research_history/FACTOR_EXPANSION_V3_5_REFERENCE_SURVEY.md
```

## Development Notes

- Follow `AGENTS.md` and the personal research roadmap for current scope and evidence
  boundaries.
- Never use information after decision time; forward prediction must not read labels.
- Keep train, validation, and test/holdout isolated. `split_003` is observed and may
  be diagnosed, not reused for tuning or called a new OOS result.
- Preserve Strategy V1 history when a future Strategy V2 is introduced.
- Reuse existing modules and keep new research engineering lightweight by default.
- Prefer compact summary outputs in Git; keep large scratch artifacts under `tmp/`.
- Run full Qlib experiments with normal local permissions on Windows.

## Key Documents

```text
docs/DOC_INDEX.md
docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md
docs/PROJECT_CONTEXT_SUMMARY.md
docs/SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md
docs/STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md
docs/FACTOR_RESEARCH_TOOLCHAIN_READINESS_V1.md
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1_PLAN.md
docs/ENVIRONMENT.md
docs/BASELINE_REPRODUCIBILITY.md
docs/DATA_SOURCE_DECISION.md
docs/UNIVERSE_POLICY.md
docs/TRADABILITY_LABEL_LAYER.md
docs/_archive/README.md
```
