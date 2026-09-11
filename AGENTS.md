# Repository Working Agreement

## Project Positioning

`A-Share Quant Research`（`A 股量化研究框架`）is a personal,
research-first China A-share quantitative research project. Microsoft Qlib is the
primary underlying framework, not the identity of the project. This repository is
not an institutional platform, compliance system, production trading service, or
large-team financial infrastructure project.

Optimize work in this order:

1. research logic correctness;
2. prevention of future-data leakage;
3. protection of test/holdout evidence from repeated tuning;
4. interpretability and maintainability;
5. useful automation and proportionate governance.

The first three priorities are strict. Apply a personal-project cost/benefit test to
everything else.

## Non-Negotiable Research Rules

- No factor, feature, universe, preprocessing step, model input, or trading decision
  may use information unavailable at its decision time.
- Forward prediction must not read future labels. Label evaluation is a separate
  operation and may run only after labels mature.
- Keep train, validation, test/holdout, and forward evidence time-isolated. Test or
  observed historical results may support diagnosis, never iterative selection.
- `split_003` has been observed. It may not be used to retune factors, models,
  TopK, rebalance frequency, or portfolio rules and then be described as fresh OOS.
- Preserve Strategy V1 predictions, decisions, positions, trades, and NAV. They are
  append-only evidence and may not be overwritten because later analysis disagrees.
- Strategy V2 requires a separately authorized protocol, a new freeze date, and new
  forward evidence. Historical diagnosis alone does not authorize it.
- Fail loudly on future-data access, invalid date ordering, schema/feature mismatch,
  complete data absence, impossible trading dates, or broken portfolio accounting.
  Limited non-critical coverage gaps may be warnings when the limitation is explicit.

## Current Authority And Research Boundary

New Dataset / Research Protocol work must use the canonical research dataset:

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

It covers `2010-01-29` through `2026-06-09`, contains 774 Factor Universe V2
definitions, and qualifies 765 for research use while keeping 9 blocked. Read its
effective-date and lineage contract in `docs/CANONICAL_RESEARCH_DATASET.md`.
The old frozen Matrix, partial extension, and lineage-resolved intermediate Matrix
are immutable historical evidence, not default inputs for new research.

Current stage boundary:

```text
Forward Track                         ACTIVE / time-priority
Strategy V1                          FROZEN
Historical Data Engineering          CLOSED
Canonical Research Dataset           READY / authority
Long-History Robust Core Selection   ACTIVE RESEARCH MAINLINE / PHASE 0 CLOSED
Phase 0 Backward Replication         CLOSED / COMPLETED
Phase 1 Feature Quality Gate         COMPLETE / MVP quality scope
Primary 20D Screening MVP            COMPLETE / STOP FOR HUMAN REVIEW
Structured ML                        NOT AUTHORIZED
Strategy V2                          NOT AUTHORIZED
```

On 2026-09-09 the user separately authorized Research Protocol V3-MVP P0-P2 in
`docs/RESEARCH_PROTOCOL_V3_MVP_PLAN.md`: annual calendar assignments, development-only
feature/label-availability audits, and fixed-model engineering canaries. These bounded
canary fits are authorized; P3 feature-pool competition, recent diagnostic replay,
and Strategy V2 remain outside that authorization. Resume from
`reports/research_protocol_v3_mvp/IMPLEMENTATION_PROGRESS.md`.

The user subsequently requested a complete audit of commits `0c4b041`, `948d2f0`,
and `9f201e2` and fresh recomputation of their results. Fresh P0-P2 results and both
494-column engineering canaries are now verified in the V3 REPORT.md; old wide-run
qualification claims remain withdrawn. P3 is still not authorized. Preserve all original run
directories and receipts; never repair a contract mismatch by rewriting a receipt.

The user subsequently authorized Broad494 then Strict332 model/prediction precompute
for all nine annual folds 2015–2023, using the f2f3fc3 float64 Sequence authority,
followed by independent saved-model prediction replay. This is a bounded exception
for fixed-model precomputation, not outcome evaluation or pool competition. No
2024+ value access is permitted. Long execution is user-run only; see
`docs/V3_PREDICTION_PRECOMPUTE_RUNBOOK.md` for commands and verification limits.

On 2026-09-10 the user authorized committing the revised literature representation
plan, then implementing D1. Plan revision is committed as `b877ad3`. D1 may inspect
formula/lineage metadata and development-only feature structure, build diagnostic
R/C/H recipes, and validate against an independent synthetic/naive oracle. It may
not train R/C/H models, read sealed outcomes, or access 2024+ research values.
Long structural scans are user-run. A passing implementation/canary does not
finalize rank/missing policy or authorize D2; resume from
`reports/literature_factor_representation_d1/REPORT.md`.

The user authorized the narrowed implementation in
`docs/LONG_HISTORY_MULTI_EVALUATOR_SCREENING_MVP_PLAN.md` on 2026-09-07.
Primary 20D V0 was delivered on 2026-09-08; see
`reports/long_history_multi_evaluator_screening_v1/REPORT.md`. Stop for human review. Recent diagnostic,
Core/portfolio construction and model training are outside this MVP.

The prior Research Protocol V2 is frozen historical evidence. Later validation
study showed that its short development environments are not sufficient selection
authority for formal Structured ML. Do not run model competition from that protocol
without a separately authorized later protocol. The current historical research
mainline is the long-history robust core-factor route; all of its 2010–2026 results
are retrospective development evidence and do not change Strategy V1.

## Documentation Navigation

For a new session, read only what the task needs, starting with:

1. `docs/PROJECT_CONTEXT_SUMMARY.md` for compact current context;
2. `docs/CURRENT_PIPELINE.md` for ACTIVE/FROZEN/CLOSED/NEXT status and commands;
3. the directly relevant authority document.

Task-specific authorities:

- canonical dataset: `docs/CANONICAL_RESEARCH_DATASET.md`;
- current historical research mainline:
  `docs/LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md`;
- first implementation unit:
  `docs/LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md`;
- research roadmap: `docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md`;
- documentation map: `docs/DOC_INDEX.md`;
- architecture: `docs/ARCHITECTURE.md`;
- outputs and evidence: `docs/OUTPUT_POLICY.md`;
- environment: `docs/ENVIRONMENT.md`;
- local/CI checks: `docs/CI_POLICY.md`;
- active operational contracts: `docs/operations/`.

`docs/_archive/`, historical reports, and preserved outputs are evidence to inspect
on demand. Their commands and “next steps” are not current instructions. A filename
or output directory containing `current` also does not by itself make a stage active.

## Engineering And Change Discipline

- Read the relevant current docs, implementation, tests, and recent changes before
  modifying an established workflow. Confirm whether it is ACTIVE, FROZEN, CLOSED,
  historical, or experimental.
- Reuse existing factor, model, Qlib execution, validation, and Forward modules.
  Prefer the smallest change that answers the current question.
- Preserve manifests, lineage, receipts, frozen artifacts, and historical evidence.
  Never overwrite formal Forward evidence for an equivalence test; use synthetic
  fixtures, temporary directories, or an explicit dry run.
- New research defaults to ordinary Python functions or small classes, YAML,
  CSV/JSON, Markdown, figures, Git, and focused tests.
- Do not add a manager, registry, manifest, protocol, gate, adapter, validator, or
  abstraction unless a concrete current problem cannot be solved more simply.
- Avoid speculative services, distributed monitoring, broker gateways, failover,
  live-trading infrastructure, or broad directory migrations without authorization.
- Do not perform unrelated research, artifact cleanup, or broad governance changes
  as a side effect of a scoped task.
- Tests should target high-risk semantics: time alignment, no look-ahead, split
  isolation, membership provenance, benchmark alignment, schema order, and portfolio
  arithmetic. Do not optimize for test count.

Before handoff, review the complete diff, confirm frozen/current boundaries, run the
proportionate tests, and check documentation links when docs changed. State what was
reused, changed, deliberately not done, and whether any conclusion may influence a
future strategy version.

## Default Git Workflow

This is a personal research repository. Ordinary research implementation, bug fixes,
documentation, and small refactors default to:

```text
main → edit → proportionate local/CI checks → review full diff → commit → push
```

A feature branch or pull request is optional and should be used when the work is a
large or high-risk refactor, requires long-lived parallel experiments, preserves two
competing research routes, may damage frozen/Forward/canonical authority, or the user
explicitly requests branch/PR isolation. Removing branch protection does not weaken
the correctness, immutability, testing, diff-review, or evidence-boundary rules above.

2026-09-10: The user authorized evaluation and implementation of the D1 freeze and
D2 R218/C201/H358 fixed-model precompute proposal. Formal approval is recorded in
reports/literature_factor_representation_d1/freeze_v1/freeze.json. This supersedes
the earlier D1-only boundary for these 27 annual models and independent replay.
Long execution remains user-run. Outcomes, pool comparison and 2024+ values remain closed.

2026-09-11: User-run D2 completed. All 27 R/C/H models and independent saved-model
replays are verified; each arm is all_nine_exact and all five arms remain sealed.
See reports/literature_factor_representation_d2/COMPLETION_REPORT.md. No rerun is
needed; D3/outcomes, pool performance comparison and 2024+ values remain unauthorized.

2026-09-11: The user subsequently authorized assessment, planning and implementation
of D3-A frozen five-arm prediction evaluation. This is a bounded new exception:
paired prediction/label evaluation for mature 2015-2023 dates only, under the unchanged
six-contrast D1 evaluation contract. See docs/LITERATURE_D3A_FROZEN_PREDICTION_EVALUATION_PLAN.md
and docs/LITERATURE_D3A_EVALUATION_RUNBOOK.md. Implementation is outcome-blind; the
formal long run remains user-run. Preserve all D1/D2 identities, models and receipts.
The append-only reports/literature_factor_representation_d3a/OUTCOME_OPENED.json is
the authority for whether D3-A has unsealed, including failed runs. Do not create
new run ids or remove failure evidence to bypass that marker. D3-B, portfolios,
SHAP, tuning, Strategy V2 and 2024+ research values remain unauthorized.

2026-09-11: User-run D3-A completed and postrun verification passed. All 2,168
mature score dates are scoreable on 4,144,939 common pairs. None of the six fixed
HAC20/Holm contrasts rejects zero difference; this is not equivalence or noninferiority.
See reports/literature_factor_representation_d3a/COMPLETION_REVIEW.md. Outcome opening
at 2026-09-11T02:25:42 UTC is permanently recorded. Preserve sealed result bytes and
stop for human review; no rerun or outcome-driven representation/model changes.
D3-B, portfolios, SHAP, tuning, Strategy V2 and 2024+ research values remain closed.

2026-09-11: The user requested assessment and planning for Economic Translation MVP,
with permission to correct the supplied proposal. See docs/ECONOMIC_TRANSLATION_MVP_PLAN.md.
This authorizes literature, source-code and metadata audit plus documentation only.
Plan delivered; E1 prediction persistence, E2/E3 execution/strategy implementation,
and E4 portfolio outcomes are not yet authorized. Proposed B494/monthly/buffer
choices are reviewable recommendations, not executable frozen strategy authority.
No 2024+ research values, Strategy V2 or changes to frozen D1/D2/D3 artifacts.

2026-09-11: The user subsequently authorized assessment of the revision memo, a
separate plan commit, then E1 prediction-only structural implementation and E2
execution/data readiness, including bounded real diagnostics and quote verification.
See docs/ECONOMIC_TRANSLATION_MVP_PLAN.md. B494 only; one structural 10/20 candidate.
Long scans remain user-run. E2 may end blocked by data/execution gaps. E3 freeze,
E4/portfolio outcomes, 2024+ values and changes to frozen D1/D2/D3 remain forbidden.
Stop after E1/E2 evidence and report for human review.
