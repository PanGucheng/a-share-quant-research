# Repository Working Agreement

## Project Positioning

This is a personal A-share quantitative research project for learning factor,
machine-learning, portfolio, and forward research with Qlib and Codex. It is not an
institutional research platform, compliance system, production trading service, or
large-team financial infrastructure project.

Optimize work in this order:

1. research logic correctness;
2. prevention of future-data leakage;
3. protection of test/holdout evidence from repeated tuning;
4. interpretability;
5. maintainability;
6. automation;
7. engineering audit and governance.

The first three priorities are strict. Apply a personal-project cost/benefit test to
the rest.

## Non-Negotiable Research Rules

- No factor, feature, universe, preprocessing step, model input, or trading decision
  may use information unavailable at its decision time.
- Forward prediction must not read future labels. Label evaluation is a separate
  operation and may run only after labels mature.
- Keep train, validation, and test/holdout periods time-isolated. Use test only for
  final evaluation, never for iterative selection.
- `split_003` has already been observed. It may be used for diagnosis, but must not
  be used to retune factors, LightGBM, TopK, rebalance frequency, or portfolio rules
  and then be described as new OOS/holdout evidence.
- A Strategy V2 informed by observed history requires a new freeze date and new
  forward evidence. Preserve Strategy V1 predictions, positions, trades, and NAV;
  never overwrite a prior strategy version because it underperformed.
- Stop on correctness failures such as future-data access, invalid date ordering,
  feature-count/schema mismatch, complete data absence, impossible trading dates,
  or broken portfolio accounting.
- For limited non-critical coverage gaps, missing industry classifications, or a
  few unavailable exposures, prefer a warning plus an explicit report limitation.

## Engineering Rules

- Reuse existing factor, model, Qlib execution, backtest, and forward modules and
  outputs. Read the relevant README, docs, recent results, and recent commits before
  changing an established workflow.
- Preserve existing manifests, validators, lineage, receipts, and frozen artifacts
  where current modules depend on them. Do not perform broad governance cleanup as
  part of unrelated research work.
- New research modules default to lightweight research engineering: ordinary Python
  functions or small classes, YAML configuration, CSV/JSON outputs, Markdown
  reports, figures, Git, and focused pytest coverage.
- Do not add a manager, registry, manifest, protocol, gate, adapter, validator, or
  abstraction unless it solves a concrete current problem that a simpler design
  cannot solve.
- Avoid parallel frameworks, speculative production abstractions, complex service
  layers, broker gateways, distributed monitoring, failover, and live-trading
  infrastructure until an approved later stage needs them.
- Fail loudly for correctness; do not turn every data-quality warning into a
  publication gate.
- Tests should cover high-risk semantics: time/date alignment, no look-ahead,
  cross-sectional IC alignment, split isolation, membership provenance, benchmark
  alignment, and portfolio arithmetic. Do not optimize for test count.

## Current Roadmap and Scope

The authoritative roadmap is `docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md`:

1. highest-priority Forward Track: Daily Data Update, frozen Strategy V1 prediction,
   and paper portfolio recording;
2. completed historical Strategy Diagnostics V1 evidence, which remains frozen and
   must not block forward data collection;
3. accumulation and evaluation of genuine prospective evidence;
4. Strategy V2 only if historical diagnostics plus forward evidence justify it;
5. shadow trading or small-capital validation much later.

Genuine forward evidence has temporal priority: historical analysis can be reproduced
later from preserved data, but a prediction or paper decision not genuinely produced
at the time cannot later be reconstructed as independent prospective evidence.

Current business priority is genuine forward evidence collection through lightweight
Daily Data Update and Forward Research work. Strategy Diagnostics V1, External PIT
Style Data V1, and the Style Attribution Extension are closed historical research
stages. Their findings may only generate hypotheses for a separately frozen Model V2
Research Protocol; they do not authorize changing Strategy V1, training Model V2,
factor selection, hyperparameter search, TopK/rebalance scans, or portfolio
optimization. Unless a proven error, leakage, contract failure, or implementation
bug is found, later work may only append clarification or open a new version/stage.

## Engineering Navigation

Before changing repository structure or an established workflow, read these current
entry documents in order:

1. `docs/CURRENT_PIPELINE.md` for active, frozen, closed, legacy, and experimental
   status plus the current run commands;
2. `docs/ARCHITECTURE.md` for domain boundaries, dependency direction, and retained
   governance responsibilities;
3. `docs/OUTPUT_POLICY.md` for runtime output, frozen artifact, report, cache, and
   Forward evidence boundaries;
4. `docs/ENGINEERING_REFACTOR_IMPLEMENTATION_PLAN.md` when implementing the staged
   engineering refactor.

The refactor is phase-gated. Implement only the phase explicitly requested by the
user, report actual changes and validation, and do not automatically enter the next
phase. If inspection shows that a planned item has materially higher compatibility,
maintenance, or research-correctness risk than expected, narrow, defer, skip, or
cancel it and record the reason instead of mechanically following the plan.

## Codex Change Discipline

- State the research question first and keep changes scoped to answering it.
- Clearly distinguish historical/post-observation diagnosis from independent
  forward evidence.
- Record limitations and mixed or inconclusive findings honestly; do not force a
  single attribution.
- Prefer modifying the smallest existing module that fits. Do not move the repository
  into the long-term target directory layout during an unrelated stage.
- Before finalizing, confirm what was reused, what changed, what was deliberately not
  done, and whether any conclusion can influence a future strategy version.
