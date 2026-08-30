from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

from research_validation.research_protocol_v2 import (
    ProtocolV2Config,
    TrainingHistoryCandidate,
    build_research_protocol_v2,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _config() -> ProtocolV2Config:
    return ProtocolV2Config(
        matrix_start=pd.Timestamp("2018-01-01"),
        matrix_end=pd.Timestamp("2025-12-31"),
        execution_lag=1,
        holding_days=20,
        first_validation_start=pd.Timestamp("2021-05-01"),
        validation_months=2,
        development_step_months=3,
        development_environment_count=5,
        minimum_train_dates=500,
        minimum_validation_dates=30,
        selection_freeze_boundary=pd.Timestamp("2022-08-01"),
        first_diagnostic_start=pd.Timestamp("2022-08-01"),
        diagnostic_months=2,
        diagnostic_step_months=3,
        diagnostic_environment_count=7,
        minimum_test_dates=30,
        candidates=(
            TrainingHistoryCandidate("expanding", "expanding"),
            TrainingHistoryCandidate("sliding_504", "sliding", 504),
        ),
    )


def _legacy(calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = pd.DataFrame(
        [
            {
                "split_id": "split_001",
                "train_start": calendar[0],
                "train_end": calendar[699],
                "validation_start": calendar[740],
                "validation_end": calendar[819],
                "test_start": calendar[860],
                "test_end": calendar[959],
                "train_dates": 700,
                "validation_dates": 80,
                "test_dates": 100,
                "purged_dates": 42,
                "embargoed_dates": 40,
                "label_horizon": 20,
                "execution_lag": 1,
            }
        ]
    )
    assignments = pd.DataFrame(
        [{"split_id": "split_001", "datetime": date, "fold": "test"} for date in calendar[860:960]]
    )
    return manifest, assignments


def test_protocol_v2_has_exact_temporal_isolation() -> None:
    calendar = pd.bdate_range("2018-01-01", "2025-12-31")
    legacy, legacy_assignments = _legacy(calendar)
    outputs = build_research_protocol_v2(calendar, _config(), legacy, legacy_assignments)

    assert outputs["validation_audit"]["status"].eq("pass").all()
    assert outputs["development_environments"]["environment_id"].nunique() == 5
    assert outputs["diagnostic_environments"]["environment_id"].nunique() == 7
    assert outputs["development_tasks"]["embargoed_dates"].eq(0).all()
    assert outputs["development_tasks"]["purged_dates"].eq(21).all()
    assert outputs["legacy_v1_windows"]["selection_authority_v2"].eq(False).all()  # noqa: E712


def test_sliding_candidate_uses_last_504_safe_dates() -> None:
    calendar = pd.bdate_range("2018-01-01", "2025-12-31")
    legacy, legacy_assignments = _legacy(calendar)
    outputs = build_research_protocol_v2(calendar, _config(), legacy, legacy_assignments)
    tasks = outputs["development_tasks"]

    sliding = tasks.loc[tasks["training_history_id"].eq("sliding_504")]
    expanding = tasks.loc[tasks["training_history_id"].eq("expanding")]
    assert sliding["train_dates"].eq(504).all()
    assert (expanding["train_dates"].to_numpy() >= sliding["train_dates"].to_numpy()).all()


def test_generation_is_deterministic() -> None:
    calendar = pd.bdate_range("2018-01-01", "2025-12-31")
    legacy, legacy_assignments = _legacy(calendar)
    first = build_research_protocol_v2(calendar, _config(), legacy, legacy_assignments)
    second = build_research_protocol_v2(calendar[::-1], _config(), legacy, legacy_assignments)

    for name in (
        "development_environments",
        "development_tasks",
        "development_date_assignments",
        "diagnostic_environments",
        "diagnostic_task_templates",
        "diagnostic_date_assignments",
    ):
        pd.testing.assert_frame_equal(first[name], second[name])


def test_registered_protocol_separates_evidence_and_caps_trials() -> None:
    payload = yaml.safe_load(
        (PROJECT_ROOT / "configs/research_protocol_v2.yaml").read_text(encoding="utf-8")
    )

    assert payload["evidence_policy"] == {
        "development": "selection_authority",
        "historical_diagnostic": "historical_diagnostic_only",
        "forward": "prospective_evidence_only",
    }
    assert payload["model_selection"]["maximum_registered_candidates_per_experiment"] == 8
    assert (
        payload["model_selection"]["candidate_axis_policy"] == "one_axis_per_registered_experiment"
    )
    assert (
        payload["historical_diagnostic"]["execution_authorized_before_development_freeze"] is False
    )
    assert payload["qlib_integration"]["rolling_gen_adopted_as_authority"] is False
    assert payload["feature_eligibility"]["fit_scope"] == "task_train_dates_only"
    assert payload["feature_eligibility"]["validation_or_test_eligibility_reads_forbidden"] is True


def test_frozen_protocol_report_hashes_are_current() -> None:
    report_dir = PROJECT_ROOT / "reports/research_protocol_v2"
    manifest = json.loads((report_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["formal_model_competition_started"] is False
    assert manifest["leakage_validation_passed"] is True
    for name, expected in manifest["output_file_hashes"].items():
        observed = hashlib.sha256((report_dir / name).read_bytes()).hexdigest()
        assert observed == expected, name
