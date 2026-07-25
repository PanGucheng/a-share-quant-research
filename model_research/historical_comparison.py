from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr

from research_validation.bootstrap import moving_block_mean_test
from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "historical_model_comparison_v1"
OUTPUTS = (
    "artifact_manifest.json",
    "bootstrap_uncertainty.csv",
    "comparison_report.md",
    "contract_status.csv",
    "daily_ic.csv",
    "execution_capability_status.csv",
    "historical_research_leader.json",
    "input_receipts.csv",
    "method_summary.csv",
    "pairwise_daily_ic_differences.csv",
    "parent_receipts.csv",
    "readiness_summary.csv",
    "resolved_config.json",
    "split_metrics.csv",
)


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def load_config(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(resolve(path).read_text(encoding="utf-8"))
    if payload["experiment_class"] != "post_observation_research":
        raise ValueError("comparison must remain post_observation_research")
    if payload["execution"]["portfolio_comparison_status"] != (
        "blocked_execution_capability"
    ):
        raise ValueError("portfolio comparison blocker was removed")
    governance = payload["governance"]
    forbidden_true = (
        "production_model_selected",
        "unbiased_final_estimate",
        "authoritative_oos_execution_ready",
    )
    if any(bool(governance[name]) for name in forbidden_true):
        raise ValueError("comparison governance overclaims research evidence")
    return payload


def _contract(
    name: str,
    passed: bool,
    observed: object,
    required: object,
    reason: str = "",
) -> dict[str, object]:
    return {
        "check_name": name,
        "status": "pass" if passed else "blocked",
        "observed_value": observed,
        "required_value": required,
        "severity": "critical",
        "reason": "" if passed else reason,
    }


def _manifest_bundle(
    config: dict[str, Any],
) -> list[tuple[str, Path, dict[str, Any]]]:
    roles = (
        "date_manifest",
        "selection_manifest",
        "labels_manifest",
        "transparent_manifest",
        "linear_manifest",
        "lightgbm_manifest",
    )
    bundle = []
    for role in roles:
        path = resolve(config["parents"][role])
        manifest = load_artifact_manifest(path)
        if (
            manifest["artifact_status"] != "pass"
            or manifest["lineage_status"] != "complete"
            or bool(manifest["code_dirty"])
        ):
            raise ValueError(f"invalid direct parent: {role}")
        issues = validate_manifest_outputs(manifest, path.parent)
        if issues:
            raise ValueError(
                f"stale direct parent {role}: "
                + "|".join(issue.reason for issue in issues)
            )
        bundle.append((role, path, manifest))
    return bundle


def _load_test_dates(
    path: Path, split_ids: list[str]
) -> dict[str, pd.DatetimeIndex]:
    frame = pd.read_csv(path, parse_dates=["datetime"])
    frame["datetime"] = frame["datetime"].dt.normalize()
    result = {}
    for split_id in split_ids:
        dates = pd.DatetimeIndex(
            frame.loc[
                frame["split_id"].eq(split_id)
                & frame["fold"].eq("test"),
                "datetime",
            ].drop_duplicates()
        ).sort_values()
        if dates.empty:
            raise ValueError(f"missing test dates: {split_id}")
        result[split_id] = dates
    return result


def _daily_ic(
    frame: pd.DataFrame,
    *,
    split_id: str,
    method: str,
    minimum_daily_pairs: int,
) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby("datetime", sort=True):
        valid = group.loc[
            np.isfinite(group["prediction"])
            & np.isfinite(group["__label"])
        ]
        value = np.nan
        status = "blocked_insufficient_pairs"
        if (
            len(valid) >= minimum_daily_pairs
            and valid["prediction"].nunique(dropna=True) >= 2
            and valid["__label"].nunique(dropna=True) >= 2
        ):
            value = float(
                spearmanr(
                    valid["prediction"].to_numpy(),
                    valid["__label"].to_numpy(),
                ).statistic
            )
            status = "pass" if np.isfinite(value) else "blocked_non_finite"
        rows.append(
            {
                "outer_split_id": split_id,
                "method": method,
                "datetime": pd.Timestamp(date).date().isoformat(),
                "pair_count": len(valid),
                "rank_ic": value,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def _metrics(
    daily: pd.DataFrame,
    *,
    coverage: float,
) -> dict[str, float | int]:
    values = pd.to_numeric(
        daily.loc[daily["status"].eq("pass"), "rank_ic"],
        errors="coerce",
    ).dropna()
    standard_deviation = float(values.std(ddof=1))
    return {
        "mean_daily_rank_ic": float(values.mean()),
        "daily_rank_ic_ir": (
            float(values.mean() / standard_deviation)
            if standard_deviation > 0
            else 0.0
        ),
        "positive_ic_day_ratio": float(values.gt(0).mean()),
        "prediction_coverage": coverage,
        "daily_ic_count": len(values),
    }


def _transparent_evidence(
    config: dict[str, Any],
    test_dates: dict[str, pd.DatetimeIndex],
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    parents = config["parents"]
    score_runtime = resolve(parents["transparent_scores_runtime"])
    score_artifact = pd.read_csv(resolve(parents["transparent_score_artifact"]))
    recorded = str(score_artifact.loc[0, "sha256"])
    observed = file_sha256(score_runtime)
    if recorded != observed:
        raise ValueError("transparent score runtime hash mismatch")
    scores = pd.read_parquet(
        score_runtime,
        columns=[
            "datetime",
            "instrument",
            "method",
            "composite_score",
            "outer_split_id",
        ],
    ).rename(columns={"composite_score": "prediction"})
    scores["datetime"] = pd.to_datetime(scores["datetime"]).dt.normalize()
    scores["instrument"] = scores["instrument"].astype(str).str.upper()
    label_name = config["comparison"]["label_name"]
    labels_path = resolve(parents["labels_runtime"])
    labels = pd.read_parquet(
        labels_path,
        columns=["datetime", "instrument", label_name],
    ).rename(columns={label_name: "__label"})
    labels["datetime"] = pd.to_datetime(labels["datetime"]).dt.normalize()
    labels["instrument"] = labels["instrument"].astype(str).str.upper()
    if labels.duplicated(["datetime", "instrument"]).any():
        raise ValueError("duplicate label keys")

    daily_frames = []
    metric_rows = []
    receipt_rows: list[dict[str, object]] = [
        {
            "input_role": "transparent_scores_runtime",
            "path": score_runtime.as_posix(),
            "sha256": observed,
            "status": "verified",
        },
        {
            "input_role": "labels_runtime",
            "path": labels_path.as_posix(),
            "sha256": file_sha256(labels_path),
            "status": "observed_post_release",
        },
    ]
    minimum_pairs = int(config["comparison"]["minimum_daily_pairs"])
    for split_id, dates in test_dates.items():
        for method in ("equal_weight", "stability_weight"):
            selected = scores.loc[
                scores["outer_split_id"].eq(split_id)
                & scores["method"].eq(method)
            ].sort_values(["datetime", "instrument"], kind="stable")
            if not set(selected["datetime"].unique()).issubset(set(dates)):
                raise ValueError(f"transparent dates escape test fold: {split_id}")
            evaluation = selected.merge(
                labels,
                on=["datetime", "instrument"],
                how="left",
                validate="one_to_one",
            )
            label_hash = canonical_hash(
                evaluation[
                    ["datetime", "instrument", "__label"]
                ].astype(str).to_dict("records")
            )
            expected_hashes = []
            for directory, peer_methods in (
                (resolve(parents["linear_release_receipts"]), ("ridge", "elastic_net")),
                (resolve(parents["lightgbm_release_receipts"]), ("lightgbm",)),
            ):
                for peer_method in peer_methods:
                    receipt = json.loads(
                        (directory / f"{split_id}_{peer_method}.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    expected_hashes.append(str(receipt["test_label_sha256"]))
            if set(expected_hashes) != {label_hash}:
                raise ValueError(f"test label release hash mismatch: {split_id}")
            daily = _daily_ic(
                evaluation,
                split_id=split_id,
                method=method,
                minimum_daily_pairs=minimum_pairs,
            )
            coverage = float(
                (
                    np.isfinite(evaluation["prediction"])
                    & np.isfinite(evaluation["__label"])
                ).sum()
                / len(evaluation)
            )
            daily_frames.append(daily)
            metric_rows.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    **_metrics(daily, coverage=coverage),
                }
            )
        receipt_rows.append(
            {
                "input_role": f"{split_id}_test_labels",
                "path": labels_path.as_posix(),
                "sha256": label_hash,
                "status": "matches_all_model_release_receipts",
            }
        )
    return (
        pd.concat(daily_frames, ignore_index=True),
        pd.DataFrame(metric_rows),
        receipt_rows,
    )


def _published_model_evidence(
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parents = config["parents"]
    daily = pd.concat(
        [
            pd.read_csv(resolve(parents["linear_daily_ic"])),
            pd.read_csv(resolve(parents["lightgbm_daily_ic"])),
        ],
        ignore_index=True,
    )
    metrics = pd.concat(
        [
            pd.read_csv(resolve(parents["linear_metrics"])),
            pd.read_csv(resolve(parents["lightgbm_metrics"])),
        ],
        ignore_index=True,
    )
    daily["datetime"] = pd.to_datetime(daily["datetime"]).dt.date.astype(str)
    metrics = metrics[
        [
            "outer_split_id",
            "method",
            "mean_daily_rank_ic",
            "daily_rank_ic_ir",
            "prediction_coverage",
            "daily_ic_count",
        ]
    ].copy()
    positive = (
        daily.assign(positive=daily["rank_ic"].gt(0))
        .groupby(["outer_split_id", "method"], as_index=False)["positive"]
        .mean()
        .rename(columns={"positive": "positive_ic_day_ratio"})
    )
    return daily, metrics.merge(
        positive, on=["outer_split_id", "method"], validate="one_to_one"
    )


def _bootstrap_tables(
    daily: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bootstrap = config["bootstrap"]
    uncertainty = []
    for index, ((split_id, method), group) in enumerate(
        daily.groupby(["outer_split_id", "method"], sort=True)
    ):
        result = moving_block_mean_test(
            group.sort_values("datetime")["rank_ic"],
            samples=int(bootstrap["samples"]),
            block_length=int(bootstrap["block_length"]),
            seed=int(bootstrap["random_seed"]) + index,
        )
        uncertainty.append(
            {"outer_split_id": split_id, "method": method, **result}
        )

    pairwise = []
    method_order = list(config["comparison"]["methods"])
    for split_index, split_id in enumerate(config["comparison"]["split_ids"]):
        pivot = daily.loc[daily["outer_split_id"].eq(split_id)].pivot(
            index="datetime", columns="method", values="rank_ic"
        )
        for pair_index, (left, right) in enumerate(combinations(method_order, 2)):
            difference = (pivot[left] - pivot[right]).dropna()
            result = moving_block_mean_test(
                difference,
                samples=int(bootstrap["samples"]),
                block_length=int(bootstrap["block_length"]),
                seed=(
                    int(bootstrap["random_seed"])
                    + 1000
                    + split_index * 100
                    + pair_index
                ),
            )
            pairwise.append(
                {
                    "outer_split_id": split_id,
                    "left_method": left,
                    "right_method": right,
                    "mean_daily_rank_ic_difference": float(difference.mean()),
                    **result,
                }
            )
    return pd.DataFrame(uncertainty), pd.DataFrame(pairwise)


def _method_summary(
    split_metrics: pd.DataFrame,
    daily: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    ranked = split_metrics.copy()
    ranked["split_rank"] = ranked.groupby("outer_split_id")[
        "mean_daily_rank_ic"
    ].rank(method="average", ascending=False)
    rows = []
    complexity = config["comparison"]["method_complexity"]
    for method in config["comparison"]["methods"]:
        split = ranked.loc[ranked["method"].eq(method)]
        pooled = daily.loc[daily["method"].eq(method), "rank_ic"]
        rows.append(
            {
                "method": method,
                "equal_split_mean_daily_rank_ic": float(
                    split["mean_daily_rank_ic"].mean()
                ),
                "equal_split_mean_daily_rank_ic_ir": float(
                    split["daily_rank_ic_ir"].mean()
                ),
                "pooled_daily_mean_rank_ic": float(pooled.mean()),
                "pooled_positive_ic_day_ratio": float(pooled.gt(0).mean()),
                "worst_split_mean_daily_rank_ic": float(
                    split["mean_daily_rank_ic"].min()
                ),
                "mean_split_rank": float(split["split_rank"].mean()),
                "split_rank_std": float(split["split_rank"].std(ddof=0)),
                "minimum_split_prediction_coverage": float(
                    split["prediction_coverage"].min()
                ),
                "method_complexity": int(complexity[method]),
            }
        )
    summary = pd.DataFrame(rows)
    return summary.sort_values(
        [
            "equal_split_mean_daily_rank_ic",
            "equal_split_mean_daily_rank_ic_ir",
            "minimum_split_prediction_coverage",
            "method_complexity",
            "method",
        ],
        ascending=[False, False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)


def run_comparison(
    config_path: str | Path,
    *,
    command: str,
) -> dict[str, object]:
    config_file = resolve(config_path)
    config = load_config(config_file)
    bundle = _manifest_bundle(config)
    split_ids = list(config["comparison"]["split_ids"])
    methods = list(config["comparison"]["methods"])
    date_assignments = resolve(config["parents"]["date_assignments"])
    test_dates = _load_test_dates(date_assignments, split_ids)
    transparent_daily, transparent_metrics, input_rows = _transparent_evidence(
        config, test_dates
    )
    model_daily, model_metrics = _published_model_evidence(config)
    daily = pd.concat([transparent_daily, model_daily], ignore_index=True)
    split_metrics = pd.concat(
        [transparent_metrics, model_metrics], ignore_index=True
    )
    daily["datetime"] = pd.to_datetime(daily["datetime"]).dt.date.astype(str)
    daily = daily.sort_values(
        ["outer_split_id", "method", "datetime"], kind="stable"
    ).reset_index(drop=True)
    split_metrics = split_metrics.sort_values(
        ["outer_split_id", "method"], kind="stable"
    ).reset_index(drop=True)

    expected_pairs = {(split_id, method) for split_id in split_ids for method in methods}
    observed_pairs = set(
        split_metrics[["outer_split_id", "method"]].itertuples(
            index=False, name=None
        )
    )
    common_dates_valid = True
    for split_id in split_ids:
        date_sets = [
            set(
                daily.loc[
                    daily["outer_split_id"].eq(split_id)
                    & daily["method"].eq(method)
                    & daily["status"].eq("pass"),
                    "datetime",
                ]
            )
            for method in methods
        ]
        common_dates_valid &= len({tuple(sorted(values)) for values in date_sets}) == 1

    uncertainty, pairwise = _bootstrap_tables(daily, config)
    summary = _method_summary(split_metrics, daily, config)
    leader = str(summary.iloc[0]["method"])
    leader_payload = {
        "schema_version": 1,
        "historical_oos_research_leader": leader,
        "selection_metric": config["comparison"]["primary_summary_metric"],
        "evidence_class": "post_observation_research",
        "historical_test_already_observed": True,
        "production_model_selected": False,
        "unbiased_final_estimate": False,
        "authoritative_execution": False,
        "disclosure": (
            "Historical research leader is descriptive for previously "
            "observed test periods and is not a production selection."
        ),
    }
    minimum_coverage = float(split_metrics["prediction_coverage"].min())
    contracts = pd.DataFrame(
        [
            _contract("direct_parents_valid", len(bundle) == 6, len(bundle), 6),
            _contract(
                "legacy_purged_manifest_not_direct_parent",
                all(
                    item[2]["stage_id"] != "purged_walk_forward_v1"
                    for item in bundle
                ),
                [item[2]["stage_id"] for item in bundle],
                "no purged_walk_forward_v1",
            ),
            _contract(
                "five_methods_three_splits_complete",
                observed_pairs == expected_pairs,
                len(observed_pairs),
                len(expected_pairs),
            ),
            _contract(
                "common_test_dates_complete",
                common_dates_valid,
                common_dates_valid,
                True,
            ),
            _contract(
                "minimum_prediction_coverage",
                minimum_coverage
                >= float(config["comparison"]["minimum_prediction_coverage"]),
                minimum_coverage,
                f">={config['comparison']['minimum_prediction_coverage']}",
            ),
            _contract(
                "all_daily_ic_finite",
                np.isfinite(daily["rank_ic"]).all()
                and daily["status"].eq("pass").all(),
                int(daily["rank_ic"].notna().sum()),
                len(daily),
            ),
            _contract(
                "all_pairwise_comparisons_complete",
                len(pairwise) == len(split_ids) * 10,
                len(pairwise),
                len(split_ids) * 10,
            ),
            _contract(
                "historical_leader_not_production_selection",
                not leader_payload["production_model_selected"],
                leader_payload["production_model_selected"],
                False,
            ),
            _contract(
                "portfolio_comparison_fail_closed",
                config["execution"]["portfolio_comparison_status"]
                == "blocked_execution_capability",
                config["execution"]["portfolio_comparison_status"],
                "blocked_execution_capability",
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError(
            "comparison contracts failed: "
            + ",".join(
                contracts.loc[
                    ~contracts["status"].eq("pass"), "check_name"
                ].astype(str)
            )
        )

    readiness = pd.DataFrame(
        [
            {
                "historical_oos_model_comparison_complete": True,
                "historical_oos_research_leader_recorded": True,
                "five_method_historical_portfolio_comparison_complete": False,
                "portfolio_comparison_status": "blocked_execution_capability",
                "production_model_selected": False,
                "authoritative_oos_execution_ready": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    execution_status = pd.DataFrame(
        [
            {
                "status": "blocked_execution_capability",
                "reason": config["execution"]["blocker"],
                "instrument": config["execution"]["blocker_instrument"],
                "datetime": config["execution"]["blocker_date"],
                "terminal_approximation_present": False,
                "authoritative_execution": False,
            }
        ]
    )
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": role,
                "stage_id": manifest["stage_id"],
                "artifact_id": manifest["artifact_id"],
                "manifest_path": path.as_posix(),
                "artifact_status": manifest["artifact_status"],
                "lineage_status": manifest["lineage_status"],
                "direct_parent": True,
            }
            for role, path, manifest in bundle
        ]
    )
    resolved_config = {
        **config,
        "config_file_sha256": file_sha256(config_file),
        "executed_command": command,
        "executed_scope": "five_method_prediction_level_historical_oos_comparison",
        "historical_oos_research_leader": leader,
        "output_dir": resolve(config["output_dir"]).as_posix(),
    }
    output_dir = resolve(config["output_dir"])
    code_state = capture_code_state(PROJECT_ROOT)
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        daily.to_csv(publisher.path("daily_ic.csv"), index=False)
        split_metrics.to_csv(publisher.path("split_metrics.csv"), index=False)
        uncertainty.to_csv(
            publisher.path("bootstrap_uncertainty.csv"), index=False
        )
        pairwise.to_csv(
            publisher.path("pairwise_daily_ic_differences.csv"), index=False
        )
        summary.to_csv(publisher.path("method_summary.csv"), index=False)
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(publisher.path("readiness_summary.csv"), index=False)
        execution_status.to_csv(
            publisher.path("execution_capability_status.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        pd.DataFrame(input_rows).to_csv(
            publisher.path("input_receipts.csv"), index=False
        )
        publisher.path("historical_research_leader.json").write_text(
            json.dumps(leader_payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(
                resolved_config,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        report_lines = [
            "# Historical Model Comparison V1",
            "",
            f"- Historical research leader: `{leader}`.",
            "- Evidence class: `post_observation_research`.",
            "- Five-method prediction comparison: complete.",
            "- Five-method portfolio/NAV comparison: "
            "`blocked_execution_capability`.",
            "- Blocker: `SZ300280` unpriceable held position on 2025-04-18.",
            "- Production model selected: false.",
            "- Authoritative execution: false.",
            "- Unbiased final estimate: false.",
            "",
            "## Equal-split summary",
            "",
            summary.to_markdown(index=False),
            "",
        ]
        publisher.path("comparison_report.md").write_text(
            "\n".join(report_lines), encoding="utf-8"
        )
        output_files = [
            publisher.path(name)
            for name in OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[path for _, path, _ in bundle],
            universe_artifact_id=bundle[1][2].get("universe_artifact_id"),
            split_manifest_id=bundle[1][2].get("split_manifest_id"),
            factor_catalog_id=bundle[1][2].get("factor_catalog_id"),
            factor_frame_id=bundle[1][2].get("factor_frame_id"),
            start_date=min(dates.min() for dates in test_dates.values()),
            end_date=max(dates.max() for dates in test_dates.values()),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "historical_oos_research_leader": leader,
        "daily_ic_rows": len(daily),
        "minimum_prediction_coverage": minimum_coverage,
        "portfolio_comparison_status": "blocked_execution_capability",
    }
