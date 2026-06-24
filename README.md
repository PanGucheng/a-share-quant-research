# Qlib A-Share Research Baseline

This repository is a local, reproducible A-share quant research workspace built around
[Microsoft Qlib](https://github.com/microsoft/qlib). It started as a validated
LightGBM + Alpha158 baseline and is now being extended into a beginner-friendly
research framework with data diagnostics, tradability constraints, factor research,
and factor screening tools.

Chinese documentation is available in [README.zh-CN.md](README.zh-CN.md).

> This project is for research and education only. It is not investment advice and
> does not contain live trading code.

## Current Direction

The project keeps Qlib as the main data and model backbone while adding independent
research modules around it:

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
- **Future portfolio backtest layer**: planned downstream consumer of screened
  factor candidates.

The current development priority is to improve the factor research and screening
toolchain before adding more models or strategy tuning.

## Repository Layout

```text
configs/          Qlib qrun workflow configs.
data_quality/     Data-quality diagnostic module.
tradability/      Tradability label builder and reports.
factor_research/  Factor evaluation, preprocessing, neutralization, and reports.
scripts/          Reproducible command-line runners and summaries.
docs/             Development plans, audits, reference surveys, and design notes.
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

The module reads existing Qlib provider intervals and benchmark features. It is an input to factor evaluation and does not bypass the required data-quality and tradability filters. See `docs/FACTOR_CONTEXT_V1.md` for time semantics and known listing-date limitations.

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
docs/FACTOR_BATCH_EVALUATION_V1.md
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

Alpha158 entries are still `runnable: false`. They are audited metadata sources
until the Qlib expression adapter is implemented and smoke-tested.

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
docs/FACTOR_RESEARCH_ALGORITHM_AUDIT.md
docs/FACTOR_RESEARCH_V3_REFERENCE_SURVEY.md
docs/FACTOR_RESEARCH_V3_1_PLAN.md
docs/FACTOR_EXPANSION_V3_5_REFERENCE_SURVEY.md
```

## Development Notes

- Keep Qlib baseline, data quality, tradability, and factor research decoupled.
- Do not bypass tradability labels in factor evaluation.
- Prefer compact summary outputs in Git; keep large scratch artifacts under `tmp/`.
- Add new factors only after the evaluation and screening toolchain is stable.
- Run full Qlib experiments with normal local permissions on Windows.

## Key Documents

```text
docs/DEVELOPMENT_PLAN.md
docs/ENVIRONMENT.md
docs/BASELINE_REPRODUCIBILITY.md
docs/TRADABILITY_LABEL_LAYER.md
docs/PROVIDER_DATA_CAPABILITY_V3_6.md
docs/FACTOR_CONTEXT_V1.md
docs/FACTOR_BATCH_EVALUATION_V1.md
docs/ALPHA158_CATALOG_AUDIT_V1.md
docs/STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md
docs/PROJECT_CONTEXT_SUMMARY.md
```
