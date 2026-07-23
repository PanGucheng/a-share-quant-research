from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(directory: Path) -> dict[str, object]:
    manifest = load_artifact_manifest(directory / "artifact_manifest.json")
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    assert not bool(manifest["code_dirty"])
    assert not validate_manifest_outputs(manifest, directory)
    return manifest


def main() -> int:
    execution_dir = PROJECT_ROOT / "outputs" / "execution_accuracy_correction_v1" / "current"
    cache_dir = PROJECT_ROOT / "outputs" / "market_cache_v2" / "current"
    state_dir = PROJECT_ROOT / "outputs" / "instrument_state_v1" / "current"
    freeze_dir = PROJECT_ROOT / "outputs" / "bugfix_research_freeze_v1" / "current"

    execution_manifest = validate_manifest(execution_dir)
    cache_manifest = validate_manifest(cache_dir)
    validate_manifest(state_dir)
    freeze_manifest = validate_manifest(freeze_dir)
    assert cache_manifest["artifact_id"] in execution_manifest["input_artifact_ids"]
    assert freeze_manifest["artifact_id"] in execution_manifest["input_artifact_ids"]

    contracts = pd.read_csv(execution_dir / "contract_status.csv").set_index("check_name")
    critical = contracts.loc[contracts["severity"].eq("critical")]
    assert critical["status"].eq("pass").all()
    expected_blocked = {
        "instrument_state_pit_valid",
        "price_limit_rule_resolved",
        "terminal_event_policy_valid",
        "authoritative_oos_execution_ready",
    }
    capability = contracts.loc[contracts["severity"].eq("capability")]
    assert set(capability.index) == expected_blocked
    assert capability["status"].eq("blocked").all()
    assert int(contracts.loc["future_market_field_count", "observed_value"]) == 0
    assert int(contracts.loc["unknown_execution_difference_count", "observed_value"]) == 0

    artifacts = pd.read_csv(execution_dir / "execution_artifacts.csv")
    assert {
        "orders",
        "fills",
        "rejected_orders",
        "partial_fills",
        "transaction_costs",
        "daily_accounting",
        "positions",
        "execution_summary",
    } == set(artifacts["table"])
    for row in artifacts.itertuples(index=False):
        path = Path(row.path)
        assert path.is_file(), path
        assert sha256(path) == row.sha256, path
        assert len(pd.read_parquet(path)) == int(row.rows), path

    fees = pd.read_csv(execution_dir / "fee_schedule_usage.csv")
    assert set(fees["fee_schedule_id"]) == {"a_share_from_2023_08_28"}
    assert fees["sell_stamp_tax_rate"].eq(0.0005).all()
    assert fees["transfer_fee_rate"].gt(0).all()
    assert fees["transfer_fee"].gt(0).all()

    comparison = pd.read_csv(execution_dir / "execution_summary_comparison.csv")
    assert len(comparison) == 6
    assert comparison.groupby("outer_split_id")["method"].nunique().eq(2).all()
    attribution = pd.read_csv(execution_dir / "old_vs_new_attribution.csv")
    assert set(attribution["category"]) == {
        "signal_change",
        "fee_schedule",
        "price_limit_semantics",
        "lot_rule",
        "stale_valuation",
        "terminal_event",
        "calendar_or_cache",
        "unknown",
    }
    unknown = attribution.loc[attribution["category"].eq("unknown")].iloc[0]
    assert unknown["status"] == "none"

    freezes = pd.read_csv(freeze_dir / "bugfix_freeze_index.csv")
    assert len(freezes) == 3
    assert freezes["freeze_type"].eq("post_observation_bugfix").all()
    assert freezes["historical_test_already_observed"].astype(bool).all()
    assert not freezes["unbiased_final_estimate"].astype(bool).any()

    print(
        "Execution Accuracy Correction V1 receipts are internally consistent: "
        "all critical semantics pass, unknown differences are zero, and "
        "authoritative historical capability remains honestly blocked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
