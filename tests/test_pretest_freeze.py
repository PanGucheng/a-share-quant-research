from pathlib import Path

import pytest

from research_validation.pretest_freeze import (
    build_pretest_freeze_payload,
    preserve_or_reject_existing_freeze,
    validate_pretest_freeze,
    reserve_test_release,
)


def make_payload(commit: str = "a" * 40) -> dict:
    return build_pretest_freeze_payload(
        outer_split_id="split_001",
        allowlist_sha256="b" * 64,
        feature_order_sha256="c" * 64,
        weights_by_method={"equal_weight": "d" * 64, "stability_weight": "e" * 64},
        preprocessing_config_sha256="f" * 64,
        model_config_sha256="1" * 64,
        training_data_sha256="2" * 64,
        qlib_exchange_config_sha256="3" * 64,
        test_dates_sha256="4" * 64,
        code_commit_sha=commit,
        freeze_timestamp="2026-07-22T00:00:00+00:00",
    )


def test_pretest_freeze_round_trip_validates_content_hash() -> None:
    payload = make_payload()
    issues = validate_pretest_freeze(
        payload,
        expected_outer_split_id="split_001",
        expected_code_commit_sha="a" * 40,
        expected_allowlist_sha256="b" * 64,
        expected_feature_order_sha256="c" * 64,
        expected_weights_by_method={"equal_weight": "d" * 64, "stability_weight": "e" * 64},
        expected_preprocessing_config_sha256="f" * 64,
        expected_model_config_sha256="1" * 64,
        expected_qlib_exchange_config_sha256="3" * 64,
        expected_test_dates_sha256="4" * 64,
    )
    assert issues == []


def test_existing_freeze_rejects_changed_commit(tmp_path: Path) -> None:
    path = tmp_path / "freeze.json"
    path.write_text(__import__("json").dumps(make_payload()), encoding="utf-8")
    with pytest.raises(ValueError, match="immutable"):
        preserve_or_reject_existing_freeze(path, make_payload(commit="9" * 40))


def test_test_release_reservation_is_single_input_identity(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    first = reserve_test_release(path, {"outer_split_id": "split_001", "freeze_id": "f1"})
    repeated = reserve_test_release(path, {"outer_split_id": "split_001", "freeze_id": "f1"})
    assert repeated == first
    with pytest.raises(ValueError, match="different frozen inputs"):
        reserve_test_release(path, {"outer_split_id": "split_001", "freeze_id": "f2"})
