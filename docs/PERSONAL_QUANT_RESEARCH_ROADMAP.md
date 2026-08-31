# Personal A-Share Quant Research Roadmap

> The numbered phases in this roadmap describe possible research progression. They
> are not extensions of the CLOSED Phase 0–6 engineering refactor; there is no
> engineering Phase 7.

## 1. Project Positioning

`A-Share Quant Research` is a personal, research-first China A-share quantitative
research framework. Its purpose is to support learning and practical research across
factors, machine learning, portfolios, backtests, and genuine forward observation,
with Microsoft Qlib as the primary underlying framework and Codex used to accelerate
implementation.

It is not intended to become an institutional platform, compliance audit system,
production trading infrastructure, or large-team financial application. Research
correctness remains strict; engineering complexity must earn its maintenance cost.

## 2. Why the Direction Changed

Earlier stages built extensive manifests, hashes, lineage, receipts, contracts,
validators, readiness gates, freeze protocols, and CI governance. That work helped
find real errors and existing modules may still depend on it, so it remains intact.

The project has now reached a point where extending those mechanisms by default has
diminishing research value. New work therefore changes from governance-driven to
research-first: solve the concrete quantitative question with the simplest design
that preserves temporal correctness and evidence boundaries.

Priority order:

1. correct research logic;
2. no future-data leakage;
3. no repeated tuning on test/holdout;
4. interpretable results;
5. maintainable code;
6. useful automation;
7. audit and governance only where justified.

## 3. Scientific Boundaries That Remain Strict

Every factor, feature, universe membership, preprocessing statistic, model input,
and portfolio decision must use only information available at decision time. Forward
prediction may not read future labels; evaluation begins only after labels mature.

Training and model/portfolio selection use only their declared development data.
Test or holdout is a final evaluation, not an iterative tuning surface.

`split_003` has already been observed. It remains useful for diagnosis but is no
longer an independent test for any change informed by it. In particular it must not
select TopK, rebalance interval, LightGBM parameters, factors, or a revised portfolio
and then be relabelled OOS.

Strategy V1 is LightGBM with the frozen 52-factor input, long-only Top50 equal
weighting, and five-trading-day rebalancing. If later evidence motivates Strategy
V2, both versions remain separately recorded. V2 begins genuine evidence only after
its own freeze date; V1 forward prediction and NAV history are never overwritten.

## 4. Lightweight Research Engineering

Existing manifests, validators, lineage records, receipts, and frozen artifacts are
kept for compatibility and historical evidence. This roadmap does not authorize a
large deletion or refactor of them.

New research modules should normally use existing inputs and modules, a small YAML
configuration, ordinary Python functions or small classes, CSV/JSON outputs,
figures, a clear Markdown report, focused pytest tests, and normal Git history.

Do not add layered lineage graphs, per-CSV hash receipts, prediction Git receipts,
stage-specific readiness gates, formal contract stacks, or production-style service
abstractions unless a demonstrated problem requires them. Correctness failures stop
the run; small non-critical coverage gaps should usually produce warnings and be
disclosed in the report.

## 5. Current Project State

Historical LightGBM research is complete. The current portfolio candidate is:

```text
Model:       LightGBM
Features:    frozen 52-factor set
Portfolio:   long only, Top 50, equal weight
Rebalance:   every 5 trading days
```

P01 performed well across the two development splits but failed to preserve relative
performance in the observed `split_003` holdout:

```text
Development mean net return:          about 29.10%
Development mean annualized excess:   about 61.70%
split_003 net return:                  about 3.57%
split_003 benchmark return:            about 19.19%
split_003 annualized excess:           about -30.24%
split_003 information ratio:           about -1.86
```

Approximate gross return in `split_003` was about 9.37%, still below the benchmark,
so cost alone is not a sufficient explanation. Frozen LightGBM test Rank IC was
approximately 0.078, 0.143, and 0.052 for `split_001`, `split_002`, and `split_003`.
That question motivated the now-closed historical diagnostics below; it is no longer
the roadmap's unstarted next action.

These are historical, already observed results. They are not a basis for claiming
an unbiased final estimate or a production-ready strategy.

Model Diagnostic V1 has now closed. Core Diagnostic, External PIT Style Data V1,
and the Style Attribution Extension are all `pass/complete`; the authoritative
historical closeout is
[`_archive/07_research_program_history/MODEL_DIAGNOSTIC_V1_CLOSEOUT.md`](_archive/07_research_program_history/MODEL_DIAGNOSTIC_V1_CLOSEOUT.md).
The combined evidence rejects a
persistent Small Cap explanation, extreme single-industry concentration, Top10
dilution, and transaction cost alone as sufficient explanations. Relationship
non-stationarity and Size/style-conditional effectiveness remain hypotheses for a
future, separately frozen protocol rather than established causes.

The Forward Track is operational and has produced the 2026-08-07 official prediction
and paper decision. Those records remain append-only; label evaluation waits for
maturity. Exact current status and commands are maintained in
[CURRENT_PIPELINE.md](CURRENT_PIPELINE.md).

Five later stages are also complete:

- **Economic Multi-Factor Research V1** mapped all 765 physically qualified factors
  into economic roles and evaluated 11 sleeves plus seven finite archetypes with
  split-local eligibility and fixed P01 diagnostics. No preregistered incremental
  chain passed both complementarity tests across all three observed splits.
- **ML Feature Pool MVP V1** found some incremental historical information in wider
  inputs, while the broad pool was less stable.
- **Performance Optimization V1** retained authoritative-compatible execution and
  rejected speedups that changed numerical outcomes.
- **Research Productivity V1** established content-addressed projection/spool cache
  reuse and froze Fast Research as screening-only, not winner selection.
- **Clustering Ablation V1** found mixed historical evidence when removing the
  one-representative-per-cluster gate, so the gate remains unchanged.

Detailed numbers and limitations live in the linked reports in
[DOC_INDEX.md](DOC_INDEX.md); they are not duplicated here. All five are CLOSED, and
the observed historical diagnostics do not authorize Strategy V2.

Research Protocol V2 was frozen independently of model outcomes and remains prior
protocol evidence. A later Dataset & Validation Design Study found that its short
development environments do not provide sufficient temporal information for formal
Structured ML selection. It therefore cannot directly authorize model competition.

Historical Data Engineering is now CLOSED. New Dataset / Protocol research must use
the canonical dataset covering 2010-01-29 through 2026-06-09: 765 of 774 frozen
definitions are research-usable and nine remain blocked. The next research stage is
a separately authorized Dataset / Research Protocol redesign; it has not started.
Structured ML and Strategy V2 remain unauthorized, while genuine Forward evidence
collection retains temporal priority.

## 6. Why Forward Collection Has Temporal Priority

Historical diagnostics and prospective evidence do not have the same time property.
The preserved `split_001`, `split_002`, and `split_003` inputs can be analyzed later:
performance, IC, style, industry, concentration, and cost diagnostics remain
reproducible from existing data.

A genuine forward observation cannot be recreated in the same way. If a trading day
passes without using the information then available to produce features, a frozen
strategy prediction, and a paper portfolio decision, a later calculation with full
historical data cannot honestly be relabelled as independent prospective evidence.

> Genuine forward evidence has time value and cannot be backfilled retrospectively.

The roadmap therefore uses a priority track plus parallel research instead of a
strict Diagnostics → Daily Data → Forward sequence.

## 7. Phase 1 — Start Genuine Forward Collection

The highest engineering priority is a lightweight Forward Track:

```text
new market data
        ↓
Daily Data Update V1
        ↓
frozen 52-feature generation
        ↓
frozen LightGBM prediction
        ↓
Strategy V1 Top50 paper decision
        ↓
persistent prediction / portfolio record
```

The immediate success criterion is not that the strategy makes money. It is that the
project starts producing real, time-stamped prospective evidence using only data
available at each decision time. Prediction must read zero future labels; evaluation
runs separately only after labels mature.

The implementation should reuse the existing forward candidate, model/preprocessing
artifacts, Qlib data/execution knowledge, and paper-accounting components. Essential
daily checks cover trading date, instrument count, OHLC gaps, volume anomalies,
52-feature count, and feature missing rate. It should not introduce another ingest
governance framework.

## 8. Completed Historical Research — Strategy Diagnostics V1

Strategy Diagnostics is closed and does not block the Forward Track. It explains the
historical performance change; it did not search for a better strategy. It reused
frozen predictions, existing historical backtest outputs, market/factor data,
universe membership, and historical effective-date market-cap/industry data.

The completed analysis covers:

- daily, monthly, cumulative, and 20/60-day rolling strategy, benchmark, and excess
  performance;
- daily, monthly, and 20/60-day rolling Rank IC plus mean, dispersion, ICIR, and
  positive ratio;
- point-in-time Size, Momentum, Volatility, and Industry exposure, with Liquidity or
  Value only if already reliable and easy to reuse;
- industry and market-cap concentration, top-ten stock contribution, and major
  positive/negative contributors where existing data supports them;
- turnover, commission, stamp tax, slippage, gross return, net return, and cost drag.

The report separates prediction quality, market regime, style exposure, portfolio
concentration, and turnover/cost. A mixed or inconclusive result is valid. Benchmark
constituent exposure is optional; if reliable weights are unavailable, Top50 versus
the research universe is the primary comparison and the limitation is stated.

This research must not call `model.fit`, retrain any model, select factors/features,
search hyperparameters, scan TopK or rebalance intervals, optimize portfolio
parameters, or create a new preferred strategy from `split_003`.

The stage is frozen except for a proven data error, leakage, contract failure,
implementation bug, or append-only clarification. Its findings may inform a future
Model V2 Research Protocol but must not modify the frozen Strategy V1 definition.
Benchmark constituent attribution remains unresolved/non-blocking.

## 9. Phase 2 — Accumulate and Evaluate Forward Evidence

Once the Forward Track is operational, the normal cycle is update, predict, paper
trade, record, and evaluate matured labels. Simple append-only or versioned CSVs for
predictions, trades, positions, daily NAV, and evaluation are sufficient. Git plus
strategy configuration provides the default version record; per-prediction receipt
infrastructure is not a default requirement.

Run Strategy V1 without adapting it to short-term results. Generate reports at useful
horizons such as 60, 120, or 250 trading days without creating a separate governance
project for every checkpoint.

## 10. Phase 3 — Research Decision

Combine historical diagnostics with genuine forward evidence to decide whether the
main issue is alpha decay, style exposure, portfolio construction, concentration,
turnover/cost, or mixed/inconclusive. Neither evidence source should be forced into a
single explanation, and observed history is not promoted back into a fresh holdout.

## 11. Phase 4 — Strategy V2 If Needed

Develop Strategy V2 only if the combined evidence identifies a concrete, actionable
problem. Observed history can generate hypotheses, but V2 receives a new version and
start/freeze date, and its real validation begins with new forward evidence after
that date. Preserve Strategy V1 and all of its forward history alongside it.

The next-stage entry, if explicitly authorized, is a separately documented **Model
V2 Research Protocol**. It must preregister the time-adaptation, relationship-
non-stationarity, Size/style-conditional, and alternative-model questions before
training. Candidate approaches are non-binding until that protocol is frozen.

## 12. Phase 5 — Long-Term Validation

Shadow trading and small-capital validation are long-term possibilities, not current
scope. Broker abstraction, order gateways, distributed monitoring, failover,
production reconciliation services, and complex kill-switch infrastructure are
explicitly deferred.

## 13. Long-Term Repository Shape

The repository may gradually converge toward:

```text
data/
    acquisition/
    update/
    quality/
research/
    factors/
    models/
    diagnostics/
backtest/
    portfolio/
    qlib_execution/
forward/
    prediction/
    paper_trading/
    evaluation/
configs/
scripts/
outputs/
```

This is a direction, not a migration task. Existing modules should not be moved in
bulk merely to match the diagram.

## 14. Codex Development Principles

Codex should read the relevant current architecture and results before changing it,
reuse existing modules, and prefer simple, explainable work that answers a research
question. Before adding a manager, registry, manifest, protocol, validator, gate,
adapter, or abstraction, ask whether the present research problem truly needs it.

Every handoff should state what was reused, what changed, what was deliberately not
done, the evidence boundary of any findings, and the next concrete research problem.

This roadmap correction changes documentation priority only. It does not authorize
implementation or execution of Daily Data Update, forward prediction, paper
portfolio, Strategy Diagnostics, Strategy V2, or shadow trading.
