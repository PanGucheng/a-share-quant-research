from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml

from research_validation.feature_matrix import canonical_hash, file_sha256
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .freeze import load_freeze_before_test
from .gates import assert_research_model_entry_artifact
from .inputs import (
    InputAccessAudit,
    join_test_labels_after_freeze,
    load_fold_dates,
    project_test_features_after_freeze,
)
from .linear_models import _date_batches, _labels_runtime_path, _matrix_authority
from .linear_models import _validation_metrics
from .lineage import resolve_authoritative_parents
from .preprocessing import WeightedPreprocessingFit
from .protocol import PROJECT_ROOT, parent_paths, resolve
from .schemas import PREDICTION_COLUMNS, prediction_schema_violations


STAGE_ID = "research_linear_model_test_release_v1"
SPLIT_IDS = ("split_001", "split_002", "split_003")
METHODS = ("ridge", "elastic_net")
RECEIPT_NAMES = tuple(
    f"release_receipts/{split_id}_{method}.json"
    for split_id in SPLIT_IDS
    for method in METHODS
)
OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    "prediction_receipt.csv",
    "test_release_index.csv",
    "test_metrics.csv",
    "test_daily_ic.csv",
    "access_audit.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "resource_summary.csv",
    "run_report.md",
    *RECEIPT_NAMES,
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _contract(
    name: str, passed: bool, observed: object, expected: object
) -> dict[str, object]:
    return {
        "check_name": name,
        "status": "pass" if passed else "blocked",
        "severity": "critical",
        "observed": json.dumps(observed, ensure_ascii=False, default=str),
        "expected": json.dumps(expected, ensure_ascii=False, default=str),
        "reason": "" if passed else f"{name} failed",
    }


def _safe_prepare_runtime(path: Path) -> None:
    allowed = resolve("outputs/research_linear_models_v1/runtime").resolve()
    target = path.resolve()
    if target != allowed and allowed not in target.parents:
        raise ValueError(f"test release runtime escapes controlled root: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def _load_preprocessing(path: Path) -> WeightedPreprocessingFit:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return WeightedPreprocessingFit(
        feature_names=tuple(str(value) for value in payload["feature_names"]),
        medians=np.asarray(payload["medians"], dtype=float),
        means=np.asarray(payload["means"], dtype=float),
        variances=np.asarray(payload["variances"], dtype=float),
    )


def _daily_ic_frame(
    frame: pd.DataFrame,
    *,
    split_id: str,
    method: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date, group in frame.groupby("datetime", sort=True):
        finite = np.isfinite(group["prediction"]) & np.isfinite(
            group["__label"]
        )
        selected = group.loc[finite]
        value = float("nan")
        if (
            len(selected) >= 2
            and selected["prediction"].nunique(dropna=True) >= 2
        ):
            value = float(
                selected["prediction"].rank(method="average").corr(
                    selected["__label"].rank(method="average")
                )
            )
        rows.append(
            {
                "outer_split_id": split_id,
                "method": method,
                "datetime": pd.Timestamp(date).date().isoformat(),
                "pair_count": len(selected),
                "rank_ic": value,
                "status": "pass" if np.isfinite(value) else "unavailable",
            }
        )
    return pd.DataFrame(rows)


def release_linear_model_tests(
    config: dict[str, Any],
    *,
    output_dir: Path,
    runtime_dir: Path,
    command: str,
) -> dict[str, Any]:
    if (output_dir / "test_release_index.csv").exists():
        raise PermissionError(
            "single test release already exists; deterministic replay requires "
            "a separate audited command"
        )
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="prediction",
    )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("test release requires a clean committed worktree")
    development_manifest_path = resolve(
        "outputs/research_linear_models_v1/development/artifact_manifest.json"
    )
    freeze_manifest_path = resolve(
        "outputs/research_linear_models_v1/test_release_freeze/"
        "artifact_manifest.json"
    )
    development = load_artifact_manifest(development_manifest_path)
    freeze_artifact = load_artifact_manifest(freeze_manifest_path)
    for role, path, manifest in (
        ("development", development_manifest_path, development),
        ("release_freeze", freeze_manifest_path, freeze_artifact),
    ):
        if manifest.get("artifact_status") != "pass":
            raise ValueError(f"{role} artifact is not pass")
        issues = validate_manifest_outputs(manifest, path.parent)
        if issues:
            raise ValueError(f"{role} output hashes are invalid")
    _safe_prepare_runtime(runtime_dir)

    protocol_config = yaml.safe_load(
        resolve(config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    labels_path = _labels_runtime_path(protocol_config, resolution)
    model_receipts = pd.read_csv(
        development_manifest_path.parent / "model_receipt.csv"
    )
    coefficient = pd.read_csv(
        development_manifest_path.parent / "coefficient_summary.csv"
    )
    freeze_index = pd.read_csv(
        freeze_manifest_path.parent / "release_freeze_index.csv"
    )
    freezes: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    models: dict[tuple[str, str], Any] = {}
    preprocessing: dict[
        tuple[str, str], WeightedPreprocessingFit
    ] = {}
    factors_by_split: dict[str, list[str]] = {}
    all_factors: list[str] = []

    for split_id in SPLIT_IDS:
        method_orders: list[list[str]] = []
        for method in METHODS:
            key = (split_id, method)
            row = freeze_index.loc[
                freeze_index["outer_split_id"].astype(str).eq(split_id)
                & freeze_index["method"].astype(str).eq(method)
            ]
            if len(row) != 1:
                raise ValueError(f"release freeze index mismatch: {key}")
            path = freeze_manifest_path.parent / str(
                row.iloc[0]["freeze_path"]
            )
            if path.as_posix().split("/")[-1] not in {
                Path(name).name for name in RECEIPT_NAMES
            }:
                raise ValueError(f"unexpected release freeze filename: {path}")
            freeze = load_freeze_before_test(path)
            if freeze.get("freeze_id") != row.iloc[0]["freeze_id"]:
                raise ValueError(f"release freeze ID mismatch: {key}")
            if freeze.get("development_artifact_id") != development["artifact_id"]:
                raise ValueError(f"release freeze development mismatch: {key}")
            freezes[key] = (path, freeze)
            model_row = model_receipts.loc[
                model_receipts["outer_split_id"].astype(str).eq(split_id)
                & model_receipts["method"].astype(str).eq(method)
            ]
            if len(model_row) != 1:
                raise ValueError(f"model receipt mismatch: {key}")
            model_row = model_row.iloc[0]
            model_path = Path(str(model_row["runtime_path"]))
            if (
                not model_path.is_file()
                or file_sha256(model_path)
                != str(freeze["model_binary_sha256"])
            ):
                raise ValueError(f"frozen model binary hash mismatch: {key}")
            models[key] = joblib.load(model_path)
            preprocessing_row = pd.read_csv(
                development_manifest_path.parent / "preprocessing_receipt.csv"
            )
            preprocessing_row = preprocessing_row.loc[
                preprocessing_row["outer_split_id"].astype(str).eq(split_id)
                & preprocessing_row["method"].astype(str).eq(method)
            ]
            if len(preprocessing_row) != 1:
                raise ValueError(f"preprocessing receipt mismatch: {key}")
            preprocessing_path = Path(
                str(preprocessing_row.iloc[0]["runtime_path"])
            )
            if (
                not preprocessing_path.is_file()
                or file_sha256(preprocessing_path)
                != str(preprocessing_row.iloc[0]["preprocessing_sha256"])
            ):
                raise ValueError(f"preprocessing hash mismatch: {key}")
            fitted = _load_preprocessing(preprocessing_path)
            if (
                "weighted-preprocessing:"
                + canonical_hash(
                    {
                        "feature_names": list(fitted.feature_names),
                        "medians": fitted.medians.tolist(),
                        "means": fitted.means.tolist(),
                        "variances": fitted.variances.tolist(),
                        "algorithm": "stable_daily_equal_weighted_preprocessing_v1",
                    }
                )
                != freeze["fitted_preprocessing_artifact_id"]
            ):
                raise ValueError(f"preprocessing artifact ID mismatch: {key}")
            preprocessing[key] = fitted
            order = (
                coefficient.loc[
                    coefficient["outer_split_id"].astype(str).eq(split_id)
                    & coefficient["method"].astype(str).eq(method)
                ]
                .sort_values("feature_order", kind="stable")["factor"]
                .astype(str)
                .tolist()
            )
            if canonical_hash(order) != str(freeze["feature_order_sha256"]):
                raise ValueError(f"test feature order hash mismatch: {key}")
            method_orders.append(order)
        if method_orders[0] != method_orders[1]:
            raise ValueError(f"linear methods use different factors: {split_id}")
        factors_by_split[split_id] = method_orders[0]
        all_factors.extend(method_orders[0])
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=sorted(set(all_factors)),
        verify_hashes=True,
    )

    audit = InputAccessAudit()
    prediction_frames: dict[tuple[str, str], list[pd.DataFrame]] = {
        (split_id, method): []
        for split_id in SPLIT_IDS
        for method in METHODS
    }
    label_frames: dict[str, list[pd.DataFrame]] = {
        split_id: [] for split_id in SPLIT_IDS
    }
    batch_size = int(config["execution"]["date_batch_size"])
    freeze_validated_before_first_read = True

    for split_id in SPLIT_IDS:
        factors = factors_by_split[split_id]
        test_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="test",
        )
        representative_freeze_path = freezes[(split_id, "ridge")][0]
        for dates in _date_batches(test_dates, batch_size):
            features = project_test_features_after_freeze(
                factor_names=factors,
                factor_index=matrix.factor_index,
                dates=dates,
                audit=audit,
                freeze_manifest_path=representative_freeze_path,
                outer_split_id=split_id,
                authorized_dates=test_dates,
            )
            joined = join_test_labels_after_freeze(
                features,
                labels_path=labels_path,
                label_name=protocol_config["target"]["label_id"],
                dates=dates,
                audit=audit,
                freeze_manifest_path=representative_freeze_path,
                outer_split_id=split_id,
                authorized_dates=test_dates,
            )
            joined = joined.rename(
                columns={protocol_config["target"]["label_id"]: "__label"}
            )
            feature_eligible = (
                joined[factors]
                .replace([np.inf, -np.inf], np.nan)
                .notna()
                .any(axis=1)
            )
            selected = joined.loc[feature_eligible].reset_index(drop=True)
            label_frames[split_id].append(
                selected[["datetime", "instrument", "__label"]]
            )
            for method in METHODS:
                key = (split_id, method)
                freeze = freezes[key][1]
                transformed = preprocessing[key].transform(
                    selected[factors].to_numpy(dtype=float)
                )
                prediction = models[key].predict(transformed)
                prediction_artifact_id = (
                    "linear-prediction:"
                    + canonical_hash(
                        {
                            "freeze_id": freeze["freeze_id"],
                            "outer_split_id": split_id,
                            "method": method,
                        }
                    )
                )
                prediction_frames[key].append(
                    pd.DataFrame(
                        {
                            "outer_split_id": split_id,
                            "datetime": selected["datetime"].to_numpy(),
                            "instrument": selected["instrument"].to_numpy(),
                            "method": method,
                            "prediction": prediction,
                            "prediction_artifact_id": prediction_artifact_id,
                            "allowlist_sha256": freeze["allowlist_sha256"],
                            "feature_order_sha256": freeze[
                                "feature_order_sha256"
                            ],
                            "model_freeze_id": freeze["freeze_id"],
                            "experiment_class": "post_observation_research",
                        }
                    )
                )

    prediction_receipts: list[dict[str, Any]] = []
    release_index_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    daily_frames: list[pd.DataFrame] = []
    release_payloads: dict[str, dict[str, Any]] = {}
    coverage_values: list[float] = []

    for split_id in SPLIT_IDS:
        labels = pd.concat(label_frames[split_id], ignore_index=True)
        test_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="test",
        )
        for method in METHODS:
            key = (split_id, method)
            prediction = pd.concat(prediction_frames[key], ignore_index=True)
            prediction = prediction[list(PREDICTION_COLUMNS)].sort_values(
                ["datetime", "instrument"], kind="stable"
            )
            violations = prediction_schema_violations(
                list(prediction.columns)
            )
            if violations:
                raise ValueError(f"prediction schema violations: {violations}")
            runtime_path = runtime_dir / f"{split_id}_{method}.parquet"
            prediction.to_parquet(runtime_path, index=False, compression="zstd")
            prediction_sha = file_sha256(runtime_path)
            evaluation = prediction[
                ["datetime", "instrument", "prediction"]
            ].merge(
                labels,
                on=["datetime", "instrument"],
                how="left",
                validate="one_to_one",
            )
            metrics = _validation_metrics(evaluation, evaluation["prediction"])
            daily = _daily_ic_frame(
                evaluation, split_id=split_id, method=method
            )
            daily_frames.append(daily)
            coverage_values.append(float(metrics["prediction_coverage"]))
            freeze_path, freeze = freezes[key]
            label_hash = canonical_hash(
                evaluation[
                    ["datetime", "instrument", "__label"]
                ].astype(str).to_dict("records")
            )
            release = {
                "schema_version": 1,
                "status": "consumed",
                "outer_split_id": split_id,
                "method": method,
                "freeze_id": freeze["freeze_id"],
                "freeze_sha256": file_sha256(freeze_path),
                "freeze_artifact_id": freeze_artifact["artifact_id"],
                "development_artifact_id": development["artifact_id"],
                "test_dates_sha256": canonical_hash(
                    [value.date().isoformat() for value in test_dates]
                ),
                "prediction_artifact_id": str(
                    prediction["prediction_artifact_id"].iloc[0]
                ),
                "prediction_sha256": prediction_sha,
                "test_label_sha256": label_hash,
                "prediction_row_count": len(prediction),
                "execution_commit_sha": code_state.commit_sha,
                "release_timestamp": datetime.now(timezone.utc).isoformat(),
                "historical_test_already_observed": True,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
                "production_model_selected": False,
            }
            release["release_id"] = (
                "linear-test-release:" + canonical_hash(release)
            )
            filename = f"{split_id}_{method}.json"
            release_payloads[filename] = release
            release_index_rows.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    "receipt_path": f"release_receipts/{filename}",
                    "release_id": release["release_id"],
                    "freeze_id": freeze["freeze_id"],
                    "prediction_sha256": prediction_sha,
                    "status": "consumed",
                }
            )
            prediction_receipts.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    "prediction_artifact_id": release[
                        "prediction_artifact_id"
                    ],
                    "prediction_row_count": len(prediction),
                    "prediction_sha256": prediction_sha,
                    "runtime_path": runtime_path.as_posix(),
                    "schema_sha256": canonical_hash(list(PREDICTION_COLUMNS)),
                    "prediction_coverage": metrics["prediction_coverage"],
                }
            )
            metric_rows.append(
                {
                    "outer_split_id": split_id,
                    "method": method,
                    **metrics,
                    "historical_test_already_observed": True,
                    "authoritative_execution": False,
                    "unbiased_final_estimate": False,
                }
            )

    prediction_receipt = pd.DataFrame(prediction_receipts)
    release_index = pd.DataFrame(release_index_rows)
    metrics = pd.DataFrame(metric_rows)
    daily_ic = pd.concat(daily_frames, ignore_index=True)
    minimum_coverage = float(
        config["validation"]["minimum_prediction_coverage"]
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "release_freeze_validated_before_first_test_read",
                freeze_validated_before_first_read,
                freeze_validated_before_first_read,
                True,
            ),
            _contract(
                "single_test_release",
                len(release_index) == 6
                and release_index["status"].eq("consumed").all(),
                len(release_index),
                6,
            ),
            _contract(
                "prediction_schema_valid",
                prediction_receipt["schema_sha256"].nunique() == 1,
                prediction_receipt["schema_sha256"].nunique(),
                1,
            ),
            _contract(
                "prediction_coverage_valid",
                min(coverage_values) >= minimum_coverage,
                min(coverage_values),
                f">={minimum_coverage}",
            ),
            _contract(
                "test_metrics_finite",
                np.isfinite(metrics["mean_daily_rank_ic"]).all()
                and np.isfinite(metrics["daily_rank_ic_ir"]).all(),
                metrics[
                    [
                        "outer_split_id",
                        "method",
                        "mean_daily_rank_ic",
                        "daily_rank_ic_ir",
                    ]
                ].to_dict("records"),
                "all finite",
            ),
            _contract(
                "model_binary_hash_valid",
                len(models) == 6,
                len(models),
                6,
            ),
            _contract(
                "historical_oos_disclosure_valid",
                metrics["historical_test_already_observed"].all()
                and (~metrics["authoritative_execution"]).all()
                and (~metrics["unbiased_final_estimate"]).all(),
                True,
                True,
            ),
            _contract(
                "production_model_not_selected",
                True,
                False,
                False,
            ),
        ]
    )
    if not contracts["status"].eq("pass").all():
        raise ValueError(
            "linear test release contracts failed: "
            + ",".join(
                contracts.loc[
                    ~contracts["status"].eq("pass"), "check_name"
                ].astype(str)
            )
        )
    readiness = pd.DataFrame(
        [
            {
                "ridge_split_count_complete": 3,
                "elastic_net_split_count_complete": 3,
                "linear_model_development_complete": True,
                "linear_model_research_complete": True,
                "pre_test_freeze_ready": True,
                "single_test_release_complete": True,
                "research_model_experiment_started": True,
                "model_training_started": True,
                "historical_oos_linear_evaluation_complete": True,
                "production_model_selected": False,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
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
            for role, path, manifest in (
                (
                    "linear_development",
                    development_manifest_path,
                    development,
                ),
                (
                    "linear_test_release_freeze",
                    freeze_manifest_path,
                    freeze_artifact,
                ),
            )
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": "single_outer_test_release_3_splits_2_methods",
        "development_artifact_id": development["artifact_id"],
        "release_freeze_artifact_id": freeze_artifact["artifact_id"],
        "output_dir": output_dir.as_posix(),
        "runtime_dir": runtime_dir.as_posix(),
    }
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        prediction_receipt.to_csv(
            publisher.path("prediction_receipt.csv"), index=False
        )
        release_index.to_csv(
            publisher.path("test_release_index.csv"), index=False
        )
        metrics.to_csv(publisher.path("test_metrics.csv"), index=False)
        daily_ic.to_csv(publisher.path("test_daily_ic.csv"), index=False)
        pd.DataFrame(audit.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        pd.DataFrame(
            [
                {
                    "split_count": 3,
                    "method_count": 2,
                    "release_count": len(release_index),
                    "prediction_row_count": int(
                        prediction_receipt["prediction_row_count"].sum()
                    ),
                    "test_feature_read_count": audit.feature_reads["test"],
                    "test_label_read_count": audit.label_reads["test"],
                }
            ]
        ).to_csv(publisher.path("resource_summary.csv"), index=False)
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        _write_json(publisher.path("resolved_config.json"), resolved_config)
        for filename, payload in release_payloads.items():
            _write_json(
                publisher.path(f"release_receipts/{filename}"), payload
            )
        publisher.path("run_report.md").write_text(
            "# Research Linear Models V1 Historical Test Release\n\n"
            "- Ridge: 3/3 split test predictions released once.\n"
            "- Elastic Net: 3/3 split test predictions released once.\n"
            f"- Prediction rows: {int(prediction_receipt['prediction_row_count'].sum()):,}.\n"
            "- Test metrics are evaluation-only and cannot alter candidates.\n"
            "- Historical test was previously observed; evidence is not an "
            "unbiased final estimate or authoritative execution result.\n"
            "- Production model selected: false.\n",
            encoding="utf-8",
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
            input_manifest_paths=[
                development_manifest_path,
                freeze_manifest_path,
            ],
            universe_artifact_id=development.get("universe_artifact_id"),
            split_manifest_id=development.get("split_manifest_id"),
            factor_catalog_id=development.get("factor_catalog_id"),
            factor_frame_id=development.get("factor_frame_id"),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "output_dir": output_dir.as_posix(),
        "release_count": len(release_index),
        "prediction_row_count": int(
            prediction_receipt["prediction_row_count"].sum()
        ),
        "minimum_prediction_coverage": min(coverage_values),
    }
