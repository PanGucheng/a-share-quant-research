from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from .lightgbm_models import _contract
from .lineage import resolve_authoritative_parents
from .linear_models import _date_batches, _labels_runtime_path
from .linear_models import _matrix_authority, _validation_metrics
from .linear_test_release import _daily_ic_frame, _load_preprocessing
from .protocol import PROJECT_ROOT, parent_paths, resolve
from .schemas import PREDICTION_COLUMNS, prediction_schema_violations


STAGE_ID = "research_lightgbm_test_release_v1"
SPLIT_IDS = ("split_001", "split_002", "split_003")
RECEIPT_NAMES = tuple(
    f"release_receipts/{split_id}_lightgbm.json"
    for split_id in SPLIT_IDS
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


def _safe_prepare_runtime(path: Path) -> None:
    allowed = resolve("outputs/research_lightgbm_v1/runtime").resolve()
    target = path.resolve()
    if target != allowed and allowed not in target.parents:
        raise ValueError(
            f"LightGBM test runtime escapes controlled root: {target}"
        )
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)


def release_lightgbm_tests(
    config: dict[str, Any],
    *,
    output_dir: Path,
    runtime_dir: Path,
    command: str,
) -> dict[str, Any]:
    import lightgbm as lgb

    if (output_dir / "test_release_index.csv").exists():
        raise PermissionError(
            "single LightGBM test release already exists"
        )
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="prediction",
    )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError(
            "LightGBM test release requires clean committed code"
        )
    development_path = resolve(
        "outputs/research_lightgbm_v1/development/"
        "artifact_manifest.json"
    )
    freeze_artifact_path = resolve(
        "outputs/research_lightgbm_v1/test_release_freeze/"
        "artifact_manifest.json"
    )
    development = load_artifact_manifest(development_path)
    freeze_artifact = load_artifact_manifest(
        freeze_artifact_path
    )
    for role, path, manifest in (
        ("development", development_path, development),
        (
            "test_release_freeze",
            freeze_artifact_path,
            freeze_artifact,
        ),
    ):
        issues = validate_manifest_outputs(manifest, path.parent)
        if (
            manifest.get("artifact_status") != "pass"
            or manifest.get("lineage_status") != "complete"
            or issues
        ):
            raise ValueError(
                f"invalid LightGBM test parent: {role}: {issues}"
            )
    _safe_prepare_runtime(runtime_dir)
    protocol_config = yaml.safe_load(
        resolve(config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(
        parent_paths(protocol_config)
    )
    labels_path = _labels_runtime_path(
        protocol_config, resolution
    )
    model_receipts = pd.read_csv(
        development_path.parent / "model_receipt.csv"
    )
    preprocessing_receipts = pd.read_csv(
        development_path.parent / "preprocessing_receipt.csv"
    )
    freeze_index = pd.read_csv(
        freeze_artifact_path.parent / "release_freeze_index.csv"
    )
    freezes: dict[str, tuple[Path, dict[str, Any]]] = {}
    models: dict[str, Any] = {}
    preprocessing: dict[str, Any] = {}
    factors_by_split: dict[str, list[str]] = {}
    all_factors: list[str] = []
    for split_id in SPLIT_IDS:
        row = freeze_index.loc[
            freeze_index["outer_split_id"].astype(str).eq(split_id)
            & freeze_index["method"].astype(str).eq("lightgbm")
        ]
        if len(row) != 1:
            raise ValueError(
                f"LightGBM release freeze mismatch: {split_id}"
            )
        freeze_path = freeze_artifact_path.parent / str(
            row.iloc[0]["freeze_path"]
        )
        freeze = load_freeze_before_test(freeze_path)
        if (
            freeze.get("freeze_id") != row.iloc[0]["freeze_id"]
            or freeze.get("development_artifact_id")
            != development["artifact_id"]
        ):
            raise ValueError(
                f"LightGBM freeze identity mismatch: {split_id}"
            )
        freezes[split_id] = (freeze_path, freeze)
        model_row = model_receipts.loc[
            model_receipts["outer_split_id"]
            .astype(str)
            .eq(split_id)
        ]
        preprocessing_row = preprocessing_receipts.loc[
            preprocessing_receipts["outer_split_id"]
            .astype(str)
            .eq(split_id)
        ]
        if len(model_row) != 1 or len(preprocessing_row) != 1:
            raise ValueError(
                f"LightGBM runtime receipt mismatch: {split_id}"
            )
        model_path = Path(str(model_row.iloc[0]["runtime_path"]))
        preprocessing_path = Path(
            str(preprocessing_row.iloc[0]["runtime_path"])
        )
        if (
            not model_path.is_file()
            or file_sha256(model_path)
            != str(freeze["model_binary_sha256"])
        ):
            raise ValueError(
                f"LightGBM model hash mismatch: {split_id}"
            )
        if (
            not preprocessing_path.is_file()
            or file_sha256(preprocessing_path)
            != str(
                preprocessing_row.iloc[0]["preprocessing_sha256"]
            )
        ):
            raise ValueError(
                f"LightGBM preprocessing hash mismatch: {split_id}"
            )
        fitted = _load_preprocessing(preprocessing_path)
        fitted_payload = {
            "feature_names": list(fitted.feature_names),
            "medians": fitted.medians.tolist(),
            "means": fitted.means.tolist(),
            "variances": fitted.variances.tolist(),
            "algorithm": (
                "stable_daily_equal_weighted_preprocessing_v1"
            ),
        }
        fitted_id = (
            "weighted-preprocessing:"
            + canonical_hash(fitted_payload)
        )
        if fitted_id != freeze[
            "fitted_preprocessing_artifact_id"
        ]:
            raise ValueError(
                f"LightGBM preprocessing ID mismatch: {split_id}"
            )
        factors = list(fitted.feature_names)
        if canonical_hash(factors) != str(
            freeze["feature_order_sha256"]
        ):
            raise ValueError(
                f"LightGBM feature order mismatch: {split_id}"
            )
        models[split_id] = lgb.Booster(model_file=str(model_path))
        preprocessing[split_id] = fitted
        factors_by_split[split_id] = factors
        all_factors.extend(factors)
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=sorted(set(all_factors)),
        verify_hashes=True,
    )

    audit = InputAccessAudit()
    prediction_frames: dict[str, list[pd.DataFrame]] = {
        split_id: [] for split_id in SPLIT_IDS
    }
    label_frames: dict[str, list[pd.DataFrame]] = {
        split_id: [] for split_id in SPLIT_IDS
    }
    batch_size = int(
        protocol_config["development_dry_run"]["date_batch_size"]
    )
    for split_id in SPLIT_IDS:
        factors = factors_by_split[split_id]
        freeze_path, freeze = freezes[split_id]
        test_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="test",
        )
        for dates in _date_batches(test_dates, batch_size):
            features = project_test_features_after_freeze(
                factor_names=factors,
                factor_index=matrix.factor_index,
                dates=dates,
                audit=audit,
                freeze_manifest_path=freeze_path,
                outer_split_id=split_id,
                authorized_dates=test_dates,
            )
            joined = join_test_labels_after_freeze(
                features,
                labels_path=labels_path,
                label_name=protocol_config["target"]["label_id"],
                dates=dates,
                audit=audit,
                freeze_manifest_path=freeze_path,
                outer_split_id=split_id,
                authorized_dates=test_dates,
            ).rename(
                columns={
                    protocol_config["target"]["label_id"]: "__label"
                }
            )
            eligible = (
                joined[factors]
                .replace([np.inf, -np.inf], np.nan)
                .notna()
                .any(axis=1)
            )
            selected = joined.loc[eligible].reset_index(drop=True)
            label_frames[split_id].append(
                selected[["datetime", "instrument", "__label"]]
            )
            transformed = preprocessing[split_id].transform(
                selected[factors].to_numpy(dtype=float)
            )
            rounds = int(
                freeze["selected_hyperparameters"][
                    "num_boost_round"
                ]
            )
            prediction = models[split_id].predict(
                transformed, num_iteration=rounds
            )
            prediction_artifact_id = (
                "lightgbm-prediction:"
                + canonical_hash(
                    {
                        "freeze_id": freeze["freeze_id"],
                        "outer_split_id": split_id,
                        "method": "lightgbm",
                    }
                )
            )
            prediction_frames[split_id].append(
                pd.DataFrame(
                    {
                        "outer_split_id": split_id,
                        "datetime": selected["datetime"].to_numpy(),
                        "instrument": selected[
                            "instrument"
                        ].to_numpy(),
                        "method": "lightgbm",
                        "prediction": prediction,
                        "prediction_artifact_id": (
                            prediction_artifact_id
                        ),
                        "allowlist_sha256": freeze[
                            "allowlist_sha256"
                        ],
                        "feature_order_sha256": freeze[
                            "feature_order_sha256"
                        ],
                        "model_freeze_id": freeze["freeze_id"],
                        "experiment_class": (
                            "post_observation_research"
                        ),
                    }
                )
            )

    prediction_receipts: list[dict[str, Any]] = []
    release_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    daily_frames: list[pd.DataFrame] = []
    release_payloads: dict[str, dict[str, Any]] = {}
    coverage_values: list[float] = []
    for split_id in SPLIT_IDS:
        labels = pd.concat(
            label_frames[split_id], ignore_index=True
        )
        prediction = pd.concat(
            prediction_frames[split_id], ignore_index=True
        )[list(PREDICTION_COLUMNS)].sort_values(
            ["datetime", "instrument"], kind="stable"
        )
        violations = prediction_schema_violations(
            list(prediction.columns)
        )
        if violations:
            raise ValueError(
                f"LightGBM prediction schema violations: {violations}"
            )
        runtime_path = runtime_dir / f"{split_id}_lightgbm.parquet"
        prediction.to_parquet(
            runtime_path, index=False, compression="zstd"
        )
        prediction_sha = file_sha256(runtime_path)
        evaluation = prediction[
            ["datetime", "instrument", "prediction"]
        ].merge(
            labels,
            on=["datetime", "instrument"],
            how="left",
            validate="one_to_one",
        )
        metrics = _validation_metrics(
            evaluation, evaluation["prediction"]
        )
        daily_frames.append(
            _daily_ic_frame(
                evaluation,
                split_id=split_id,
                method="lightgbm",
            )
        )
        coverage_values.append(float(metrics["prediction_coverage"]))
        freeze_path, freeze = freezes[split_id]
        test_dates = load_fold_dates(
            parent_paths(protocol_config).selection_date_assignments,
            outer_split_id=split_id,
            fold="test",
        )
        release = {
            "schema_version": 1,
            "status": "consumed",
            "outer_split_id": split_id,
            "method": "lightgbm",
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
            "test_label_sha256": canonical_hash(
                evaluation[
                    ["datetime", "instrument", "__label"]
                ]
                .astype(str)
                .to_dict("records")
            ),
            "prediction_row_count": len(prediction),
            "execution_commit_sha": code_state.commit_sha,
            "release_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "historical_test_already_observed": True,
            "authoritative_execution": False,
            "unbiased_final_estimate": False,
            "production_model_selected": False,
        }
        release["release_id"] = (
            "lightgbm-test-release:" + canonical_hash(release)
        )
        filename = f"{split_id}_lightgbm.json"
        release_payloads[filename] = release
        release_rows.append(
            {
                "outer_split_id": split_id,
                "method": "lightgbm",
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
                "method": "lightgbm",
                "prediction_artifact_id": release[
                    "prediction_artifact_id"
                ],
                "prediction_row_count": len(prediction),
                "prediction_sha256": prediction_sha,
                "runtime_path": runtime_path.as_posix(),
                "schema_sha256": canonical_hash(
                    list(PREDICTION_COLUMNS)
                ),
                "prediction_coverage": metrics[
                    "prediction_coverage"
                ],
            }
        )
        metric_rows.append(
            {
                "outer_split_id": split_id,
                "method": "lightgbm",
                **metrics,
                "historical_test_already_observed": True,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        )
    prediction_receipt = pd.DataFrame(prediction_receipts)
    release_index = pd.DataFrame(release_rows)
    metrics = pd.DataFrame(metric_rows)
    daily_ic = pd.concat(daily_frames, ignore_index=True)
    minimum_coverage = float(
        config["validation"]["minimum_prediction_coverage"]
    )
    contracts = pd.DataFrame(
        [
            _contract(
                "release_freeze_validated_before_first_test_read",
                True,
                True,
                True,
            ),
            _contract(
                "single_test_release",
                len(release_index) == 3
                and release_index["status"].eq("consumed").all(),
                len(release_index),
                3,
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
                        "mean_daily_rank_ic",
                        "daily_rank_ic_ir",
                    ]
                ].to_dict("records"),
                "all finite",
            ),
            _contract(
                "model_binary_hash_valid",
                len(models) == 3,
                len(models),
                3,
            ),
            _contract(
                "historical_oos_disclosure_valid",
                metrics[
                    "historical_test_already_observed"
                ].all()
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
        raise ValueError("LightGBM test release contracts failed")
    readiness = pd.DataFrame(
        [
            {
                "lightgbm_split_count_complete": 3,
                "lightgbm_development_complete": True,
                "lightgbm_model_research_complete": True,
                "pre_test_freeze_ready": True,
                "single_test_release_complete": True,
                "research_model_experiment_started": True,
                "model_training_started": True,
                "historical_oos_lightgbm_evaluation_complete": True,
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
                ("lightgbm_development", development_path, development),
                (
                    "lightgbm_test_release_freeze",
                    freeze_artifact_path,
                    freeze_artifact,
                ),
            )
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": (
            "single_outer_test_release_3_lightgbm_models"
        ),
        "development_artifact_id": development["artifact_id"],
        "release_freeze_artifact_id": freeze_artifact[
            "artifact_id"
        ],
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
        metrics.to_csv(
            publisher.path("test_metrics.csv"), index=False
        )
        daily_ic.to_csv(
            publisher.path("test_daily_ic.csv"), index=False
        )
        pd.DataFrame(audit.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False
        )
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        pd.DataFrame(
            [
                {
                    "split_count": 3,
                    "method_count": 1,
                    "release_count": len(release_index),
                    "prediction_row_count": int(
                        prediction_receipt[
                            "prediction_row_count"
                        ].sum()
                    ),
                    "test_feature_read_count": audit.feature_reads[
                        "test"
                    ],
                    "test_label_read_count": audit.label_reads["test"],
                }
            ]
        ).to_csv(
            publisher.path("resource_summary.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
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
        for filename, payload in release_payloads.items():
            publisher.path(
                f"release_receipts/{filename}"
            ).write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        publisher.path("run_report.md").write_text(
            "# Research LightGBM V1 Historical Test Release\n\n"
            "- LightGBM: 3/3 split test predictions released once.\n"
            f"- Prediction rows: "
            f"{int(prediction_receipt['prediction_row_count'].sum()):,}.\n"
            "- Test metrics are evaluation-only and cannot alter "
            "candidates or rounds.\n"
            "- Historical test was previously observed; evidence is "
            "not an unbiased final estimate or authoritative execution.\n"
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
                development_path,
                freeze_artifact_path,
            ],
            universe_artifact_id=development.get(
                "universe_artifact_id"
            ),
            split_manifest_id=development.get("split_manifest_id"),
            factor_catalog_id=development.get(
                "factor_catalog_id"
            ),
            factor_frame_id=development.get("factor_frame_id"),
            contract_paths=[
                publisher.path("contract_status.csv")
            ],
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
