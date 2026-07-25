from __future__ import annotations

import hashlib
import json
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import Ridge

from research_validation.feature_matrix import canonical_hash
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher

from .gates import assert_research_model_entry_artifact
from .inputs import (
    InputAccessAudit,
    assert_fold_isolation,
    join_labels,
    load_fold_dates,
    load_split_feature_order,
    project_features,
)
from .lineage import resolve_authoritative_parents
from .preprocessing import daily_equal_weights, fit_weighted_preprocessing
from .protocol import PROJECT_ROOT, parent_paths, resolve
from .protocol_v1_1 import _labels_runtime_path, _matrix_authority
from .targets import eligible_daily_cross_sectional_rank_centered


STAGE_ID = "research_linear_models_v1"
CANARY_OUTPUTS = (
    "artifact_manifest.json",
    "resolved_config.json",
    "parent_receipts.csv",
    "solver_canary_results.csv",
    "ridge_solver_receipt.json",
    "access_audit.csv",
    "resource_summary.csv",
    "contract_status.csv",
    "readiness_summary.csv",
    "run_review_bundle.json",
    "run_report.md",
)


def load_linear_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("stage_id") != STAGE_ID:
        raise ValueError(f"unexpected linear model stage: {payload.get('stage_id')}")
    if payload.get("experiment_class") != "post_observation_research":
        raise ValueError("linear model experiment_class must be post_observation_research")
    ridge = payload["ridge"]
    elastic = payload["elastic_net"]
    if len(ridge["alphas"]) != int(ridge["maximum_candidates_per_split"]):
        raise ValueError("Ridge candidate count does not match frozen maximum")
    if (
        len(elastic["alphas"]) * len(elastic["l1_ratios"])
        != int(elastic["maximum_candidates_per_split"])
    ):
        raise ValueError("Elastic Net candidate count does not match frozen maximum")
    if str(ridge["solver"]).lower() == "auto":
        raise ValueError("solver=auto is forbidden")
    if payload["validation"]["primary_metric"] != "mean_daily_rank_ic":
        raise ValueError("linear model primary metric is not frozen")
    if payload["validation"]["final_fit_scope"] != "outer_train_plus_validation":
        raise ValueError("linear model final fit scope is not frozen")
    return payload


def _array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _current_rss_mb() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:  # pragma: no cover - optional diagnostic
        return float("nan")


@dataclass
class _MemorySampler:
    interval_seconds: float = 0.005

    def __post_init__(self) -> None:
        self.baseline_mb = _current_rss_mb()
        self.peak_mb = self.baseline_mb
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.peak_mb = float(np.nanmax([self.peak_mb, _current_rss_mb()]))

    def __enter__(self) -> "_MemorySampler":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._stop.set()
        self._thread.join()
        self.peak_mb = float(np.nanmax([self.peak_mb, _current_rss_mb()]))

    @property
    def peak_delta_mb(self) -> float:
        return max(0.0, self.peak_mb - self.baseline_mb)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _contract(
    name: str,
    passed: bool,
    observed: object,
    expected: object,
) -> dict[str, object]:
    return {
        "check_name": name,
        "status": "pass" if passed else "blocked",
        "severity": "critical",
        "observed": json.dumps(observed, ensure_ascii=False, default=str),
        "expected": json.dumps(expected, ensure_ascii=False, default=str),
        "reason": "" if passed else f"{name} failed",
    }


def _canary_training_sample(
    config: dict[str, Any],
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[str, ...],
    InputAccessAudit,
    list[dict[str, object]],
]:
    protocol_config = yaml.safe_load(
        resolve(config["protocol_config"]).read_text(encoding="utf-8")
    )
    resolution = resolve_authoritative_parents(parent_paths(protocol_config))
    split_id = str(config["solver_canary"]["split_id"])
    ordered, _ = load_split_feature_order(
        resolve(protocol_config["selection"]["factor_weights"]),
        resolve(protocol_config["selection"]["allowlist_manifest"]),
        outer_split_id=split_id,
    )
    factor_count = int(config["solver_canary"]["factor_count"])
    factors = tuple(ordered["factor"].astype(str).tolist()[:factor_count])
    matrix = _matrix_authority(
        protocol_config,
        selected_factors=list(factors),
        verify_hashes=True,
    )
    dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="train",
        limit=int(config["solver_canary"]["train_date_count"]),
    )
    validation_dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="validation",
    )
    test_dates = load_fold_dates(
        parent_paths(protocol_config).selection_date_assignments,
        outer_split_id=split_id,
        fold="test",
    )
    assert_fold_isolation(dates, validation_dates, test_dates)
    audit = InputAccessAudit()
    joined = join_labels(
        project_features(
            factor_names=list(factors),
            factor_index=matrix.factor_index,
            dates=dates,
            fold="train",
            audit=audit,
        ),
        labels_path=_labels_runtime_path(protocol_config, resolution),
        label_name=protocol_config["target"]["label_id"],
        dates=dates,
        fold="train",
        audit=audit,
    )
    target, _, receipt = eligible_daily_cross_sectional_rank_centered(
        joined,
        label_column=protocol_config["target"]["label_id"],
        feature_columns=list(factors),
        expected_dates=dates,
        minimum_daily_pairs=int(protocol_config["target"]["minimum_daily_pairs"]),
    )
    eligible = target.notna()
    selected = joined.loc[eligible].reset_index(drop=True)
    weights = daily_equal_weights(selected["datetime"].to_numpy())
    keys = (
        selected["datetime"].astype(str)
        + "|"
        + selected["instrument"].astype(str)
    ).to_numpy()
    preprocessing = fit_weighted_preprocessing(
        selected[list(factors)].to_numpy(dtype=float),
        weights,
        feature_names=factors,
        canonical_row_keys=keys,
    )
    transformed = preprocessing.transform(
        selected[list(factors)].to_numpy(dtype=float)
    )
    selected_paths = {matrix.factor_index[factor] for factor in factors}
    partition_receipts = [
        row
        for row in matrix.partition_receipts
        if Path(str(row["partition_path"])) in selected_paths
    ]
    if audit.test_read_count:
        raise AssertionError("solver canary read test payload")
    if not receipt["status"].eq("pass").all():
        raise ValueError("solver canary sample eligibility failed")
    return (
        transformed,
        target.loc[eligible].to_numpy(dtype=float),
        weights,
        factors,
        audit,
        partition_receipts,
    )


def run_solver_canary(
    config: dict[str, Any],
    *,
    output_dir: Path,
    command: str,
) -> dict[str, Any]:
    protocol_manifest_path = resolve(config["protocol_manifest"])
    assert_research_model_entry_artifact(
        protocol_manifest_path,
        experiment_class=str(config["experiment_class"]),
        operation="canary",
    )
    code_state = capture_code_state(PROJECT_ROOT)
    if code_state.dirty:
        raise ValueError("solver canary requires a clean committed worktree")
    free_disk_gb = shutil.disk_usage(PROJECT_ROOT).free / (1024**3)
    minimum_free = float(config["resource_budget"]["minimum_free_disk_gb"])
    if free_disk_gb < minimum_free:
        raise ValueError(
            f"insufficient free disk for solver canary: {free_disk_gb:.2f} GiB"
        )
    (
        features,
        target,
        weights,
        factors,
        audit,
        partition_receipts,
    ) = _canary_training_sample(config)
    repeat_count = int(config["solver_canary"]["repeat_count"])
    rows: list[dict[str, object]] = []
    for solver in [str(item) for item in config["solver_canary"]["candidates"]]:
        coefficient_hashes: list[str] = []
        prediction_hashes: list[str] = []
        solver_rows: list[dict[str, object]] = []
        for repeat_index in range(repeat_count):
            started = time.perf_counter()
            with _MemorySampler() as sampler:
                model = Ridge(
                    alpha=1.0,
                    fit_intercept=True,
                    solver=solver,
                )
                model.fit(features, target, sample_weight=weights)
                prediction = model.predict(features)
            coefficient_hashes.append(
                canonical_hash(
                    {
                        "coef": _array_hash(model.coef_),
                        "intercept": float(model.intercept_),
                    }
                )
            )
            prediction_hashes.append(_array_hash(prediction))
            solver_rows.append(
                {
                    "solver": solver,
                    "repeat_index": repeat_index,
                    "coefficient_sha256": coefficient_hashes[-1],
                    "prediction_sha256": prediction_hashes[-1],
                    "wall_time_seconds": time.perf_counter() - started,
                    "peak_memory_delta_mb": sampler.peak_delta_mb,
                    "fit_row_count": len(features),
                    "factor_count": len(factors),
                    "status": "",
                }
            )
        stable = (
            len(set(coefficient_hashes)) == 1
            and len(set(prediction_hashes)) == 1
        )
        for row in solver_rows:
            row["status"] = "pass" if stable else "blocked"
        rows.extend(solver_rows)
    results = pd.DataFrame(rows)
    eligible = results.groupby("solver", as_index=False).agg(
        stable=("status", lambda values: values.eq("pass").all()),
        peak_memory_delta_mb=("peak_memory_delta_mb", "max"),
        wall_time_seconds=("wall_time_seconds", "sum"),
    )
    eligible = eligible.loc[eligible["stable"]].sort_values(
        ["peak_memory_delta_mb", "wall_time_seconds", "solver"],
        kind="stable",
    )
    if eligible.empty:
        raise ValueError("no deterministic Ridge solver passed canary")
    selected_solver = str(eligible.iloc[0]["solver"])
    protocol_manifest = load_artifact_manifest(protocol_manifest_path)
    receipt = {
        "schema_version": 1,
        "selected_solver": selected_solver,
        "selection_uses_prediction_quality": False,
        "candidate_solvers": [
            str(item) for item in config["solver_canary"]["candidates"]
        ],
        "repeat_count": repeat_count,
        "factor_count": len(factors),
        "train_date_count": int(config["solver_canary"]["train_date_count"]),
        "fit_row_count": len(features),
        "selection_order": [
            "lower_peak_memory",
            "lower_wall_time",
            "canonical_solver_name",
        ],
        "result_sha256": canonical_hash(results.to_dict("records")),
        "protocol_artifact_id": protocol_manifest["artifact_id"],
        "code_commit_sha": code_state.commit_sha,
        "test_read_count": audit.test_read_count,
    }
    receipt["solver_receipt_sha256"] = canonical_hash(receipt)
    review = {
        "schema_version": 1,
        "approval_type": "user_session_waiver",
        "scope": "PR5B frozen linear model config and staged run sequence",
        "command": command,
        "config_sha256": canonical_hash(config),
        "protocol_artifact_id": protocol_manifest["artifact_id"],
        "code_commit_sha": code_state.commit_sha,
        "input_partition_receipts_sha256": canonical_hash(partition_receipts),
        "free_disk_gb_at_start": free_disk_gb,
        "resource_budget": config["resource_budget"],
        "test_read_budget": 0,
    }
    review["approval_id"] = "user-session-waiver:" + canonical_hash(review)
    contracts = pd.DataFrame(
        [
            _contract(
                "protocol_artifact_gate_valid",
                True,
                protocol_manifest["artifact_id"],
                "hash-verified V1.1 protocol",
            ),
            _contract(
                "solver_auto_forbidden",
                "auto"
                not in {
                    str(value).lower()
                    for value in config["solver_canary"]["candidates"]
                },
                config["solver_canary"]["candidates"],
                "auto absent",
            ),
            _contract(
                "solver_repeat_hash_stable",
                results["status"].eq("pass").all(),
                results.groupby("solver")["status"].apply(list).to_dict(),
                "all pass",
            ),
            _contract(
                "test_read_count_before_freeze_zero",
                audit.test_read_count == 0,
                audit.test_read_count,
                0,
            ),
            _contract(
                "resource_budget_valid",
                float(results["peak_memory_delta_mb"].max())
                <= float(config["resource_budget"]["maximum_peak_rss_mb"]),
                float(results["peak_memory_delta_mb"].max()),
                config["resource_budget"]["maximum_peak_rss_mb"],
            ),
        ]
    )
    ready = contracts["status"].eq("pass").all()
    if not ready:
        raise ValueError("solver canary critical contracts failed")
    readiness = pd.DataFrame(
        [
            {
                "solver_canary_ready": True,
                "ridge_development_ready": True,
                "elastic_net_development_ready": False,
                "linear_model_research_complete": False,
                "research_model_experiment_started": True,
                "model_training_started": True,
                "test_read_count_before_freeze": audit.test_read_count,
                "production_model_selected": False,
                "authoritative_execution": False,
                "unbiased_final_estimate": False,
            }
        ]
    )
    resource = pd.DataFrame(
        [
            {
                "fit_row_count": len(features),
                "factor_count": len(factors),
                "candidate_solver_count": results["solver"].nunique(),
                "repeat_fit_count": len(results),
                "peak_memory_delta_mb": results["peak_memory_delta_mb"].max(),
                "wall_time_seconds": results["wall_time_seconds"].sum(),
                "free_disk_gb_at_start": free_disk_gb,
                "test_read_count": audit.test_read_count,
            }
        ]
    )
    parent_receipts = pd.DataFrame(
        [
            {
                "parent_role": "research_model_protocol_v1_1",
                "stage_id": protocol_manifest["stage_id"],
                "artifact_id": protocol_manifest["artifact_id"],
                "manifest_path": protocol_manifest_path.as_posix(),
                "artifact_status": protocol_manifest["artifact_status"],
                "lineage_status": protocol_manifest["lineage_status"],
                "direct_parent": True,
            }
        ]
    )
    resolved_config = {
        **config,
        "executed_command": command,
        "executed_scope": "solver_canary",
        "selected_solver": selected_solver,
        "approval_id": review["approval_id"],
    }
    with StageOutputPublisher(output_dir, CANARY_OUTPUTS) as publisher:
        results.to_csv(
            publisher.path("solver_canary_results.csv"), index=False
        )
        _write_json(publisher.path("ridge_solver_receipt.json"), receipt)
        pd.DataFrame(audit.rows()).to_csv(
            publisher.path("access_audit.csv"), index=False
        )
        resource.to_csv(publisher.path("resource_summary.csv"), index=False)
        contracts.to_csv(publisher.path("contract_status.csv"), index=False)
        readiness.to_csv(
            publisher.path("readiness_summary.csv"), index=False
        )
        parent_receipts.to_csv(
            publisher.path("parent_receipts.csv"), index=False
        )
        _write_json(publisher.path("run_review_bundle.json"), review)
        _write_json(publisher.path("resolved_config.json"), resolved_config)
        publisher.path("run_report.md").write_text(
            "# Research Linear Models V1 Solver Canary\n\n"
            f"- Selected Ridge solver: `{selected_solver}`.\n"
            f"- Scope: {len(factors)} factors × "
            f"{config['solver_canary']['train_date_count']} train dates.\n"
            f"- Fit rows: {len(features):,}.\n"
            f"- Test payload reads: {audit.test_read_count}.\n"
            "- Solver selection did not use validation or prediction quality.\n",
            encoding="utf-8",
        )
        output_files = [
            publisher.path(name)
            for name in CANARY_OUTPUTS
            if name != "artifact_manifest.json"
        ]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id=STAGE_ID,
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=output_files,
            code_state=code_state,
            input_manifest_paths=[protocol_manifest_path],
            universe_artifact_id=protocol_manifest.get(
                "universe_artifact_id"
            ),
            split_manifest_id=protocol_manifest.get("split_manifest_id"),
            factor_catalog_id=protocol_manifest.get("factor_catalog_id"),
            factor_frame_id=protocol_manifest.get("factor_frame_id"),
            contract_paths=[publisher.path("contract_status.csv")],
        )
        publisher.publish()
    return {
        "selected_solver": selected_solver,
        "output_dir": output_dir.as_posix(),
        "approval_id": review["approval_id"],
        "test_read_count": audit.test_read_count,
    }

