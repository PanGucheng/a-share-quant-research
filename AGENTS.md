# Repository Working Agreement

## Project Positioning

`A-Share Quant Research`（`A 股量化研究框架`）is a personal, research-first
China A-share quantitative research project for learning factor, machine-learning,
portfolio, and forward research with Qlib and Codex. Microsoft Qlib is the primary
underlying framework, not the identity of the whole project. This is not an
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

ML Feature Pool MVP V1, Performance Optimization V1, Research Productivity V1, and
Clustering Ablation V1 are also CLOSED. Their preserved reports are diagnostic or
engineering evidence, not Strategy V2 authorization. Fast Research is screening-only,
and the one-representative clustering gate remains unchanged after mixed historical
evidence. The next historical research area, when separately authorized, is a
high-level Factor Universe / Data Capability Upgrade; no V2 implementation plan is
implied by this roadmap entry.

## Engineering Navigation

Before changing repository structure or an established workflow, read these current
entry documents in order:

1. `docs/CURRENT_PIPELINE.md` for active, frozen, closed, legacy, and experimental
   status plus the current run commands;
2. `docs/ARCHITECTURE.md` for domain boundaries, dependency direction, and retained
   governance responsibilities;
3. `docs/OUTPUT_POLICY.md` for runtime output, frozen artifact, report, cache, and
   Forward evidence boundaries;
4. `docs/CI_POLICY.md` for the shared local/CI quality tiers.

The Phase 0–6 engineering refactor is closed at
`b46b4f614f3be5388bf7a26ebf2b035d14906f5f`. There is no implicit Phase 7. Its
closeout, implementation plan, and original guide are historical evidence under
`docs/_archive/08_engineering_refactor/`; do not resume them as active instructions.
A future structural change needs a concrete objective, a fresh cost/risk review, and
explicit user authorization.

## Documentation Authority

- `docs/DOC_INDEX.md` is the documentation entry point. Files in the `docs/` root are
  current authority/governance; `docs/operations/` contains current operational
  contracts that do not belong in the top-level new-session reading set.
- `docs/_archive/` contains CLOSED, HISTORICAL, or SUPERSEDED records. Preserve them,
  but do not treat an archived plan as permission to restart work.
- Keep both root READMEs concise and aligned with `DOC_INDEX.md`; detailed historical
  results belong in the archive or preserved outputs.
- When moving a document, update Markdown links, path-bearing configuration metadata,
  and current navigation in the same change. Run the all-Markdown link audit plus the
  repository documentation check before finalizing.

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
