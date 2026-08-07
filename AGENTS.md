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

1. Strategy Diagnostics;
2. Daily Data Update;
3. Forward Prediction and Paper Portfolio;
4. accumulation of genuine forward evidence;
5. Strategy V2 only after evidence identifies a concrete problem;
6. shadow trading or small-capital validation much later.

The current implementation target is Strategy Diagnostics V1. It diagnoses the
already observed LightGBM + P01 results without training, factor selection,
hyperparameter search, TopK scans, rebalance scans, or portfolio optimization.
Until the user explicitly asks implementation to resume, documentation changes do
not authorize running or building that diagnostics stage.

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
