# A-Share Quant Research

Research-first quantitative research framework for the China A-share market, built
primarily with [Microsoft Qlib](https://github.com/microsoft/qlib). Qlib is the main
underlying framework, not the identity of the whole project. This repository is for
research and education; it is not a production trading service or investment advice.

Repository:
[PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)

Chinese: [README.zh-CN.md](README.zh-CN.md)

## Current Status

The time-sensitive active path is the Forward Track:

```text
Daily Data Update
        ↓
frozen 52-feature snapshot
        ↓
frozen Strategy V1 LightGBM prediction
        ↓
Top50 equal-weight paper decision
        ↓
mature-label evaluation
```

Strategy V1, historical predictions, and observed `split_003` evidence are frozen.
`split_003` may be diagnosed but must not be reused for tuning and described as fresh
OOS evidence. Model Diagnostic V1, ML Feature Pool MVP V1, Performance Optimization
V1, Research Productivity V1, Clustering Ablation V1, and the Phase 0–6 engineering
refactor are closed. Fast Research is screening-only; the clustering representative
gate remains unchanged. Factor Universe V2 is frozen as a research-only catalog of
774 factors (669 immutable V1, 19 recovered, 28 canonicalized and 58 new mature
factors). It does not authorize Strategy V2 or modify Forward Track. There is no
implicit engineering Phase 7.

Start with [docs/DOC_INDEX.md](docs/DOC_INDEX.md). The exact active commands and
machine-state paths are in
[docs/CURRENT_PIPELINE.md](docs/CURRENT_PIPELINE.md).

## Setup

The committed [configs/project.yaml](configs/project.yaml) is portable. Put local
Qlib source, provider, and Daily Update cache paths in ignored
`configs/project.local.yaml`, using
[configs/project.local.example.yaml](configs/project.local.example.yaml) as the
template.

```powershell
conda activate qlib_env
python -m pip install -e .
qlib-doctor --strict
```

The interpreter is runtime state (`sys.executable`), not a project setting. See
[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) for the verified Windows environment and
configuration precedence.

## Active Commands

```powershell
qlib-daily-update --target-date YYYY-MM-DD
qlib-forward-predict --help
qlib-forward-label-update --help
qlib-paper-portfolio --help
qlib-forward-status
```

Do not infer production arguments from this short list. Follow the cutoff, Git
binding, label-maturity, and append-only rules in
[docs/CURRENT_PIPELINE.md](docs/CURRENT_PIPELINE.md).

## Quality Commands

Local and GitHub Actions use the same tiers:

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

`fast` uses a finite Ruff scope and focused engineering tests. `full` runs complete
pytest plus the existing compact/synthetic validators. `qlib` runs synthetic Qlib
Exchange runtime tests. These commands do not download the full A-share dataset,
train models, or run historical backtests. See
[docs/CI_POLICY.md](docs/CI_POLICY.md).

## Repository Layout

```text
qlib_baseline/    Settings, atomic I/O, weak-cache helpers, and active CLIs.
daily_update/     Active Daily Update pipeline and compatibility facade.
model_research/   Frozen/forward model and paper-portfolio modules.
factor_research/  Factor evaluation and research modules.
qlib_integration/ Qlib Exchange/Executor integration.
configs/          Portable project and workflow configuration.
scripts/          Active wrappers, quality runner, validators, and historical tools.
docs/             Current authority and governance documentation.
docs/operations/  Current operational contracts used by active/frozen workflows.
docs/_archive/    CLOSED, HISTORICAL, and SUPERSEDED plans and audits.
outputs/          Runtime results plus preserved historical/Forward evidence.
artifacts/        Immutable frozen machine objects.
reports/          Compact human-readable evidence intended for Git.
tmp/              Ignored caches, downloads, references, and scratch data.
```

## Documentation Authority

- [Personal research roadmap](docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md)
- [Current pipeline](docs/CURRENT_PIPELINE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Output policy](docs/OUTPUT_POLICY.md)
- [CI policy](docs/CI_POLICY.md)
- [Documentation archive](docs/_archive/README.md)

Archived plans preserve project history but are not current execution instructions.
Existing manifests, receipts, lineage, frozen artifacts, and historical outputs remain
intact for compatibility and evidence.

## Research Boundaries

- Use only information available at decision time.
- Keep train, validation, test/holdout, and forward-label evaluation time-isolated.
- Never overwrite Strategy V1 predictions, paper decisions, positions, trades, or NAV.
- Do not interpret historical or post-observation diagnostics as production readiness.
- Prefer the smallest design that preserves research correctness and evidence
  boundaries.

The repository working agreement is [AGENTS.md](AGENTS.md).
