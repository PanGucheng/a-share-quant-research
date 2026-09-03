# A-Share Quant Research

Personal, research-first quantitative research framework for the China A-share
market, built primarily with [Microsoft Qlib](https://github.com/microsoft/qlib).
Qlib is the main underlying framework, not the identity of the project. This
repository is for research and education; it is not a production trading service or
investment advice.

Repository:
[PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)

Chinese: [README.zh-CN.md](README.zh-CN.md)

## Current Status

- **ACTIVE:** time-sensitive Forward Track — Daily Data Update, frozen Strategy V1
  prediction, paper portfolio, and mature-label evaluation.
- **FROZEN:** Strategy V1 and all historical/Forward evidence.
- **READY / AUTHORITY:** canonical research dataset for the current long-history
  factor research mainline and any later protocol work.
- **CLOSED:** Historical Data Engineering and the completed historical research stages.
- **PERFORMANCE CLOSED:** Fast `fast_research_mt_v2`; Full `full_research_accelerated_v3`.
  Phase H outer-worker benchmarking was intentionally not pursued.
- **ACTIVE RESEARCH MAINLINE / PHASE 0 CLOSED:** Long-History Robust Core Factor
  Selection V1; Phase 0 backward replication is completed and Phase 1 is not started.
- **NOT AUTHORIZED:** Structured ML, Strategy V2, and live trading.

Canonical dataset:

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

It covers `2010-01-29` through `2026-06-09`; 765 of 774 definitions are
research-usable and 9 remain blocked. The old frozen Matrix and historical
extensions remain immutable evidence, not default inputs for new research. See the
[canonical dataset authority](docs/CANONICAL_RESEARCH_DATASET.md).

The prior Research Protocol V2 is frozen historical evidence. Its short development
environments are not sufficient authority for formal Structured ML. The current
historical research mainline is the
[Long-History Robust Core Factor Selection route](docs/LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md),
not model competition; all results remain retrospective development evidence.

Start with [the documentation index](docs/DOC_INDEX.md). Exact commands and status
boundaries are in [Current Pipeline](docs/CURRENT_PIPELINE.md).

## Setup

The committed [configs/project.yaml](configs/project.yaml) is portable. Put local
Qlib source, provider, and Daily Update cache paths in ignored
`configs/project.local.yaml`; use
[configs/project.local.example.yaml](configs/project.local.example.yaml) as a template.

```powershell
conda activate qlib_env
python -m pip install -e .
qlib-doctor --strict
```

Environment details: [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md).

## Active Commands

```powershell
qlib-daily-update --target-date YYYY-MM-DD
qlib-forward-predict --help
qlib-forward-label-update --help
qlib-paper-portfolio --help
qlib-forward-status
```

Follow cutoff, Git-binding, label-maturity, and append-only rules in
[Current Pipeline](docs/CURRENT_PIPELINE.md); do not infer production arguments from
this short list.

## Quality Commands

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

These tiers do not download the full A-share dataset, train models, or run historical
backtests. Policy: [docs/CI_POLICY.md](docs/CI_POLICY.md).

## Documentation

- [Project context summary](docs/PROJECT_CONTEXT_SUMMARY.md)
- [Current pipeline](docs/CURRENT_PIPELINE.md)
- [Canonical research dataset](docs/CANONICAL_RESEARCH_DATASET.md)
- [Long-history robust core-factor route](docs/LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md)
- [Phase 0 development plan](docs/LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md)
- [Personal research roadmap](docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Output policy](docs/OUTPUT_POLICY.md)
- [Documentation index and archive map](docs/DOC_INDEX.md)

`docs/` contains current authority, `docs/operations/` contains active operational
contracts, and `docs/_archive/` plus `reports/` preserve historical evidence. Archived
plans are not current execution instructions.

The repository working agreement is [AGENTS.md](AGENTS.md).
