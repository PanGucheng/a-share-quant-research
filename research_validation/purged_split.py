from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardConfig:
    train_years: int
    validation_months: int
    test_months: int
    step_months: int
    label_horizon: int
    execution_lag: int
    embargo_trading_days: int
    minimum_train_dates: int
    minimum_validation_dates: int
    minimum_test_dates: int
    split_mode: str = "expanding"


def label_intervals(calendar: pd.DatetimeIndex, horizon: int, execution_lag: int) -> pd.DataFrame:
    dates = pd.DatetimeIndex(calendar).sort_values().unique()
    rows = []
    for index, feature_time in enumerate(dates):
        start_index = index + execution_lag
        end_index = start_index + horizon
        if start_index >= len(dates) or end_index >= len(dates):
            continue
        rows.append({"feature_time": feature_time, "label_start_time": dates[start_index], "label_end_time": dates[end_index]})
    return pd.DataFrame(rows)


def purge_against_period(samples: pd.DataFrame, period_start: pd.Timestamp, period_end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    overlap = (samples["label_start_time"] <= period_end) & (samples["label_end_time"] >= period_start)
    return samples.loc[~overlap].copy(), samples.loc[overlap].copy()


def _range(dates: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    return dates[(dates >= start) & (dates < end)]


def build_purged_walk_forward(calendar: pd.DatetimeIndex, config: WalkForwardConfig) -> dict[str, pd.DataFrame]:
    dates = pd.DatetimeIndex(calendar).sort_values().unique()
    labels = label_intervals(dates, config.label_horizon, config.execution_lag)
    if labels.empty:
        raise ValueError("calendar cannot support configured label metadata")
    first_test = dates[0] + pd.DateOffset(years=config.train_years, months=config.validation_months)
    eligible_test_starts = dates[dates >= first_test]
    if eligible_test_starts.empty:
        raise ValueError("calendar is too short for configured train and validation windows")
    test_start = eligible_test_starts[0]
    manifests, assignments, purged_rows, embargo_rows = [], [], [], []
    split_id = 0
    while test_start <= dates[-1]:
        test_end_target = test_start + pd.DateOffset(months=config.test_months)
        test_dates = _range(dates, test_start, test_end_target)
        if len(test_dates) < config.minimum_test_dates:
            break
        validation_start_target = test_start - pd.DateOffset(months=config.validation_months)
        validation_dates = _range(dates, validation_start_target, test_start)
        if len(validation_dates) < config.minimum_validation_dates:
            raise ValueError("validation window has insufficient dates")
        if config.split_mode == "rolling":
            train_start = validation_dates[0] - pd.DateOffset(years=config.train_years)
        elif config.split_mode == "expanding":
            train_start = dates[0]
        else:
            raise ValueError(f"unknown split_mode: {config.split_mode}")
        train_dates = _range(dates, train_start, validation_dates[0])
        train_samples = labels.loc[labels["feature_time"].isin(train_dates)]
        validation_samples = labels.loc[labels["feature_time"].isin(validation_dates)]

        train_kept, train_purged = purge_against_period(train_samples, validation_dates[0], test_dates[-1])
        validation_kept, validation_purged = purge_against_period(validation_samples, test_dates[0], test_dates[-1])
        embargo_count = config.embargo_trading_days
        train_embargo = train_kept.tail(embargo_count) if embargo_count else train_kept.iloc[0:0]
        validation_embargo = validation_kept.tail(embargo_count) if embargo_count else validation_kept.iloc[0:0]
        train_kept = train_kept.drop(train_embargo.index)
        validation_kept = validation_kept.drop(validation_embargo.index)
        if len(train_kept) < config.minimum_train_dates or len(validation_kept) < config.minimum_validation_dates:
            raise ValueError("purge/embargo leaves insufficient train or validation dates")

        split_id += 1
        split_name = f"split_{split_id:03d}"
        for role, frame in [("train", train_kept), ("validation", validation_kept)]:
            assignments.extend({"split_id": split_name, "datetime": value, "fold": role} for value in frame["feature_time"])
        assignments.extend({"split_id": split_name, "datetime": value, "fold": "test"} for value in test_dates)
        for role, frame in [("train", train_purged), ("validation", validation_purged)]:
            purged_rows.extend({"split_id": split_name, "datetime": value, "source_fold": role, "reason": "label_overlap"} for value in frame["feature_time"])
        for role, frame in [("train", train_embargo), ("validation", validation_embargo)]:
            embargo_rows.extend({"split_id": split_name, "datetime": value, "source_fold": role, "reason": "embargo"} for value in frame["feature_time"])
        manifests.append(
            {
                "split_id": split_name,
                "train_start": train_kept["feature_time"].min(), "train_end": train_kept["feature_time"].max(),
                "validation_start": validation_kept["feature_time"].min(), "validation_end": validation_kept["feature_time"].max(),
                "test_start": test_dates[0], "test_end": test_dates[-1],
                "train_dates": len(train_kept), "validation_dates": len(validation_kept), "test_dates": len(test_dates),
                "purged_dates": len(train_purged) + len(validation_purged), "embargoed_dates": len(train_embargo) + len(validation_embargo),
                "label_horizon": config.label_horizon, "execution_lag": config.execution_lag,
            }
        )
        next_target = test_start + pd.DateOffset(months=config.step_months)
        next_dates = dates[dates >= next_target]
        if next_dates.empty:
            break
        test_start = next_dates[0]
    if not manifests:
        raise ValueError("no valid walk-forward split produced")
    return {
        "split_manifest": pd.DataFrame(manifests),
        "date_assignments": pd.DataFrame(assignments),
        "purged_dates": pd.DataFrame(purged_rows, columns=["split_id", "datetime", "source_fold", "reason"]),
        "embargoed_dates": pd.DataFrame(embargo_rows, columns=["split_id", "datetime", "source_fold", "reason"]),
        "label_intervals": labels,
    }


def leakage_audit(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    assignments = outputs["date_assignments"]
    labels = outputs["label_intervals"].set_index("feature_time")
    overlap_count = 0
    train_validation_overlap = 0
    validation_test_overlap = 0
    same_date_cross_fold = 0
    for _, group in assignments.groupby("split_id"):
        same_date_cross_fold += int((group.groupby("datetime")["fold"].nunique() > 1).sum())
        train_dates = group.loc[group["fold"] == "train", "datetime"]
        test_dates = group.loc[group["fold"] == "test", "datetime"]
        validation_dates = group.loc[group["fold"] == "validation", "datetime"]
        if len(validation_dates):
            train_labels = labels.loc[labels.index.intersection(train_dates)]
            train_validation_overlap += int(((train_labels["label_start_time"] <= validation_dates.max()) & (train_labels["label_end_time"] >= validation_dates.min())).sum())
        if len(test_dates):
            train_labels = labels.loc[labels.index.intersection(train_dates)]
            overlap_count += int(((train_labels["label_start_time"] <= test_dates.max()) & (train_labels["label_end_time"] >= test_dates.min())).sum())
            validation_labels = labels.loc[labels.index.intersection(validation_dates)]
            validation_test_overlap += int(
                (
                    (validation_labels["label_start_time"] <= test_dates.max())
                    & (validation_labels["label_end_time"] >= test_dates.min())
                ).sum()
            )
    embargo = outputs["embargoed_dates"]
    merged = assignments.merge(embargo[["split_id", "datetime"]], on=["split_id", "datetime"], how="inner")
    rows = [
        ("train_test_label_overlap", overlap_count, 0),
        ("train_validation_label_overlap", train_validation_overlap, 0),
        ("validation_test_label_overlap", validation_test_overlap, 0),
        ("same_date_cross_fold_count", same_date_cross_fold, 0),
        ("embargo_violation_count", len(merged), 0),
        (
            "split_contract",
            "pass"
            if overlap_count == 0
            and train_validation_overlap == 0
            and validation_test_overlap == 0
            and same_date_cross_fold == 0
            and len(merged) == 0
            else "fail",
            "pass",
        ),
    ]
    return pd.DataFrame([{"check_name": name, "status": "pass" if observed == required else "fail", "observed_value": observed, "required_value": required, "severity": "critical", "reason": "Purged walk-forward leakage contract."} for name, observed, required in rows])
