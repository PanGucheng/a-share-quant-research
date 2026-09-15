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

2026-09-11: E1/E2 implementation delivered after separate plan commit 6464937.
E1 is IMPLEMENTED / AWAITING USER RUN, not yet real-data complete. Use only
scripts/study_economic_e1.ps1 for the authorized long structural study/replay.
E2 is BLOCKED BY EXECUTION / DATA GAP: bounded quote-unit canary and synthetic
Qlib validation do not certify full historical state, corporate actions, opening
trade evidence or executable benchmark. See reports/economic_translation_mvp/REPORT.md
and EXECUTION_CONTRACT.md there. No E3 freeze/E4 or 2024+ access. Preserve original
adapters/configs, source receipts, D1/D2/D3 and new E1/E2 evidence. Stop for review.

2026-09-12: User-run E1 nine-year B494 structural scan and independent replay completed.
Postrun hashes, bindings, closed access inventory and summary recomputation passed.
See reports/economic_translation_mvp/e1_completion_v1/REPORT.md. E1 is COMPLETE /
PREDICTION STRUCTURE VERIFIED; do not rerun or rewrite sealed outputs. E2 remains
BLOCKED by execution/data gaps; E3/E4 and 2024+ values remain unauthorized.

2026-09-12: The user authorized the E2 data-readiness closure audit, bounded real
canaries and necessary data/rule adapters. Audit completed: see reports/economic_translation_mvp/
e2_readiness_v2/REPORT.md and MATRIX.md. E2 remains BLOCKED; not READY FOR E3 FREEZE.
Preserve original E1/E2 receipts. New evidence is outputs/economic_translation_mvp/e2_closure_v1.
A SH601313 unit/identity anomaly is unresolved; do not silently rescale, drop the
security or change frozen models. Full historical states/events, held continuity,
warmup wiring, early-2015 fees and benchmark feasibility remain incomplete.
No E1 rerun, E3/E4, real NAV/outcomes, Strategy V2 or 2024+ research-value access.

2026-09-13: The user authorized the small-capital E2/E3 prerequisite study and
specified CNY 50k/100k, bilateral 0.00025 commission with CNY 5 minimum, separate
historical stamp/transfer fees, and assumed STAR/ChiNext access. Bounded score-blind
static study is complete; see reports/economic_translation_mvp/small_capital_v1/REPORT.md
and MATRIX.md. K=5 for 50k and K=8 for 100k are review candidates, not frozen strategy
parameters or certified executions. Academic benchmark definition is separate from
personal full-pool replication; raw/state/event/accounting blockers remain.
The fixed-K prediction-only check is designed and synthetically validated, not run
on real scores; select one actual AUM/K for human review first. E1 is unchanged.
Stop at E2 BLOCKED for review. No E3/E4, NAV/outcomes, B494 changes or 2024+ access.

2026-09-13: The user authorized bounded E2 Hard-Blocker Closure. See
`reports/economic_translation_mvp/e2_hard_closure_v1/REPORT.md` and its MATRIX/RUNBOOK.
Only the twenty sessions 2014-12-04 through 2014-12-31 were additionally authorized
for 2015 ADV20 warmup; all other research-value access stays within 2015-2023.
Alias unit overlay, held-gap explanations and synthetic Qlib event bridge are
verified; E2 STILL BLOCKED. Full Quotes/States/Dividends scans are user-run only.
Do not silently exclude difficult stocks, change frozen IDs/scores, or drop held
rights; prospective eligibility is a review proposal, not a new authorization.
No E1 rerun, E3/E4, real portfolio outcomes or 2024+ value access.

2026-09-14: User ran the historical scans: Quotes complete (4,416 chunks),
States 118 complete then failed at SH600143; Dividends 5 dates then interrupted.
Completed file hashes verified. Resume only via `scripts/resume_e2_hard_history.ps1`
one network phase at a time; parent receipts are immutable, new attempts append.
See the E2 hard-closure USER_RUN_20260914.md. No full recovery run by Codex.

2026-09-14: User authorized bounded automatic retries for repeated network timeouts.
The existing resume PowerShell entry now wraps unchanged hash-bound recovery code
with scripts/retry_e2_hard_history.py: up to 8 transport retries per invocation,
30/60/120-second capped waits, reconnect and preserved attempts. Validation,
permission and hash errors do not retry. Full scans remain user-run only.

States recovery inventory is now complete: 4,416 keys, 7,347,019 rows; all referenced
receipt/data hashes checked. Only SH601313 has an empty response, still requiring
identity reconciliation. Next user-run phase is Dividends; do not rerun Quotes or
States. See reports/economic_translation_mvp/e2_hard_closure_v1/STATES_COMPLETION.md.
This is inventory completion, not E2 READY or complete semantic coverage.

User increased the automatic transport retry budget to 100 per invocation.
Default and allowed maximum are now 100; delays and non-network fail-fast rules
are unchanged. Existing running processes retain their original retry budget.

Dividends recovery is complete: 2,189 dates, 28,681 records; referenced hashes
verified. All three user inventories are now complete; do not rerun them.
See reports/economic_translation_mvp/e2_hard_closure_v1/DIVIDENDS_COMPLETION.md
for non-implemented records, missing cash/listing dates and conflicting event keys.
E2 remains BLOCKED; next work is semantic reconciliation, not more stage commands.

2026-09-14: User authorized full offline semantic reconciliation of the already
sealed Quotes/States/Dividends inputs, execution overlays, event/account bridge,
independent verification and current E2 reports, followed by commit/push and stop.
See e2_hard_closure_v1/REPORT.md, MATRIX.md and SEMANTIC_RECONCILIATION.md.
No recollection or rerun of the three scans or E1. Preserve canonical/B494 and
all original receipts. E2 STILL BLOCKED; unresolved held rights, terminal/identity
continuity, raw conflicts and execution-state evidence cannot be bypassed.
Warmup/auction/early fee details are graded separately under explicit MVP scope.
No K/AUM/benchmark selection, structural search, real account/outcomes, E3/E4
or 2024+ value access. Stop after delivery for human review.

2026-09-15: User authorized assessment and implementation of E2 MVP scope
simplification. See e2_hard_closure_v1/MVP_SCOPE_SIMPLIFICATION_REVIEW.md and
current MATRIX.md. An independent PIT Entry gate may deny unheld candidates
without blocking unrelated holdings; full special-session simulation is no
longer an E2 requirement. Existing shares/receivables/bonus rights must persist.
Only exposed valuation, identity/settlement and entitlement gaps remain R1-R3
conditional account blockers. A halt or all-NO_ENTRY result is not E2 READY.
No retrospective exclusions or claims of never-held securities without evidence.
E2 STILL BLOCKED; preserve original scans/receipts, canonical/B494 and E1.
No recollection, K/AUM/benchmark selection, real outcomes/NAV, E3/E4 or 2024+
values. Commit/push scope delivery and stop for human review.

2026-09-15: User authorized the E2 Core / Strategy-Specific Path boundary review.
Current authority is e2_hard_closure_v1/STAGE_BOUNDARY_REVIEW.md and MATRIX.md.
Core and account-path readiness are separate. Stop global case-cleanup as a Core
prerequisite; R1-R3 are conditional on frozen actual exposure, not Core blockers.
Current E2 CORE PARTIAL / GENERIC INTEGRATION GAPS: C1 source-bound PIT input
adapter/bounded canary and C2 scope/Qlib session/event/valuation wiring remain open.
E2 STILL BLOCKED; existing primitives verified, real path not started. E3 freeze
preparation/parameter selection is conditional on reviewed Core Ready and was not
activated this turn. Freeze rules before constructing any real path; never change
rules to avoid triggered incidents. Target membership is not actual exposure.
Keep outcomes/metrics closed; E4 needs separate authorization. No reacquisition,
E1 rerun, frozen modifications or 2024+ values. Commit/push and stop for review.

2026-09-15: User authorized implementing and accepting C1+C2 only, without expanding
E2 scope. See e2_hard_closure_v1/CORE_IMPLEMENTATION_ACCEPTANCE.md and MATRIX.md.
C2 is CLOSED / SYNTHETIC INTEGRATION ACCEPTED: opt-in whole-day Qlib transaction,
phase-separated inputs, carry without fake quotes, and full rollback/replay.
C1 input adaptation is implemented; fixed SH600000 / 2020-08-24 source canary remains
NOT ACCEPTED because source-bound ordinary state, identity availability and event
coverage evidence is missing. E2 STILL BLOCKED solely on C1 acceptance, no new scope.
Daily market phase clocks are explicit existing MVP approximations, not source
publication timestamps; they cannot generate state/event-clearance certificates.
Do not swap the failed sample, recollect full scans, rerun E1, freeze/select strategy,
read real outcomes/2024+ or activate E3/E4. Preserve all prior evidence and stop for review.

2026-09-15: User authorized revising C1 historical availability under the supplied
Historical/Live separation memo. Current authority is CORE_IMPLEMENTATION_ACCEPTANCE.md
and MATRIX.md in e2_hard_closure_v1. C1+C2 CLOSED; E2 CORE READY / STRATEGY PATH
VERIFICATION PENDING. Historical session-effective evidence keeps known_at null;
known-event review is explicitly incomplete, not a five-family absence certificate.
Fixed SH600000 / 2020-08-24 ordinary one-day engineering canary COMMITTED; 220 tests
passed. Live receipt/freshness validation rejects historical approximations; no live
provider/execution implemented. Prior strict-PIT failure/receipts remain immutable.
Stop generic E2 infrastructure. No full R1-R3 cleanup, source recollection, E1 rerun,
B494/canonical edits, parameter selection, real strategy path, outcomes or 2024+.
Core Ready does not certify any actual strategy path. Commit/push and stop for human
review; do not auto-activate E3/E4.
