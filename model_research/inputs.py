from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from research_validation.feature_matrix import canonical_hash


KEY_COLUMNS = ("datetime", "instrument")


@dataclass
class InputAccessAudit:
    feature_reads: dict[str, int] = field(
        default_factory=lambda: {"train": 0, "validation": 0, "test": 0}
    )
    label_reads: dict[str, int] = field(
        default_factory=lambda: {"train": 0, "validation": 0, "test": 0}
    )

    def record(self, *, kind: str, fold: str) -> None:
        target = self.feature_reads if kind == "feature" else self.label_reads
        if fold not in target:
            raise ValueError(f"unknown fold access: {fold}")
        target[fold] += 1

    @property
    def test_read_count(self) -> int:
        return self.feature_reads["test"] + self.label_reads["test"]

    def rows(self) -> list[dict[str, object]]:
        return [
            {"input_kind": kind, "fold": fold, "read_count": count}
            for kind, values in (
                ("feature", self.feature_reads),
                ("label", self.label_reads),
            )
            for fold, count in values.items()
        ]


def load_split_feature_order(
    weights_path: Path,
    allowlist_path: Path,
    *,
    outer_split_id: str,
) -> tuple[pd.DataFrame, pd.Series]:
    weights = pd.read_csv(weights_path)
    selected = weights.loc[
        weights["outer_split_id"].astype(str).eq(outer_split_id)
        & weights["method"].astype(str).eq("equal_weight")
    ].copy()
    if selected.empty:
        raise ValueError(f"no equal-weight feature order for {outer_split_id}")
    selected["feature_order"] = pd.to_numeric(
        selected["feature_order"], errors="raise"
    ).astype(int)
    selected = selected.sort_values("feature_order", kind="stable")
    if selected["feature_order"].tolist() != list(range(len(selected))):
        raise ValueError(f"non-contiguous feature order for {outer_split_id}")
    if selected["factor"].duplicated().any():
        raise ValueError(f"duplicate factors for {outer_split_id}")

    allowlists = pd.read_csv(allowlist_path)
    row = allowlists.loc[
        allowlists["outer_split_id"].astype(str).eq(outer_split_id)
    ]
    if len(row) != 1:
        raise ValueError(
            f"allowlist manifest matched {len(row)} rows for {outer_split_id}"
        )
    receipt = row.iloc[0]
    factors = selected["factor"].astype(str).tolist()
    if int(receipt["factor_count"]) != len(factors):
        raise ValueError(f"factor count mismatch for {outer_split_id}")
    observed_feature_order = canonical_hash(factors)
    if observed_feature_order != str(receipt["feature_order_sha256"]):
        raise ValueError(f"feature order hash mismatch for {outer_split_id}")
    return selected.reset_index(drop=True), receipt


def load_fold_dates(
    date_assignments_path: Path,
    *,
    outer_split_id: str,
    fold: str,
    limit: int | None = None,
) -> pd.DatetimeIndex:
    assignments = pd.read_csv(date_assignments_path)
    split_column = "split_id" if "split_id" in assignments.columns else "outer_split_id"
    selected = assignments.loc[
        assignments[split_column].astype(str).eq(outer_split_id)
        & assignments["fold"].astype(str).eq(fold),
        "datetime",
    ]
    dates = pd.DatetimeIndex(pd.to_datetime(selected, errors="raise")).normalize()
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError(f"{outer_split_id}/{fold} dates are not unique and sorted")
    if limit is not None:
        dates = dates[:limit]
    if len(dates) == 0:
        raise ValueError(f"no dates for {outer_split_id}/{fold}")
    return dates


def partition_factor_index(partition_status_path: Path) -> dict[str, Path]:
    status = pd.read_csv(partition_status_path)
    passed = status.loc[status["status"].astype(str).eq("pass")]
    index: dict[str, Path] = {}
    for row in passed.itertuples(index=False):
        path = Path(str(row.output_path))
        if not path.is_file():
            raise ValueError(f"matrix runtime partition missing: {path}")
        for column in pq.read_schema(path).names:
            if column in KEY_COLUMNS:
                continue
            if column in index:
                raise ValueError(f"factor appears in multiple partitions: {column}")
            index[column] = path
    return index


def validate_factor_availability(
    factor_names: list[str],
    factor_index: dict[str, Path],
) -> None:
    missing = sorted(set(factor_names) - set(factor_index))
    if missing:
        raise ValueError(f"frozen factors missing from Matrix v4: {missing}")


def _read_partition_dates(
    path: Path,
    columns: list[str],
    dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        columns=list(KEY_COLUMNS) + columns,
        filters=[
            ("datetime", ">=", dates.min()),
            ("datetime", "<=", dates.max()),
        ],
    )
    frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.normalize()
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame.loc[frame["datetime"].isin(dates)].sort_values(
        list(KEY_COLUMNS), kind="stable"
    )


def project_features(
    *,
    factor_names: list[str],
    factor_index: dict[str, Path],
    dates: pd.DatetimeIndex,
    fold: str,
    audit: InputAccessAudit,
) -> pd.DataFrame:
    if fold == "test":
        raise PermissionError("test feature loader is disabled before pre-test freeze")
    validate_factor_availability(factor_names, factor_index)
    by_partition: dict[Path, list[str]] = {}
    for factor in factor_names:
        by_partition.setdefault(factor_index[factor], []).append(factor)
    frames: list[pd.DataFrame] = []
    for path, columns in sorted(by_partition.items(), key=lambda item: str(item[0])):
        audit.record(kind="feature", fold=fold)
        frames.append(_read_partition_dates(path, columns, dates))
    result = frames[0]
    for frame in frames[1:]:
        result = result.merge(
            frame,
            on=list(KEY_COLUMNS),
            how="outer",
            validate="one_to_one",
            indicator=True,
        )
        if not result["_merge"].eq("both").all():
            raise ValueError("Matrix v4 partitions do not share exact canary keys")
        result = result.drop(columns="_merge")
    if result.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("duplicate feature keys")
    return result[list(KEY_COLUMNS) + factor_names].sort_values(
        list(KEY_COLUMNS), kind="stable"
    ).reset_index(drop=True)


def join_labels(
    features: pd.DataFrame,
    *,
    labels_path: Path,
    label_name: str,
    dates: pd.DatetimeIndex,
    fold: str,
    audit: InputAccessAudit,
) -> pd.DataFrame:
    if fold == "test":
        raise PermissionError("test label loader is disabled before pre-test freeze")
    audit.record(kind="label", fold=fold)
    labels = pd.read_parquet(
        labels_path,
        columns=list(KEY_COLUMNS) + [label_name],
        filters=[
            ("datetime", ">=", dates.min()),
            ("datetime", "<=", dates.max()),
        ],
    )
    labels["datetime"] = pd.to_datetime(labels["datetime"]).dt.normalize()
    labels["instrument"] = labels["instrument"].astype(str).str.upper()
    labels = labels.loc[labels["datetime"].isin(dates)]
    if labels.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("duplicate label keys")
    merged = features.merge(
        labels,
        on=list(KEY_COLUMNS),
        how="left",
        validate="one_to_one",
    )
    return merged.sort_values(list(KEY_COLUMNS), kind="stable").reset_index(drop=True)


def assert_fold_isolation(
    train_dates: pd.DatetimeIndex,
    validation_dates: pd.DatetimeIndex,
    test_dates: pd.DatetimeIndex,
) -> None:
    sets = [set(values) for values in (train_dates, validation_dates, test_dates)]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise ValueError("train/validation/test date assignments overlap")


def assert_feature_order(
    actual: list[str] | tuple[str, ...],
    expected: list[str] | tuple[str, ...],
) -> None:
    if tuple(actual) != tuple(expected):
        raise ValueError(
            f"feature order mismatch: {tuple(actual)} != {tuple(expected)}"
        )
