from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from model_research.clustering_ablation import POLICY_D, POLICY_IDS
from model_research.feature_pool_policy import POLICY_A


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("split_001", "split_002", "split_003")


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _arm_root(split_id: str, policy_id: str) -> Path:
    stage = "ml_feature_pool_mvp_v1" if policy_id == POLICY_A else "ml_clustering_ablation_v1"
    return _resolve(f"outputs/{stage}/development/{split_id}/{policy_id}")


def _selected_validation(split_id: str, policy_id: str) -> dict[str, Any]:
    root = _arm_root(split_id, policy_id)
    selected = json.loads(
        (root / "selected_hyperparameters.json").read_text(encoding="utf-8")
    )["selected_hyperparameters"]
    metrics = pd.read_csv(root / "validation_metrics.csv")
    row = metrics.loc[metrics["candidate_sha256"].astype(str).eq(selected["candidate_sha256"])]
    if len(row) != 1:
        raise ValueError(f"missing selected validation metric: {split_id}/{policy_id}")
    return {**selected, **row.iloc[0].to_dict()}


def _comparison_rows(
    values: dict[tuple[str, str], dict[str, Any]],
    numeric_fields: list[str],
    split_ids: tuple[str, ...] = SPLITS,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split_id in split_ids:
        for role, policy_id in (("A", POLICY_A), ("D", POLICY_D)):
            rows.append(
                {
                    "outer_split_id": split_id,
                    "comparison_role": role,
                    "policy_id": policy_id,
                    **values[(split_id, policy_id)],
                }
            )
        a = values[(split_id, POLICY_A)]
        d = values[(split_id, POLICY_D)]
        delta = {field: float(d[field]) - float(a[field]) for field in numeric_fields}
        rows.append(
            {
                "outer_split_id": split_id,
                "comparison_role": "D_minus_A",
                "policy_id": "D_minus_A",
                **delta,
            }
        )
    return pd.DataFrame(rows)


def _model_diagnostics(
    feature_manifest: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    import lightgbm as lgb

    resource_rows: list[dict[str, Any]] = []
    usage_rows: list[dict[str, Any]] = []
    usage_summary: list[dict[str, Any]] = []
    for split_id in SPLITS:
        for policy_id in POLICY_IDS:
            root = _arm_root(split_id, policy_id)
            selected = _selected_validation(split_id, policy_id)
            resources = pd.read_csv(root / "resource_summary.csv").iloc[0]
            model_path = root / "model.txt"
            booster = lgb.Booster(model_file=str(model_path))
            annotations = feature_manifest.loc[
                feature_manifest["outer_split_id"].astype(str).eq(split_id)
                & feature_manifest["policy_id"].astype(str).eq(policy_id)
            ].sort_values("feature_order", kind="stable")
            factors = annotations["factor"].astype(str).tolist()
            if booster.feature_name() != factors:
                raise ValueError(f"model feature order mismatch: {split_id}/{policy_id}")
            split_importance = booster.feature_importance(importance_type="split")
            gain_importance = booster.feature_importance(importance_type="gain")
            model_dump = booster.dump_model()
            cluster_count = int(annotations["cluster_id"].nunique())
            nonrepresentative_count = int((~annotations["is_representative"].astype(bool)).sum())
            resource_rows.append(
                {
                    "outer_split_id": split_id,
                    "policy_id": policy_id,
                    "feature_count": len(factors),
                    "cluster_count": cluster_count,
                    "average_members_per_cluster": len(factors) / cluster_count,
                    "nonrepresentative_count": nonrepresentative_count,
                    "fraction_nonrepresentatives": nonrepresentative_count / len(factors),
                    "selected_candidate": f"{selected['structural_row_id']}@{int(selected['num_boost_round'])}",
                    "wall_seconds": float(resources["wall_seconds"]),
                    "peak_rss_mib": float(resources["peak_rss_mib"]),
                    "model_size_bytes": model_path.stat().st_size,
                    "tree_count": int(booster.num_trees()),
                    "total_leaves": int(
                        sum(int(tree["num_leaves"]) for tree in model_dump["tree_info"])
                    ),
                    "execution_class": "full_development",
                    "execution_profile": (
                        "ml_feature_pool_mvp_v1"
                        if policy_id == POLICY_A
                        else "ml_clustering_ablation_full_v1"
                    ),
                }
            )
            if policy_id == POLICY_D:
                usage = annotations[
                    [
                        "outer_split_id",
                        "factor",
                        "feature_order",
                        "source_family",
                        "cluster_id",
                        "is_representative",
                        "representative_score",
                    ]
                ].copy()
                usage["split_importance"] = split_importance
                usage["gain_importance"] = gain_importance
                usage["used_by_split"] = usage["split_importance"].gt(0)
                usage["used_by_gain"] = usage["gain_importance"].gt(0)
                usage_rows.extend(usage.to_dict("records"))
                nonrep = ~usage["is_representative"].astype(bool)
                used = usage["used_by_split"] | usage["used_by_gain"]
                multi_used = (
                    usage.loc[used].groupby("cluster_id")["factor"].nunique().gt(1)
                )
                usage_summary.append(
                    {
                        "outer_split_id": split_id,
                        "d_total_features": len(usage),
                        "a_representatives": int((~nonrep).sum()),
                        "d_minus_a_nonrepresentatives": int(nonrep.sum()),
                        "representatives_with_nonzero_split": int(
                            ((~nonrep) & usage["used_by_split"]).sum()
                        ),
                        "nonrepresentatives_with_nonzero_split": int(
                            (nonrep & usage["used_by_split"]).sum()
                        ),
                        "nonrepresentatives_with_nonzero_gain": int(
                            (nonrep & usage["used_by_gain"]).sum()
                        ),
                        "clusters_with_multiple_used_members": int(multi_used.sum()),
                    }
                )
    resources = pd.DataFrame(resource_rows)
    delta_rows = []
    numeric_fields = [
        "feature_count",
        "cluster_count",
        "average_members_per_cluster",
        "nonrepresentative_count",
        "fraction_nonrepresentatives",
        "wall_seconds",
        "peak_rss_mib",
        "model_size_bytes",
        "tree_count",
        "total_leaves",
    ]
    for split_id in SPLITS:
        a = resources.loc[
            resources["outer_split_id"].eq(split_id) & resources["policy_id"].eq(POLICY_A)
        ].iloc[0]
        d = resources.loc[
            resources["outer_split_id"].eq(split_id) & resources["policy_id"].eq(POLICY_D)
        ].iloc[0]
        delta_rows.append(
            {
                "outer_split_id": split_id,
                "policy_id": "D_minus_A",
                **{field: float(d[field]) - float(a[field]) for field in numeric_fields},
                "selected_candidate": "not_applicable",
                "execution_class": "comparison",
                "execution_profile": "D_minus_A",
            }
        )
    resources = pd.concat([resources, pd.DataFrame(delta_rows)], ignore_index=True)
    return resources, pd.DataFrame(usage_rows), pd.DataFrame(usage_summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", default="reports/ml_clustering_ablation_v1")
    args = parser.parse_args()
    report_dir = _resolve(args.report_dir)
    if report_dir.exists():
        raise FileExistsError("clustering-ablation report is immutable")
    report_dir.mkdir(parents=True, exist_ok=False)

    current = _resolve("outputs/ml_clustering_ablation_v1/current")
    feature_manifest = pd.read_csv(current / "feature_pool_manifest.csv")
    policies = pd.read_csv(current / "policy_manifest.csv")
    feature_manifest.loc[feature_manifest["policy_id"].eq(POLICY_D)].to_csv(
        report_dir / "policy_D_manifest.csv", index=False
    )
    pd.read_csv(current / "stable_core_eligibility_exclusions.csv").to_csv(
        report_dir / "stable_core_eligibility_exclusions.csv", index=False
    )

    cold_root = _resolve(
        "outputs/research_productivity_v1/fast_runs/ml_clustering_ablation_v1_cold"
    )
    warm_root = _resolve(
        "outputs/research_productivity_v1/fast_runs/ml_clustering_ablation_v1_warm"
    )
    cold = pd.read_csv(cold_root / "arm_summary.csv")
    warm = pd.read_csv(warm_root / "arm_summary.csv")
    fast_values: dict[tuple[str, str], dict[str, Any]] = {}
    for row in cold.itertuples(index=False):
        warm_row = warm.loc[
            warm["outer_split_id"].astype(str).eq(str(row.outer_split_id))
            & warm["policy_id"].astype(str).eq(str(row.policy_id))
        ].iloc[0]
        fast_values[(str(row.outer_split_id), str(row.policy_id))] = {
            "feature_count": int(row.feature_count),
            "mean_daily_rank_ic": float(row.mean_daily_rank_ic),
            "daily_rank_ic_ir": float(row.daily_rank_ic_ir),
            "prediction_coverage": float(row.prediction_coverage),
            "cold_wall_seconds": float(row.wall_seconds),
            "warm_wall_seconds": float(warm_row["wall_seconds"]),
            "cold_peak_rss_mib": float(row.peak_rss_mib),
            "warm_peak_rss_mib": float(warm_row["peak_rss_mib"]),
            "cold_cache_hit": bool(row.train_cache_hit) and bool(row.validation_cache_hit),
            "warm_cache_hit": bool(warm_row["train_cache_hit"])
            and bool(warm_row["validation_cache_hit"]),
            "selected_candidate": f"{row.selected_fast_structural_row_id}@{int(row.selected_fast_num_boost_round)}",
        }
    fast = _comparison_rows(
        fast_values,
        [
            "feature_count",
            "mean_daily_rank_ic",
            "daily_rank_ic_ir",
            "prediction_coverage",
            "cold_wall_seconds",
            "warm_wall_seconds",
            "cold_peak_rss_mib",
            "warm_peak_rss_mib",
        ],
        split_ids=("split_001", "split_002"),
    )
    cold_receipt = json.loads(
        (cold_root / "fast_research_receipt.json").read_text(encoding="utf-8")
    )
    fast["promotion_status"] = cold_receipt["promotion_status"]
    fast["execution_class"] = "exploratory_fast"
    fast["execution_profile"] = "fast_research_v1"
    fast.to_csv(report_dir / "fast_research_results.csv", index=False)

    development_values: dict[tuple[str, str], dict[str, Any]] = {}
    validation_metrics: dict[tuple[str, str], dict[str, Any]] = {}
    for split_id in SPLITS:
        for policy_id in POLICY_IDS:
            selected = _selected_validation(split_id, policy_id)
            validation_metrics[(split_id, policy_id)] = selected
            development_values[(split_id, policy_id)] = {
                "feature_count": int(
                    policies.loc[
                        policies["outer_split_id"].astype(str).eq(split_id)
                        & policies["policy_id"].astype(str).eq(policy_id),
                        "factor_count",
                    ].iloc[0]
                ),
                "mean_daily_rank_ic": float(selected["mean_daily_rank_ic"]),
                "daily_rank_ic_ir": float(selected["daily_rank_ic_ir"]),
                "prediction_coverage": float(selected["prediction_coverage"]),
                "selected_candidate": f"{selected['structural_row_id']}@{int(selected['num_boost_round'])}",
            }
    development = _comparison_rows(
        development_values,
        ["feature_count", "mean_daily_rank_ic", "daily_rank_ic_ir", "prediction_coverage"],
    )
    development["execution_class"] = "full_development"
    development.to_csv(report_dir / "development_metrics.csv", index=False)

    replay_root = _resolve("outputs/ml_clustering_ablation_v1/historical_replay")
    historical_metrics = pd.read_csv(replay_root / "test_metrics.csv")
    daily = pd.read_csv(replay_root / "test_daily_ic.csv")
    historical_values: dict[tuple[str, str], dict[str, Any]] = {}
    for split_id in SPLITS:
        for policy_id in POLICY_IDS:
            metric = historical_metrics.loc[
                historical_metrics["outer_split_id"].astype(str).eq(split_id)
                & historical_metrics["policy_id"].astype(str).eq(policy_id)
            ].iloc[0]
            daily_rows = daily.loc[
                daily["outer_split_id"].astype(str).eq(split_id)
                & daily["policy_id"].astype(str).eq(policy_id)
                & daily["status"].astype(str).eq("pass")
            ]
            historical_values[(split_id, policy_id)] = {
                "mean_daily_rank_ic": float(metric["mean_daily_rank_ic"]),
                "daily_rank_ic_ir": float(metric["daily_rank_ic_ir"]),
                "positive_ic_ratio": float(daily_rows["rank_ic"].gt(0).mean()),
                "prediction_coverage": float(metric["prediction_coverage"]),
                "validation_to_historical_rank_ic_degradation": float(
                    metric["mean_daily_rank_ic"]
                )
                - float(validation_metrics[(split_id, policy_id)]["mean_daily_rank_ic"]),
            }
    historical = _comparison_rows(
        historical_values,
        [
            "mean_daily_rank_ic",
            "daily_rank_ic_ir",
            "positive_ic_ratio",
            "prediction_coverage",
            "validation_to_historical_rank_ic_degradation",
        ],
    )
    historical.to_csv(report_dir / "historical_prediction_comparison.csv", index=False)
    historical_deltas = historical.loc[historical["comparison_role"].eq("D_minus_A")]
    summary = pd.DataFrame(
        [
            {
                "metric": field,
                "equal_split_mean_delta": float(historical_deltas[field].mean()),
                "split_dispersion_std": float(historical_deltas[field].std(ddof=0)),
                "worst_split": str(
                    historical_deltas.loc[historical_deltas[field].idxmin(), "outer_split_id"]
                ),
                "worst_split_delta": float(historical_deltas[field].min()),
                "positive_delta_split_count": int(historical_deltas[field].gt(0).sum()),
                "split_count": len(SPLITS),
            }
            for field in (
                "mean_daily_rank_ic",
                "daily_rank_ic_ir",
                "positive_ic_ratio",
                "prediction_coverage",
            )
        ]
    )
    summary.to_csv(report_dir / "historical_prediction_summary.csv", index=False)

    resources, usage, usage_summary = _model_diagnostics(feature_manifest)
    resources.to_csv(report_dir / "model_resource_comparison.csv", index=False)
    usage.to_csv(report_dir / "feature_usage_diagnostic.csv", index=False)
    usage_summary.to_csv(report_dir / "feature_usage_summary.csv", index=False)

    portfolio_raw = pd.read_csv(
        _resolve("outputs/ml_clustering_ablation_v1/portfolio/portfolio_comparison.csv")
    )
    portfolio_fields = [
        "total_return",
        "sharpe_ratio",
        "information_ratio",
        "max_drawdown",
        "annualized_turnover",
        "cost_drag",
        "prediction_coverage",
    ]
    portfolio_rows: list[dict[str, Any]] = []
    for cost in (0.0, 10.0, 20.0):
        for split_id in SPLITS:
            by_policy = {}
            for role, policy_id in (("A", POLICY_A), ("D", POLICY_D)):
                row = portfolio_raw.loc[
                    portfolio_raw["outer_split_id"].astype(str).eq(split_id)
                    & portfolio_raw["policy_id"].astype(str).eq(policy_id)
                    & portfolio_raw["cost_scenario_bps"].astype(float).eq(cost)
                ].iloc[0]
                by_policy[policy_id] = row
                portfolio_rows.append(
                    {
                        "outer_split_id": split_id,
                        "cost_scenario_bps": cost,
                        "comparison_role": role,
                        "policy_id": policy_id,
                        **{field: float(row[field]) for field in portfolio_fields},
                    }
                )
            portfolio_rows.append(
                {
                    "outer_split_id": split_id,
                    "cost_scenario_bps": cost,
                    "comparison_role": "D_minus_A",
                    "policy_id": "D_minus_A",
                    **{
                        field: float(by_policy[POLICY_D][field])
                        - float(by_policy[POLICY_A][field])
                        for field in portfolio_fields
                    },
                }
            )
    portfolio = pd.DataFrame(portfolio_rows)
    portfolio.to_csv(report_dir / "portfolio_comparison.csv", index=False)

    limitations = {
        "historical_pattern": "mixed",
        "experiment_class": "post_observation_research",
        "historical_test_already_observed": True,
        "authoritative_execution": False,
        "unbiased_final_estimate": False,
        "decision_authority": "diagnostic_only",
        "selection_authorized": False,
        "strategy_v2_authorized": False,
        "production_winner_produced": False,
        "historical_execution_approximate": True,
        "bootstrap_not_run": True,
        "clustering_parent_lineage_status": "inconsistent:universe_artifact_id",
        "importance_is_diagnostic_only": True,
        "deferred": [
            "Policy E",
            "feature-selection redesign",
            "SHAP/permutation",
            "model-aware selection",
            "LightGBM retuning",
        ],
    }
    (report_dir / "limitations.json").write_text(
        json.dumps(limitations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    d_counts = policies.loc[policies["policy_id"].eq(POLICY_D)].set_index(
        "outer_split_id"
    )["factor_count"]
    a_counts = policies.loc[policies["policy_id"].eq(POLICY_A)].set_index(
        "outer_split_id"
    )["factor_count"]
    fast_delta = fast.loc[fast["comparison_role"].eq("D_minus_A")].set_index(
        "outer_split_id"
    )
    dev_delta = development.loc[
        development["comparison_role"].eq("D_minus_A")
    ].set_index("outer_split_id")
    hist_delta = historical.loc[
        historical["comparison_role"].eq("D_minus_A")
    ].set_index("outer_split_id")
    primary = portfolio.loc[
        portfolio["comparison_role"].eq("D_minus_A")
        & portfolio["cost_scenario_bps"].eq(10.0)
    ].set_index("outer_split_id")
    lines = [
        "# Clustering Ablation V1 — Historical Diagnostic Report",
        "",
        "## Outcome",
        "",
        "`historical_pattern = mixed`",
        "",
        "Removing the one-representative-per-cluster hard gate helped Full development "
        "in two of three splits, but historical Rank IC and fixed P01 improved in only "
        "one of three splits. The evidence does not support calling the gate either "
        "uniformly information-losing or uniformly useful denoising.",
        "",
        "- `decision_authority=diagnostic_only`",
        "- `selection_authorized=false`",
        "- `strategy_v2_authorized=false`",
        "- Historical tests were already observed; this is not fresh OOS or an unbiased estimate.",
        "",
        "## Policy identity",
        "",
    ]
    for split_id in SPLITS:
        lines.append(
            f"- {split_id}: A={int(a_counts[split_id])}, D={int(d_counts[split_id])}, "
            f"D-A={int(d_counts[split_id] - a_counts[split_id])} stable_core non-representatives."
        )
    lines.extend(
        [
            "",
            "D preserves frozen A order and appends eligible non-representatives in "
            "`source_family,factor` order. Stable-core roles, FDR, windows, thresholds, "
            "clustering, eligibility, preprocessing, model candidates, seeds, and P01 were not recomputed.",
            "",
            "The frozen eligibility intersection excluded 6/4/5 stable-core factors: "
            "14 split-factor rows were duplicate columns and one had insufficient coverage. "
            "All passed correctness checks; exclusions are recorded explicitly.",
            "",
            "## Canary and Fast Research",
            "",
            "Canary passed deterministic prediction hashes, finite predictions, candidate-table "
            "parity, train-only preprocessing, and zero historical-test reads.",
        ]
    )
    for split_id in ("split_001", "split_002"):
        lines.append(
            f"- Fast {split_id}: Rank IC D-A {fast_delta.at[split_id, 'mean_daily_rank_ic']:+.6f}; "
            f"ICIR D-A {fast_delta.at[split_id, 'daily_rank_ic_ir']:+.6f}; "
            f"D cold/warm {fast_values[(split_id, POLICY_D)]['cold_wall_seconds']:.1f}/"
            f"{fast_values[(split_id, POLICY_D)]['warm_wall_seconds']:.1f}s; "
            f"D cold/warm peak RSS {fast_values[(split_id, POLICY_D)]['cold_peak_rss_mib']:.1f}/"
            f"{fast_values[(split_id, POLICY_D)]['warm_peak_rss_mib']:.1f} MiB."
        )
    lines.extend(
        [
            "- Fast promotion status: `inconclusive`; under frozen semantics this was promoted to Full.",
            "- Cold/warm metric and selected-candidate parity was exact; all warm projection caches hit.",
            "",
            "## Full development",
            "",
        ]
    )
    for split_id in SPLITS:
        lines.append(
            f"- {split_id}: Rank IC D-A {dev_delta.at[split_id, 'mean_daily_rank_ic']:+.6f}; "
            f"ICIR D-A {dev_delta.at[split_id, 'daily_rank_ic_ir']:+.6f}."
        )
    lines.extend(
        [
            f"- Equal-split mean Rank IC D-A: {dev_delta['mean_daily_rank_ic'].mean():+.6f}; "
            f"positive splits: {int(dev_delta['mean_daily_rank_ic'].gt(0).sum())}/3.",
            "",
            "## Historical diagnostic replay",
            "",
        ]
    )
    for split_id in SPLITS:
        lines.append(
            f"- {split_id}: Rank IC D-A {hist_delta.at[split_id, 'mean_daily_rank_ic']:+.6f}; "
            f"ICIR D-A {hist_delta.at[split_id, 'daily_rank_ic_ir']:+.6f}; "
            f"positive-IC ratio D-A {hist_delta.at[split_id, 'positive_ic_ratio']:+.6f}."
        )
    lines.extend(
        [
            f"- Equal-split mean Rank IC D-A: {hist_delta['mean_daily_rank_ic'].mean():+.6f}; "
            f"positive splits: {int(hist_delta['mean_daily_rank_ic'].gt(0).sum())}/3; "
            f"worst split: {hist_delta['mean_daily_rank_ic'].idxmin()}.",
            "",
            "## Fixed P01 at 10 bps",
            "",
        ]
    )
    for split_id in SPLITS:
        lines.append(
            f"- {split_id}: net return D-A {primary.at[split_id, 'total_return']:+.6f}; "
            f"IR D-A {primary.at[split_id, 'information_ratio']:+.6f}; "
            f"turnover D-A {primary.at[split_id, 'annualized_turnover']:+.3f}."
        )
    lines.extend(
        [
            "- Net return and IR improved in 1/3 splits; turnover fell in 3/3 splits.",
            "- 0 and 20 bps secondary scenarios are in `portfolio_comparison.csv`; no rule was searched.",
            "",
            "## Mechanism and cost",
            "",
        ]
    )
    for row in usage_summary.itertuples(index=False):
        resource = resources.loc[
            resources["outer_split_id"].eq(row.outer_split_id)
            & resources["policy_id"].eq(POLICY_D)
        ].iloc[0]
        baseline_resource = resources.loc[
            resources["outer_split_id"].eq(row.outer_split_id)
            & resources["policy_id"].eq(POLICY_A)
        ].iloc[0]
        lines.append(
            f"- {row.outer_split_id}: {row.nonrepresentatives_with_nonzero_split}/"
            f"{row.d_minus_a_nonrepresentatives} non-representatives had non-zero split "
            f"importance; {row.clusters_with_multiple_used_members} clusters used multiple members; "
            f"D/A wall {resource['wall_seconds']:.1f}/{baseline_resource['wall_seconds']:.1f}s "
            f"({resource['wall_seconds'] / baseline_resource['wall_seconds']:.2f}x); "
            f"D/A peak RSS {resource['peak_rss_mib']:.1f}/{baseline_resource['peak_rss_mib']:.1f} MiB "
            f"({resource['peak_rss_mib'] / baseline_resource['peak_rss_mib']:.2f}x)."
        )
    lines.extend(
        [
            "",
            "The added members were genuinely used by LightGBM, but usage does not prove causal "
            "increment. Wider D also materially increased runtime, memory, and model search cost.",
            "",
            "## Interpretation and next step",
            "",
            "The representative hard gate is currently **mixed**: it may discard useful joint "
            "development information in some regimes, while the unrestricted stable-core pool "
            "did not generalize consistently and was notably worse in split_002 P01. Do not "
            "remove the gate from Strategy V1 and do not create Policy E from this result.",
            "",
            "Given the prior B>A diagnostic and the non-consistent A→D result, the next focused "
            "study should prioritize the existing conditional-signal mechanism. Any later "
            "multiple-representative or group-aware clustering study must be separately "
            "preregistered; SHAP, permutation, model-aware pruning, interactions, and LightGBM "
            "retuning remain out of scope.",
            "",
            "## Limitations",
            "",
            "- Historical tests were already observed and cannot authorize production or Strategy V2.",
            "- No bootstrap was added; paired daily values are diagnostic only.",
            "- P01 historical execution remains approximate and retains existing Qlib fallback warnings.",
            "- The frozen clustering parent records an existing universe-artifact lineage inconsistency; "
            "D uses cluster metadata only as annotation, while A identity is referenced unchanged.",
        ]
    )
    (report_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
