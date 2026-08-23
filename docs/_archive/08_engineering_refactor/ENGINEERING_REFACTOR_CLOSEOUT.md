# Engineering Refactor Closeout

> Status: **CLOSED**
>
> Final green baseline: `b46b4f614f3be5388bf7a26ebf2b035d14906f5f`
>
> Closed on: 2026-08-09

This document is the authoritative closeout for the Phase 0–6 engineering refactor.
It records the engineering foundation that remains in force; it is not a Phase 7 and
does not authorize more repository restructuring.

## Final Outcome

The refactor reduced current development friction without changing the frozen
research or strategy:

- Phase 0 established current-pipeline, architecture, output, and implementation
  boundaries.
- Phase 1 added portable Project Settings, editable packaging, atomic text/JSON I/O,
  and `qlib-doctor`; runtime interpreter identity remains separate from project paths.
- Phase 2 migrated the five active Forward Track commands while retaining legacy
  wrappers.
- Phase 3A decomposed Daily Update behind its compatibility facade and passed
  Regression Gate A.
- Phase 3B decomposed Forward state, binding, prediction, and mature-label handling
  behind the existing facade and passed Regression Gate B.
- Phase 4 made future runtime outputs ignored by default, kept official Forward
  evidence on an explicit allowlist, and preserved every historically tracked
  output/artifact.
- Phase 5 hardened only the three approved weak caches with layered fingerprints and
  Parquet sidecars; Matrix v4, raw snapshot manifests, and lineage were untouched.
- Phase 6 unified local and CI quality commands into `fast`, `full`, and `qlib` tiers
  with a deliberately finite Ruff scope.

The CI follow-up at `b46b4f6` removed a fresh-checkout-only test dependency on ignored
Forward runtime state. GitHub Actions run
[`research-validation-ci #267`](https://github.com/PanGucheng/qlib-baseline/actions/runs/31300114400)
completed successfully. That old URL is intentionally retained as a historical run
link from before the repository rename.

## Repository Identity Maintenance

After the engineering and documentation closeouts, the same GitHub repository
(`repository_id=1265754497`) was renamed from `PanGucheng/qlib-baseline` to
[`PanGucheng/a-share-quant-research`](https://github.com/PanGucheng/a-share-quant-research).
This was repository identity and branding maintenance only; it did not reopen the
refactor or create a Phase 7.

The display names are `A-Share Quant Research` and `A 股量化研究框架`. Microsoft Qlib
remains the primary underlying framework. The Python distribution `qlib-baseline`,
the import package `qlib_baseline`, existing CLI names, local directory
`E:/qlib_prj/qlib_baseline`, and historical evidence remain unchanged.

The retired repository name `PanGucheng/qlib-baseline` must not be recreated under
the same owner. Recreating it could break GitHub redirects for old repository, issue,
commit, PR, and Actions URLs.

## Current Engineering Authority

Read these documents for present work:

1. [CURRENT_PIPELINE.md](../../CURRENT_PIPELINE.md) — active/frozen/closed entry points and
   commands.
2. [ARCHITECTURE.md](../../ARCHITECTURE.md) — domain boundaries and dependency direction.
3. [OUTPUT_POLICY.md](../../OUTPUT_POLICY.md) — runtime, artifact, report, cache, and Forward
   evidence placement.
4. [CI_POLICY.md](../../CI_POLICY.md) — local/CI quality tiers and path classification.
5. [ENVIRONMENT.md](../../ENVIRONMENT.md) — local settings, doctor, and verified runtime.

The implementation plan and original open-ended guide are historical inputs under
[`docs/_archive/08_engineering_refactor/`](README.md). They no
longer override the current documents above.

## Supported Commands

```powershell
qlib-doctor --strict
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

The active Forward commands remain:

```text
qlib-daily-update
qlib-forward-predict
qlib-forward-label-update
qlib-paper-portfolio
qlib-forward-status
```

Exact arguments and time/evidence rules remain in
[CURRENT_PIPELINE.md](../../CURRENT_PIPELINE.md).

## Frozen Boundaries

This closeout did not and does not authorize:

- model training, factor selection, hyperparameter search, or historical backtest
  reruns;
- changes to Strategy V1, Forward evidence, Matrix v4, raw snapshot manifests, or
  research lineage;
- a `src/` migration, all-repository Ruff/formatting, or mass `sys.path` cleanup;
- deleting, moving, or untracking historical outputs/artifacts;
- treating `split_003` as a fresh holdout.

Tracked output and artifact sets were unchanged throughout the refactor. The final
quality baseline was Ruff pass, 388 pytest tests, 25/25 compact/synthetic validators,
and 6 Qlib synthetic runtime tests, with four pre-existing Qlib warnings.

## Change Rule After Closeout

There is no implicit Phase 7. Future work starts from the current documents and must
have a concrete research or maintenance objective. A new structural change requires
its own scoped proposal, cost/risk justification, validation, and explicit user
authorization. Closed plans may be consulted as evidence but must not be resumed by
default.
