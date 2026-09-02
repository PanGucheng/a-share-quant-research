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
Long-History Robust Core Selection   ACTIVE RESEARCH MAINLINE / PLANNING
Phase 0 Backward Replication         READY FOR IMPLEMENTATION / NOT STARTED
Structured ML                        NOT AUTHORIZED
Strategy V2                          NOT AUTHORIZED
```

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
