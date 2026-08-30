from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from research_validation.purged_split import label_intervals


@dataclass(frozen=True)
class TrainingHistoryCandidate:
    candidate_id: str
    mode: str
    safe_training_dates: int | None = None


@dataclass(frozen=True)
class ProtocolV2Config:
    matrix_start: pd.Timestamp
    matrix_end: pd.Timestamp
    execution_lag: int
    holding_days: int
    first_validation_start: pd.Timestamp
    validation_months: int
    development_step_months: int
    development_environment_count: int
    minimum_train_dates: int
    minimum_validation_dates: int
    selection_freeze_boundary: pd.Timestamp
    first_diagnostic_start: pd.Timestamp
    diagnostic_months: int
    diagnostic_step_months: int
    diagnostic_environment_count: int
    minimum_test_dates: int
    candidates: tuple[TrainingHistoryCandidate, ...]


def load_calendar(path: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(pd.to_datetime(path.read_text(encoding="utf-8").splitlines()))
    dates = dates[(dates >= start) & (dates <= end)].drop_duplicates().sort_values()
    if dates.empty or dates[0] != start or dates[-1] != end:
        raise ValueError("canonical calendar does not cover the declared matrix boundaries")
    return dates


def _dates_in_period(
    dates: pd.DatetimeIndex, start: pd.Timestamp, end_exclusive: pd.Timestamp
) -> pd.DatetimeIndex:
    return dates[(dates >= start) & (dates < end_exclusive)]


def _mature_within(
    intervals: pd.DataFrame, dates: pd.DatetimeIndex, boundary: pd.Timestamp
) -> pd.DataFrame:
    selected = intervals.loc[intervals["feature_time"].isin(dates)].copy()
    return selected.loc[selected["label_end_time"] < boundary].copy()


def _safe_training_pool(
    intervals: pd.DataFrame, test_start: pd.Timestamp
) -> tuple[pd.DataFrame, pd.DataFrame]:
    earlier = intervals.loc[intervals["feature_time"] < test_start].copy()
    overlap = earlier["label_end_time"] >= test_start
    return earlier.loc[~overlap].copy(), earlier.loc[overlap].copy()


def _candidate_train(
    safe_pool: pd.DataFrame, candidate: TrainingHistoryCandidate
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if candidate.mode == "expanding":
        return safe_pool.copy(), safe_pool.iloc[0:0].copy()
    if candidate.mode != "sliding" or not candidate.safe_training_dates:
        raise ValueError(f"unsupported training history candidate: {candidate}")
    kept = safe_pool.tail(candidate.safe_training_dates).copy()
    excluded = safe_pool.iloc[: max(0, len(safe_pool) - len(kept))].copy()
    return kept, excluded


def build_research_protocol_v2(
    calendar: pd.DatetimeIndex,
    config: ProtocolV2Config,
    legacy_manifest: pd.DataFrame,
    legacy_assignments: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    dates = pd.DatetimeIndex(calendar).drop_duplicates().sort_values()
    intervals = label_intervals(dates, config.holding_days, config.execution_lag)
    development_environments: list[dict[str, object]] = []
    development_tasks: list[dict[str, object]] = []
    development_assignments: list[dict[str, object]] = []
    purged_rows: list[dict[str, object]] = []
    window_excluded_rows: list[dict[str, object]] = []

    for sequence in range(config.development_environment_count):
        target_start = config.first_validation_start + pd.DateOffset(
            months=sequence * config.development_step_months
        )
        target_end = target_start + pd.DateOffset(months=config.validation_months)
        next_environment = target_start + pd.DateOffset(months=config.development_step_months)
        raw_validation_dates = _dates_in_period(dates, target_start, target_end)
        validation = _mature_within(intervals, raw_validation_dates, next_environment)
        if validation.empty or len(validation) < config.minimum_validation_dates:
            raise ValueError(
                f"development environment {sequence + 1} has insufficient validation dates"
            )
        validation_start = validation["feature_time"].min()
        safe_pool, purged = _safe_training_pool(intervals, validation_start)
        environment_id = f"dev_env_{sequence + 1:03d}"
        development_environments.append(
            {
                "environment_id": environment_id,
                "sequence": sequence + 1,
                "nominal_start": target_start,
                "nominal_end": target_end - pd.Timedelta(days=1),
                "validation_start": validation_start,
                "validation_end": validation["feature_time"].max(),
                "validation_label_end": validation["label_end_time"].max(),
                "next_environment_boundary": next_environment,
                "nominal_trading_dates": len(raw_validation_dates),
                "validation_dates": len(validation),
                "maturity_boundary_exclusions": len(raw_validation_dates) - len(validation),
                "evidence_role": "development_selection_authority",
            }
        )
        for candidate in config.candidates:
            train, window_excluded = _candidate_train(safe_pool, candidate)
            if len(train) < config.minimum_train_dates:
                raise ValueError(
                    f"{environment_id}/{candidate.candidate_id} has insufficient train dates"
                )
            task_id = f"{environment_id}__{candidate.candidate_id}"
            development_tasks.append(
                {
                    "task_id": task_id,
                    "environment_id": environment_id,
                    "training_history_id": candidate.candidate_id,
                    "train_start": train["feature_time"].min(),
                    "train_end": train["feature_time"].max(),
                    "validation_start": validation_start,
                    "validation_end": validation["feature_time"].max(),
                    "train_dates": len(train),
                    "validation_dates": len(validation),
                    "purged_dates": len(purged),
                    "embargoed_dates": 0,
                    "window_excluded_dates": len(window_excluded),
                    "selection_authority": True,
                    "execution_authorized": False,
                }
            )
            development_assignments.extend(
                {"task_id": task_id, "datetime": value, "fold": "train"}
                for value in train["feature_time"]
            )
            development_assignments.extend(
                {"task_id": task_id, "datetime": value, "fold": "validation"}
                for value in validation["feature_time"]
            )
            purged_rows.extend(
                {
                    "task_id": task_id,
                    "datetime": row.feature_time,
                    "label_start_time": row.label_start_time,
                    "label_end_time": row.label_end_time,
                    "reason": "label_interval_overlaps_validation_start",
                }
                for row in purged.itertuples(index=False)
            )
            window_excluded_rows.extend(
                {
                    "task_id": task_id,
                    "datetime": value,
                    "reason": "outside_registered_sliding_history",
                }
                for value in window_excluded["feature_time"]
            )

    last_development_label = max(row["validation_label_end"] for row in development_environments)
    if pd.Timestamp(last_development_label) >= config.selection_freeze_boundary:
        raise ValueError("development labels cross the selection freeze boundary")

    diagnostic_environments: list[dict[str, object]] = []
    diagnostic_tasks: list[dict[str, object]] = []
    diagnostic_assignments: list[dict[str, object]] = []
    diagnostic_purged_rows: list[dict[str, object]] = []
    for sequence in range(config.diagnostic_environment_count):
        target_start = config.first_diagnostic_start + pd.DateOffset(
            months=sequence * config.diagnostic_step_months
        )
        target_end = target_start + pd.DateOffset(months=config.diagnostic_months)
        next_environment = target_start + pd.DateOffset(months=config.diagnostic_step_months)
        raw_test_dates = _dates_in_period(dates, target_start, target_end)
        test = _mature_within(intervals, raw_test_dates, next_environment)
        if test.empty or len(test) < config.minimum_test_dates:
            raise ValueError(f"diagnostic environment {sequence + 1} has insufficient test dates")
        test_start = test["feature_time"].min()
        safe_pool, purged = _safe_training_pool(intervals, test_start)
        environment_id = f"diag_env_{sequence + 1:03d}"
        diagnostic_environments.append(
            {
                "environment_id": environment_id,
                "sequence": sequence + 1,
                "nominal_start": target_start,
                "nominal_end": target_end - pd.Timedelta(days=1),
                "test_start": test_start,
                "test_end": test["feature_time"].max(),
                "test_label_end": test["label_end_time"].max(),
                "next_environment_boundary": next_environment,
                "nominal_trading_dates": len(raw_test_dates),
                "test_dates": len(test),
                "maturity_boundary_exclusions": len(raw_test_dates) - len(test),
                "evidence_role": "historical_diagnostic_only",
                "post_observation_research": True,
            }
        )
        for candidate in config.candidates:
            train, window_excluded = _candidate_train(safe_pool, candidate)
            task_id = f"{environment_id}__{candidate.candidate_id}"
            diagnostic_tasks.append(
                {
                    "task_id": task_id,
                    "environment_id": environment_id,
                    "training_history_id": candidate.candidate_id,
                    "train_start": train["feature_time"].min(),
                    "train_end": train["feature_time"].max(),
                    "test_start": test_start,
                    "test_end": test["feature_time"].max(),
                    "train_dates": len(train),
                    "test_dates": len(test),
                    "purged_dates": len(purged),
                    "embargoed_dates": 0,
                    "window_excluded_dates": len(window_excluded),
                    "selection_authority": False,
                    "execution_authorized": False,
                    "authorization_condition": "development_candidate_frozen_first",
                }
            )
            diagnostic_assignments.extend(
                {"task_id": task_id, "datetime": value, "fold": "train"}
                for value in train["feature_time"]
            )
            diagnostic_assignments.extend(
                {"task_id": task_id, "datetime": value, "fold": "test"}
                for value in test["feature_time"]
            )
            diagnostic_purged_rows.extend(
                {
                    "task_id": task_id,
                    "datetime": row.feature_time,
                    "label_start_time": row.label_start_time,
                    "label_end_time": row.label_end_time,
                    "reason": "label_interval_overlaps_diagnostic_start",
                }
                for row in purged.itertuples(index=False)
            )

    legacy = legacy_manifest.copy()
    legacy["evidence_role_v2"] = "legacy_historical_diagnostic_anchor"
    legacy["selection_authority_v2"] = False
    legacy["historical_test_already_observed"] = True
    legacy_counts = (
        legacy_assignments.loc[legacy_assignments["fold"].eq("test")]
        .groupby("split_id")
        .size()
        .rename("verified_test_assignment_dates")
        .reset_index()
    )
    legacy = legacy.merge(legacy_counts, on="split_id", how="left", validate="one_to_one")

    result = {
        "label_intervals": intervals,
        "development_environments": pd.DataFrame(development_environments),
        "development_tasks": pd.DataFrame(development_tasks),
        "development_date_assignments": pd.DataFrame(development_assignments),
        "development_purged_dates": pd.DataFrame(purged_rows),
        "window_excluded_dates": pd.DataFrame(window_excluded_rows),
        "diagnostic_environments": pd.DataFrame(diagnostic_environments),
        "diagnostic_task_templates": pd.DataFrame(diagnostic_tasks),
        "diagnostic_date_assignments": pd.DataFrame(diagnostic_assignments),
        "diagnostic_purged_dates": pd.DataFrame(diagnostic_purged_rows),
        "legacy_v1_windows": legacy,
    }
    result["validation_audit"] = validate_research_protocol_v2(result, dates, config)
    return result


def validate_research_protocol_v2(
    outputs: dict[str, pd.DataFrame], calendar: pd.DatetimeIndex, config: ProtocolV2Config
) -> pd.DataFrame:
    intervals = outputs["label_intervals"].set_index("feature_time")
    calendar_set = set(calendar)
    rows: list[tuple[str, object, object]] = []
    for scope, assignments, eval_fold in (
        ("development", outputs["development_date_assignments"], "validation"),
        ("diagnostic", outputs["diagnostic_date_assignments"], "test"),
    ):
        label_overlap = 0
        chronological_failures = 0
        duplicate_cross_fold = 0
        duplicate_rows = int(assignments.duplicated(["task_id", "datetime", "fold"]).sum())
        outside_calendar = sum(value not in calendar_set for value in assignments["datetime"])
        assignment_count_mismatches = 0
        manifest = (
            outputs["development_tasks"]
            if scope == "development"
            else outputs["diagnostic_task_templates"]
        )
        for _, group in assignments.groupby("task_id", sort=True):
            train_dates = pd.DatetimeIndex(group.loc[group["fold"].eq("train"), "datetime"])
            evaluation_dates = pd.DatetimeIndex(group.loc[group["fold"].eq(eval_fold), "datetime"])
            duplicate_cross_fold += int((group.groupby("datetime")["fold"].nunique() > 1).sum())
            chronological_failures += int(train_dates.max() >= evaluation_dates.min())
            train_labels = intervals.loc[intervals.index.intersection(train_dates)]
            label_overlap += int((train_labels["label_end_time"] >= evaluation_dates.min()).sum())
            task = manifest.loc[manifest["task_id"].eq(group["task_id"].iloc[0])].iloc[0]
            assignment_count_mismatches += int(len(train_dates) != int(task["train_dates"]))
            assignment_count_mismatches += int(
                len(evaluation_dates) != int(task[f"{eval_fold}_dates"])
            )
        rows.extend(
            [
                (f"{scope}_train_evaluation_label_overlap", label_overlap, 0),
                (f"{scope}_chronological_order_failures", chronological_failures, 0),
                (f"{scope}_same_date_cross_fold", duplicate_cross_fold, 0),
                (f"{scope}_duplicate_assignment_rows", duplicate_rows, 0),
                (f"{scope}_dates_outside_matrix_calendar", outside_calendar, 0),
                (f"{scope}_manifest_assignment_count_mismatches", assignment_count_mismatches, 0),
            ]
        )
    development = outputs["development_environments"]
    diagnostic = outputs["diagnostic_environments"]
    rows.extend(
        [
            (
                "development_environment_count",
                development["environment_id"].nunique(),
                config.development_environment_count,
            ),
            (
                "diagnostic_environment_count",
                diagnostic["environment_id"].nunique(),
                config.diagnostic_environment_count,
            ),
            (
                "development_labels_before_freeze_boundary",
                bool(
                    (development["validation_label_end"] < config.selection_freeze_boundary).all()
                ),
                True,
            ),
            (
                "development_environment_label_isolation",
                bool(
                    (
                        development["validation_label_end"]
                        < development["next_environment_boundary"]
                    ).all()
                ),
                True,
            ),
            (
                "diagnostic_environment_label_isolation",
                bool(
                    (diagnostic["test_label_end"] < diagnostic["next_environment_boundary"]).all()
                ),
                True,
            ),
            ("embargoed_date_count", 0, 0),
            (
                "legacy_v1_selection_authority_count",
                int(outputs["legacy_v1_windows"]["selection_authority_v2"].sum()),
                0,
            ),
            (
                "diagnostic_selection_authority_count",
                int(outputs["diagnostic_task_templates"]["selection_authority"].sum()),
                0,
            ),
            (
                "diagnostic_execution_authorized_count",
                int(outputs["diagnostic_task_templates"]["execution_authorized"].sum()),
                0,
            ),
            (
                "development_execution_authorized_count",
                int(outputs["development_tasks"]["execution_authorized"].sum()),
                0,
            ),
        ]
    )
    return pd.DataFrame(
        [
            {
                "check_name": name,
                "status": "pass" if observed == required else "fail",
                "observed_value": observed,
                "required_value": required,
                "severity": "critical",
                "reason": "Research Protocol V2 temporal and evidence-authority contract.",
            }
            for name, observed, required in rows
        ]
    )
