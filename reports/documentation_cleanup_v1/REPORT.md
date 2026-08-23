# Documentation Cleanup V1

## Outcome

Repository documentation now has one navigation authority (`docs/DOC_INDEX.md`), a
compact new-session context, a present-state pipeline, and a roadmap whose next
research area is Factor Universe / Data Capability Upgrade. This was documentation-
only governance: no research code, configuration, runtime output, frozen artifact,
historical evidence, or Forward evidence was changed.

## Inventory And Decisions

- Reviewed the 118 tracked governance-scope Markdown documents present at task start:
  `AGENTS.md`, both root READMEs, 15 current `docs/` files, 95 archive files, and five
  report entry/final-report files.
- Classified `docs/` root as current authority or operational reference, `reports/`
  as compact final evidence, and `docs/_archive/` as historical plans/provenance.
- Archived one completed tracked implementation plan:
  `ML_FEATURE_POOL_POLICY_EXPERIMENT_PLAN.md`.
- Deleted no historical plan and no research evidence. No reports were merged because
  the four recent stages have distinct scientific or engineering responsibilities.
- The pre-existing untracked performance-task document was preserved unchanged and
  excluded from this commit.

## Current Authority Refresh

- `DOC_INDEX`, `PROJECT_CONTEXT_SUMMARY`, `CURRENT_PIPELINE`, and the roadmap now mark
  ML Feature Pool MVP V1, Performance Optimization V1, Research Productivity V1, and
  Clustering Ablation V1 as CLOSED.
- Current docs carry only compact conclusions and link to final reports for numbers.
- Fast Research is explicitly screening-only; Clustering Ablation is mixed and does
  not change the representative gate.
- Strategy V1 and Forward Track boundaries remain frozen/append-only.
- Both READMEs carry the same concise current status.
- Stale `Next Action` wording in the data-source and universe policies was converted
  to historical completion status without rewriting historical evidence.

## Validation And Remaining Debt

Validation results:

- repository-wide local-link and `DOC_INDEX` audit: 560 Markdown files, zero issues;
- `python scripts/check_quality.py fast`: Ruff passed and 45 tests passed;
- `python scripts/check_quality.py full`: 411 tests passed with four existing Qlib
  empty-slice warnings, followed by all 25 compact/synthetic validators passing;
- `git diff --check`: passed.

Remaining debt is intentionally small: many archived early plans retain period-
accurate language and absolute paths. They are preserved as provenance and are not
current instructions. The untracked local performance-task document remains the
owner's file and may be archived separately only if the owner later chooses to track
it.
