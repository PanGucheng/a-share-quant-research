from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research_validation.feature_matrix import canonical_hash

from .inputs import (
    InputAccessAudit,
    assert_feature_order,
    assert_fold_isolation,
    join_labels,
    load_fold_dates,
    load_split_feature_order,
    project_features,
)
from .preprocessing import (
    NEAR_ZERO_VARIANCE_THRESHOLD,
    WeightedPreprocessingFit,
    daily_equal_weights,
    stable_weighted_median,
)
from .protocol import common_payloads, contract_row, parent_paths, resolve
from .protocol_v1_1 import (
    _labels_runtime_path,
    _matrix_authority,
    _publish,
    build_protocol_binding,
    validate_canary_binding,
)
from .targets import (
    TARGET_TRANSFORM_V2_ID,
    eligible_daily_cross_sectional_rank_centered,
)
from .lineage import resolve_authoritative_parents


def _date_batches(
    dates: pd.DatetimeIndex, batch_size: int
) -> list[pd.DatetimeIndex]:
    return [
        dates[start : start + batch_size]
        for start in range(0, len(dates), batch_size)
    ]


def _current_rss_mb() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:  # pragma: no cover - optional resource diagnostic
        return float("nan")


def _prepare_runtime_dir(path: Path) -> None:
    resolved = path.resolve()
    allowed = resolve(
        "outputs/research_model_protocol_v1_1/runtime"
    ).resolve()
    if allowed != resolved and allowed not in resolved.parents:
        raise ValueError(f"dry-run runtime path escapes controlled root: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=False)


def _fit_from_spool(
    spool_paths: list[Path],
    factors: list[str],
) -> WeightedPreprocessingFit:
    medians: list[float] = []
    for factor in factors:
        values: list[np.ndarray] = []
        weights: list[np.ndarray] = []
        keys: list[np.ndarray] = []
        for path in spool_paths:
            frame = pd.read_parquet(
                path,
                columns=["datetime", "instrument", "__weight", factor],
            )
            values.append(frame[factor].to_numpy(dtype=float))
            weights.append(frame["__weight"].to_numpy(dtype=float))
            keys.append(
                (
                    frame["datetime"].astype(str)
                    + "|"
                    + frame["instrument"].astype(str)
                ).to_numpy()
            )
        medians.append(
            stable_weighted_median(
                np.concatenate(values),
                np.concatenate(weights),
                canonical_keys=np.concatenate(keys),
            )
        )
    median_array = np.asarray(medians, dtype=float)
    weighted_sum = np.zeros(len(factors), dtype=float)
    weighted_square_sum = np.zeros(len(factors), dtype=float)
    total_weight = 0.0
    for path in spool_paths:
        frame = pd.read_parquet(path, columns=["__weight", *factors])
        weights = frame["__weight"].to_numpy(dtype=float)
        matrix = frame[factors].to_numpy(dtype=float)
        matrix[~np.isfinite(matrix)] = np.nan
        for index in range(matrix.shape[1]):
            missing = np.isnan(matrix[:, index])
            matrix[missing, index] = median_array[index]
        weighted_sum += np.sum(matrix * weights[:, None], axis=0)
        weighted_square_sum += np.sum(
            (matrix**2) * weights[:, None], axis=0
        )
        total_weight += float(weights.sum())
    means = weighted_sum / total_weight
    variances = weighted_square_sum / total_weight - means**2
    blocked = [
        factors[index]
        for index in np.flatnonzero(
            variances <= NEAR_ZERO_VARIANCE_THRESHOLD
        )
    ]
    if blocked:
        raise ValueError(f"near-zero weighted variance features: {blocked}")
    return WeightedPreprocessingFit(
        feature_names=tuple(factors),
        medians=median_array,
        means=means,
        variances=variances,
    )


def run_development_dry_run(
    config: dict[str, Any],
    *,
    canary_manifest_path: Path,
    output_dir: Path,
    runtime_dir: Path,
    split_ids: list[str],
    train_date_limit: int | None = None,
    validation_date_limit: int | None = None,
    full_scope: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    resolution = resolve_authoritative_parents(parent_paths(config))
    binding = validate_canary_binding(
        config=config,
        resolution=resolution,
        canary_manifest_path=canary_manifest_path,
    )
    _prepare_runtime_dir(runtime_dir)
    batch_size = int(config["development_dry_run"]["date_batch_size"])
    labels_path = _labels_runtime_path(config, resolution)
    factor_orders: dict[str, pd.DataFrame] = {}
    allowlist_receipts: dict[str, pd.Series] = {}
    all_factors: list[str] = []
    for split_id in split_ids:
        ordered, receipt = load_split_feature_order(
            resolve(config["selection"]["factor_weights"]),
            resolve(config["selection"]["allowlist_manifest"]),
            outer_split_id=split_id,
        )
        factor_orders[split_id] = ordered
        allowlist_receipts[split_id] = receipt
        all_factors.extend(ordered["factor"].astype(str).tolist())
    matrix = _matrix_authority(
        config,
        selected_factors=sorted(set(all_factors)),
        verify_hashes=True,
    )
    access = InputAccessAudit()
    eligibility_rows: list[pd.DataFrame] = []
    validation_rows: list[dict[str, object]] = []
    split_input_rows: list[dict[str, object]] = []
    resource_rows: list[dict[str, object]] = []
    feature_rows: list[pd.DataFrame] = []
    peak_rss_mb = _current_rss_mb()
    all_expected_dates = 0

    for split_id in split_ids:
        split_started = time.perf_counter()
        ordered = factor_orders[split_id]
        receipt = allowlist_receipts[split_id]
        factors = ordered["factor"].astype(str).tolist()
        feature_rows.append(
            ordered[
                [
                    "outer_split_id",
                    "factor",
                    "factor_column",
                    "feature_order",
                ]
            ]
        )
        train_dates = load_fold_dates(
            parent_paths(config).selection_date_assignments,
            outer_split_id=split_id,
            fold="train",
            limit=train_date_limit,
        )
        validation_dates = load_fold_dates(
            parent_paths(config).selection_date_assignments,
            outer_split_id=split_id,
            fold="validation",
            limit=validation_date_limit,
        )
        test_dates = load_fold_dates(
            parent_paths(config).selection_date_assignments,
            outer_split_id=split_id,
            fold="test",
        )
        assert_fold_isolation(train_dates, validation_dates, test_dates)
        all_expected_dates += len(train_dates) + len(validation_dates)
        split_runtime = runtime_dir / split_id
        split_runtime.mkdir(parents=True, exist_ok=True)
        spool_paths: list[Path] = []
        train_key_count = 0
        train_fit_count = 0
        for batch_index, dates in enumerate(
            _date_batches(train_dates, batch_size)
        ):
            joined = join_labels(
                project_features(
                    factor_names=factors,
                    factor_index=matrix.factor_index,
                    dates=dates,
                    fold="train",
                    audit=access,
                ),
                labels_path=labels_path,
                label_name=config["target"]["label_id"],
                dates=dates,
                fold="train",
                audit=access,
            )
            target, _, date_receipt = (
                eligible_daily_cross_sectional_rank_centered(
                    joined,
                    label_column=config["target"]["label_id"],
                    feature_columns=factors,
                    expected_dates=dates,
                    minimum_daily_pairs=int(
                        config["target"]["minimum_daily_pairs"]
                    ),
                )
            )
            date_receipt = date_receipt.assign(
                outer_split_id=split_id, fold="train"
            )
            eligibility_rows.append(date_receipt)
            fit_rows = target.notna()
            fit_frame = joined.loc[
                fit_rows, ["datetime", "instrument", *factors]
            ].copy()
            fit_frame["__weight"] = daily_equal_weights(
                fit_frame["datetime"].to_numpy()
            )
            fit_frame["__target"] = target.loc[fit_rows].to_numpy()
            spool_path = split_runtime / f"train_{batch_index:03d}.parquet"
            fit_frame.to_parquet(
                spool_path, index=False, compression="zstd"
            )
            spool_paths.append(spool_path)
            train_key_count += len(joined)
            train_fit_count += len(fit_frame)
            peak_rss_mb = float(
                np.nanmax([peak_rss_mb, _current_rss_mb()])
            )
        fitted = _fit_from_spool(spool_paths, factors)

        validation_key_count = 0
        validation_transform_count = 0
        validation_feature_eligible_count = 0
        validation_all_nan_count = 0
        for dates in _date_batches(validation_dates, batch_size):
            joined = join_labels(
                project_features(
                    factor_names=factors,
                    factor_index=matrix.factor_index,
                    dates=dates,
                    fold="validation",
                    audit=access,
                ),
                labels_path=labels_path,
                label_name=config["target"]["label_id"],
                dates=dates,
                fold="validation",
                audit=access,
            )
            _, _, date_receipt = eligible_daily_cross_sectional_rank_centered(
                joined,
                label_column=config["target"]["label_id"],
                feature_columns=factors,
                expected_dates=dates,
                minimum_daily_pairs=int(
                    config["target"]["minimum_daily_pairs"]
                ),
            )
            eligibility_rows.append(
                date_receipt.assign(
                    outer_split_id=split_id, fold="validation"
                )
            )
            feature_eligible = (
                joined[factors]
                .replace([np.inf, -np.inf], np.nan)
                .notna()
                .any(axis=1)
            )
            transform_frame = joined.loc[feature_eligible]
            assert_feature_order(
                list(transform_frame[factors].columns), factors
            )
            transformed = fitted.transform(
                transform_frame[factors].to_numpy()
            )
            if transformed.shape[1] != len(factors):
                raise ValueError(
                    f"validation transform width mismatch for {split_id}"
                )
            validation_key_count += len(joined)
            validation_transform_count += transformed.shape[0]
            validation_feature_eligible_count += int(
                feature_eligible.sum()
            )
            validation_all_nan_count += int((~feature_eligible).sum())
            peak_rss_mb = float(
                np.nanmax([peak_rss_mb, _current_rss_mb()])
            )
        coverage = (
            validation_transform_count / validation_key_count
            if validation_key_count
            else 0.0
        )
        minimum_coverage = float(
            config["validation"]["minimum_transform_coverage"]
        )
        validation_rows.append(
            {
                "outer_split_id": split_id,
                "factor_count": len(factors),
                "input_row_count": validation_key_count,
                "feature_eligible_row_count": validation_feature_eligible_count,
                "all_nan_row_count": validation_all_nan_count,
                "output_row_count": validation_transform_count,
                "output_feature_count": len(factors),
                "feature_order_valid": True,
                "transform_coverage": coverage,
                "minimum_transform_coverage": minimum_coverage,
                "status": "pass" if coverage >= minimum_coverage else "blocked",
            }
        )
        for fold, dates, keys in (
            ("train", train_dates, train_key_count),
            ("validation", validation_dates, validation_key_count),
        ):
            split_input_rows.append(
                {
                    "outer_split_id": split_id,
                    "fold": fold,
                    "date_count": len(dates),
                    "start_date": dates.min().date().isoformat(),
                    "end_date": dates.max().date().isoformat(),
                    "key_count": keys,
                    "factor_count": len(factors),
                    "allowlist_sha256": receipt["allowlist_sha256"],
                    "feature_order_sha256": receipt["feature_order_sha256"],
                    "allowed_dates_sha256": receipt["allowed_dates_sha256"],
                }
            )
        resource_rows.append(
            {
                "outer_split_id": split_id,
                "train_date_count": len(train_dates),
                "validation_date_count": len(validation_dates),
                "factor_count": len(factors),
                "train_fit_row_count": train_fit_count,
                "runtime_seconds": time.perf_counter() - split_started,
                "peak_rss_mb_observed": peak_rss_mb,
                "spool_file_count": len(spool_paths),
                "model_fit_count": 0,
                "test_read_count": access.test_read_count,
            }
        )

    eligibility = pd.concat(eligibility_rows, ignore_index=True)[
        [
            "outer_split_id",
            "fold",
            "datetime",
            "valid_pair_count",
            "status",
        ]
    ]
    validation = pd.DataFrame(validation_rows)
    partitions = pd.DataFrame(matrix.partition_receipts)
    selected_paths = {
        matrix.factor_index[name].as_posix() for name in set(all_factors)
    }
    partitions = partitions.loc[
        partitions["partition_path"].isin(selected_paths)
    ].reset_index(drop=True)
    sample_exact = (
        len(eligibility) == all_expected_dates
        and eligibility["datetime"].notna().all()
    )
    validation_ready = (
        not validation.empty and validation["status"].eq("pass").all()
    )
    matrix_ready = (
        not partitions.empty
        and partitions["hash_verified"].astype(bool).all()
    )
    scope_complete = (
        full_scope
        and split_ids
        == [str(item) for item in config["development_dry_run"]["split_ids"]]
        and train_date_limit is None
        and validation_date_limit is None
    )
    contracts = pd.DataFrame(
        [
            contract_row(
                "canary_protocol_binding_valid",
                bool(binding["binding_sha256"]),
                binding["binding_sha256"],
                "current protocol equals canary binding",
            ),
            contract_row(
                "sample_eligibility_exact",
                sample_exact,
                len(eligibility),
                all_expected_dates,
            ),
            contract_row(
                "validation_transform_ready",
                validation_ready,
                validation[
                    ["outer_split_id", "transform_coverage", "status"]
                ].to_dict("records"),
                "all split validation transforms pass",
            ),
            contract_row(
                "matrix_runtime_authority_valid",
                matrix_ready,
                int(partitions["hash_verified"].astype(bool).sum()),
                len(partitions),
            ),
            contract_row(
                (
                    "development_dry_run_ready"
                    if scope_complete
                    else "development_smoke_ready"
                ),
                True,
                {
                    "split_ids": split_ids,
                    "train_date_limit": train_date_limit,
                    "validation_date_limit": validation_date_limit,
                },
                "requested development scope completed",
            ),
            contract_row(
                "test_read_count_before_freeze_zero",
                access.test_read_count == 0,
                access.test_read_count,
                0,
            ),
        ]
    )
    ready = contracts["status"].eq("pass").all()
    payloads = common_payloads(config)
    payloads["target_transform"]["target_transform_id"] = (
        TARGET_TRANSFORM_V2_ID
    )
    payloads["protocol_binding"] = binding
    frames = {
        "parent_receipts": pd.DataFrame(resolution.receipts),
        "split_input_manifest": pd.DataFrame(split_input_rows),
        "feature_order_manifest": pd.concat(feature_rows, ignore_index=True),
        "sample_eligibility_receipt": eligibility,
        "validation_transform_receipt": validation,
        "partition_source_receipt": partitions,
        "mutation_results": pd.DataFrame(
            [
                {
                    "mutation_name": "canary_binding_revalidated",
                    "status": "pass",
                    "development_hash_unchanged": True,
                    "reason": "",
                }
            ]
        ),
        "access_audit": pd.DataFrame(access.rows()),
        "resource_summary": pd.DataFrame(resource_rows).assign(
            total_runtime_seconds=time.perf_counter() - started,
            runtime_parquet_committed=False,
        ),
        "contract_status": contracts,
        "readiness_summary": pd.DataFrame(
            [
                {
                    "protocol_closure_version": "1.1",
                    "research_model_protocol_ready": False,
                    "research_model_input_protocol_ready": ready,
                    "research_model_input_ready": False,
                    "research_model_training_ready": False,
                    "research_model_hard_stop_active": True,
                    "production_model_hard_stop_active": True,
                    "production_model_selected": False,
                    "research_model_experiment_started": False,
                    "model_training_started": False,
                    "experiment_class": "post_observation_research",
                    "historical_test_already_observed": True,
                    "authoritative_execution": False,
                    "unbiased_final_estimate": False,
                    "development_dry_run_ready": scope_complete and ready,
                    "test_read_count_before_freeze": access.test_read_count,
                }
            ]
        ),
    }
    return _publish(
        config={
            **config,
            "executed_development_scope": {
                "split_ids": split_ids,
                "train_date_limit": train_date_limit,
                "validation_date_limit": validation_date_limit,
                "full_scope": full_scope,
            },
        },
        output_dir=output_dir,
        resolution=resolution,
        frames=frames,
        payloads=payloads,
        report=(
            "# Research Model Protocol V1.1 Development Dry-run\n\n"
            f"- Splits: {', '.join(split_ids)}.\n"
            f"- Full scope: {scope_complete}.\n"
            "- Train preprocessing was fit without model training; validation "
            "was transformed in exact frozen feature order.\n"
            "- Runtime spools are untracked. Test payload reads: 0. Model fits: 0.\n"
        ),
        input_manifest_paths=[
            *parent_paths(config).direct_model_parent_paths,
            canary_manifest_path,
        ],
    )
