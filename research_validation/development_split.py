from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DevelopmentSplitConfig:
    validation_dates: int = 60
    embargo_trading_days: int = 20
    minimum_train_dates: int = 252
    minimum_validation_dates: int = 40
    minimum_inner_windows: int = 3
    validation_end_fractions: tuple[float, ...] = (0.65, 0.82, 1.0)


def build_development_robustness_splits(
    outer_manifest: pd.DataFrame,
    outer_assignments: pd.DataFrame,
    label_intervals: pd.DataFrame,
    config: DevelopmentSplitConfig,
) -> dict[str, pd.DataFrame]:
    assignments = outer_assignments.copy()
    assignments["datetime"] = pd.to_datetime(assignments["datetime"])
    intervals = label_intervals.copy()
    intervals["feature_time"] = pd.to_datetime(intervals["feature_time"])
    intervals["label_start_time"] = pd.to_datetime(intervals["label_start_time"])
    intervals["label_end_time"] = pd.to_datetime(intervals["label_end_time"])
    interval_by_date = intervals.set_index("feature_time")
    inner_rows: list[dict[str, object]] = []
    date_rows: list[dict[str, object]] = []
    purged_rows: list[dict[str, object]] = []
    embargoed_rows: list[dict[str, object]] = []
    allowed_rows: list[dict[str, object]] = []

    for outer in outer_manifest.itertuples(index=False):
        outer_id = str(outer.split_id)
        outer_group = assignments.loc[assignments["split_id"].astype(str).eq(outer_id)]
        development_dates = pd.DatetimeIndex(
            outer_group.loc[outer_group["fold"].isin(["train", "validation"]), "datetime"]
        ).sort_values().unique()
        test_dates = pd.DatetimeIndex(outer_group.loc[outer_group["fold"].eq("test"), "datetime"]).sort_values().unique()
        if len(development_dates) == 0 or len(test_dates) == 0:
            raise ValueError(f"outer split lacks development or test dates: {outer_id}")
        allowed_rows.extend({"outer_split_id": outer_id, "datetime": date} for date in development_dates)
        built = 0
        for sequence, fraction in enumerate(config.validation_end_fractions, start=1):
            end_position = min(len(development_dates), max(1, int(round(len(development_dates) * fraction))))
            validation_start_position = end_position - config.validation_dates
            if validation_start_position <= 0:
                continue
            validation_candidates = development_dates[validation_start_position:end_position]
            train_candidates = development_dates[:validation_start_position]
            train_intervals = interval_by_date.loc[interval_by_date.index.intersection(train_candidates)].copy()
            validation_intervals = interval_by_date.loc[interval_by_date.index.intersection(validation_candidates)].copy()
            validation_start = validation_candidates.min()
            validation_end = validation_candidates.max()
            train_overlap = (train_intervals["label_start_time"] <= validation_end) & (
                train_intervals["label_end_time"] >= validation_start
            )
            train_purged = train_intervals.loc[train_overlap]
            train_kept = train_intervals.loc[~train_overlap]
            train_embargo = train_kept.tail(config.embargo_trading_days)
            validation_embargo = validation_intervals.tail(config.embargo_trading_days)
            train_kept = train_kept.drop(train_embargo.index)
            validation_kept = validation_intervals.drop(validation_embargo.index)
            if len(train_kept) < config.minimum_train_dates or len(validation_kept) < config.minimum_validation_dates:
                continue
            built += 1
            inner_id = f"{outer_id}_inner_{built:03d}"
            date_rows.extend(
                {"outer_split_id": outer_id, "inner_split_id": inner_id, "datetime": date, "fold": "train"}
                for date in train_kept.index
            )
            date_rows.extend(
                {"outer_split_id": outer_id, "inner_split_id": inner_id, "datetime": date, "fold": "validation"}
                for date in validation_kept.index
            )
            purged_rows.extend(
                {"outer_split_id": outer_id, "inner_split_id": inner_id, "datetime": date, "source_fold": "train", "reason": "label_overlap_with_inner_validation"}
                for date in train_purged.index
            )
            embargoed_rows.extend(
                {"outer_split_id": outer_id, "inner_split_id": inner_id, "datetime": date, "source_fold": fold, "reason": "inner_embargo"}
                for fold, dates in (("train", train_embargo.index), ("validation", validation_embargo.index))
                for date in dates
            )
            inner_rows.append(
                {
                    "outer_split_id": outer_id,
                    "inner_split_id": inner_id,
                    "sequence": sequence,
                    "validation_end_fraction": fraction,
                    "train_start": train_kept.index.min(),
                    "train_end": train_kept.index.max(),
                    "validation_start": validation_kept.index.min(),
                    "validation_end": validation_kept.index.max(),
                    "train_dates": len(train_kept),
                    "validation_dates": len(validation_kept),
                    "purged_dates": len(train_purged),
                    "embargoed_dates": len(train_embargo) + len(validation_embargo),
                    "outer_test_start": test_dates.min(),
                    "outer_test_end": test_dates.max(),
                    "semantic_role": "development_robustness_not_nested_selection_replay",
                }
            )
        if built < config.minimum_inner_windows:
            raise ValueError(f"{outer_id} produced {built} inner windows; require {config.minimum_inner_windows}")

    output = {
        "inner_split_manifest": pd.DataFrame(inner_rows),
        "development_date_assignments": pd.DataFrame(date_rows),
        "outer_development_allowed_dates": pd.DataFrame(allowed_rows).drop_duplicates().sort_values(["outer_split_id", "datetime"]),
        "purged_dates": pd.DataFrame(purged_rows, columns=["outer_split_id", "inner_split_id", "datetime", "source_fold", "reason"]),
        "embargoed_dates": pd.DataFrame(embargoed_rows, columns=["outer_split_id", "inner_split_id", "datetime", "source_fold", "reason"]),
    }
    output["leakage_audit"] = audit_development_splits(
        output, outer_assignments=assignments, label_intervals=intervals, minimum_inner_windows=config.minimum_inner_windows
    )
    return output


def audit_development_splits(
    outputs: dict[str, pd.DataFrame],
    *,
    outer_assignments: pd.DataFrame,
    label_intervals: pd.DataFrame,
    minimum_inner_windows: int,
) -> pd.DataFrame:
    inner = outputs["development_date_assignments"]
    intervals = label_intervals.set_index("feature_time")
    outer = outer_assignments.copy()
    outer["datetime"] = pd.to_datetime(outer["datetime"])
    train_test_overlap = 0
    validation_test_overlap = 0
    inner_label_test_overlap = 0
    outside_development = 0
    same_date_cross_fold = 0
    for (outer_id, inner_id), group in inner.groupby(["outer_split_id", "inner_split_id"], sort=True):
        outer_group = outer.loc[outer["split_id"].astype(str).eq(str(outer_id))]
        test_dates = outer_group.loc[outer_group["fold"].eq("test"), "datetime"]
        allowed = set(outer_group.loc[outer_group["fold"].isin(["train", "validation"]), "datetime"])
        train_dates = group.loc[group["fold"].eq("train"), "datetime"]
        validation_dates = group.loc[group["fold"].eq("validation"), "datetime"]
        train_test_overlap += len(set(train_dates) & set(test_dates))
        validation_test_overlap += len(set(validation_dates) & set(test_dates))
        outside_development += sum(date not in allowed for date in group["datetime"])
        same_date_cross_fold += int((group.groupby("datetime")["fold"].nunique() > 1).sum())
        used = intervals.loc[intervals.index.intersection(group["datetime"])]
        if len(test_dates):
            inner_label_test_overlap += int(
                ((used["label_start_time"] <= test_dates.max()) & (used["label_end_time"] >= test_dates.min())).sum()
            )
    counts = outputs["inner_split_manifest"].groupby("outer_split_id")["inner_split_id"].nunique()
    semantic_ok = outputs["inner_split_manifest"]["semantic_role"].eq(
        "development_robustness_not_nested_selection_replay"
    ).all()
    checks = [
        ("inner_train_outer_test_overlap", train_test_overlap, 0),
        ("inner_validation_outer_test_overlap", validation_test_overlap, 0),
        ("inner_label_outer_test_overlap", inner_label_test_overlap, 0),
        ("development_date_outside_outer_train_validation", outside_development, 0),
        ("minimum_inner_window_count", int(counts.min()), f">={minimum_inner_windows}"),
        ("same_date_cross_inner_fold", same_date_cross_fold, 0),
        ("semantic_role", semantic_ok, True),
    ]
    rows = []
    for name, observed, required in checks:
        passed = observed >= minimum_inner_windows if name == "minimum_inner_window_count" else observed == required
        rows.append({"check_name": name, "status": "pass" if passed else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "Development robustness dates must remain outside outer test."})
    return pd.DataFrame(rows)
